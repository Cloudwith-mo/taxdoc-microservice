import json
import boto3
import base64
import uuid
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
textract = boto3.client('textract')
bedrock = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

# Configuration
BUCKET_NAME = 'taxflowsai-uploads'
TABLE_NAME = 'taxdoc-documents'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:995805900737:taxdoc-alerts'

def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": _cors_headers(),
        "body": json.dumps(body) if not isinstance(body, str) else body
    }

def lambda_handler(event, context):
    """AI-powered document processing with Textract + Claude"""
    
    if event.get("httpMethod", "").upper() == "OPTIONS":
        return _response(200, "")
    
    try:
        logger.info(f"Processing event: {json.dumps(event)}")
        # Handle base64 image upload
        body_str = event.get('body', '{}')
        if not body_str:
            return _response(400, {'error': 'No body provided'})
        
        try:
            body_json = json.loads(body_str)
            filename = body_json.get('filename', 'document.png')
            content_base64 = body_json.get('contentBase64')
            
            if not content_base64:
                return _response(400, {'error': 'No contentBase64 provided'})
            
            # Clean base64 string thoroughly
            import re
            # Remove data: prefix
            content_base64 = re.sub(r'^data:.*;base64,', '', content_base64, flags=re.I)
            # Remove whitespace/newlines
            content_base64 = re.sub(r'\s+', '', content_base64)
            # Normalize URL-safe to standard
            content_base64 = content_base64.replace('-', '+').replace('_', '/')
            # Add padding
            rem = len(content_base64) % 4
            if rem:
                content_base64 += '=' * (4 - rem)
            
            try:
                file_content = base64.b64decode(content_base64, validate=False)
            except Exception as e:
                return _response(400, {'error': 'Invalid base64', 'detail': str(e)})
            
            logger.info(f"Base64 cleaned, first 40 chars: {content_base64[:40]}")
            
            if not file_content:
                return _response(400, {'error': 'Empty file content'})
            
            return process_uploaded_document(file_content, filename)
            
        except json.JSONDecodeError:
            return _response(400, {'error': 'Invalid JSON in request body'})
        except Exception as e:
            logger.exception("Body parsing error")
            return _response(500, {'error': 'Failed to parse request', 'detail': str(e)})
        
        # Extract file from multipart data (simplified)
        file_content = extract_file_from_multipart(body)
        
        # Generate unique document ID
        doc_id = str(uuid.uuid4())
        s3_key = f"documents/{doc_id}.pdf"
        
        # Upload to S3
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_content)
        
        # Step 1: Textract OCR
        textract_response = textract.analyze_document(
            Document={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}},
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        # Extract raw text
        raw_text = extract_text_from_textract(textract_response)
        
        # Step 2: Claude AI extraction
        extracted_data = extract_with_claude(raw_text)
        
        # Step 3: Regex fallback for missing fields
        final_data = apply_regex_fallback(raw_text, extracted_data)
        
        # Step 4: Store results
        # Enhanced result with field-level confidence
        field_count = len(final_data.get('fields', {}))
        avg_confidence = sum(f.get('confidence', 0.5) for f in final_data.get('fields', {}).values() if isinstance(f, dict)) / max(field_count, 1)
        
        result = {
            'DocumentID': doc_id,
            'DocumentType': final_data.get('document_type', 'Unknown'),
            'ClassificationConfidence': final_data.get('confidence', 0.95),
            'FieldExtractionConfidence': round(avg_confidence, 2),
            'UploadDate': datetime.utcnow().isoformat(),
            'S3Location': f"s3://{BUCKET_NAME}/{s3_key}",
            'ExtractedFields': final_data.get('fields', {}),
            'FieldCount': field_count,
            'ProcessingStatus': 'Completed',
            'ExtractionMetadata': {
                'textract_blocks': len(textract_response.get('Blocks', [])),
                'extracted_fields': field_count,
                'avg_field_confidence': round(avg_confidence, 2),
                'processing_engine': 'Textract+Claude+Regex'
            }
        }
        
        # Save to DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item=result)
        
        # Send SNS notification
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f'Document Processed: {final_data.get("document_type", "Unknown")}',
            Message=f'Successfully processed document {doc_id} with {len(final_data.get("fields", {}))} fields extracted.'
        )
        
        return _response(200, result)
        
    except Exception as e:
        logger.exception("Process handler error")
        return _response(500, {'error': 'internal server error', 'detail': str(e)})

def extract_file_from_multipart(body):
    """Extract file content from multipart form data"""
    # Simplified multipart parsing - in production use proper parser
    boundary_start = body.find(b'Content-Type: application/pdf')
    if boundary_start == -1:
        boundary_start = body.find(b'Content-Type: image/')
    
    if boundary_start != -1:
        content_start = body.find(b'\r\n\r\n', boundary_start) + 4
        content_end = body.rfind(b'\r\n--')
        return body[content_start:content_end]
    
    return body

def extract_text_from_textract(response):
    """Extract text from Textract response"""
    text_blocks = []
    for block in response.get('Blocks', []):
        if block['BlockType'] == 'LINE':
            text_blocks.append(block['Text'])
    return '\n'.join(text_blocks)

def extract_with_claude(text):
    """Advanced Claude AI with streaming and optimized prompts"""
    
    # Token-optimized text chunking
    text_chunks = chunk_text_optimally(text, max_tokens=6000)
    all_fields = {}
    
    for i, chunk in enumerate(text_chunks):
        chunk_fields = process_text_chunk(chunk, i)
        all_fields.update(chunk_fields)
    
    # Merge and validate results
    return merge_field_results(all_fields)

def chunk_text_optimally(text, max_tokens=6000):
    """Smart text chunking with context preservation"""
    # Estimate tokens (4 chars ≈ 1 token)
    max_chars = max_tokens * 4
    
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    lines = text.split('\n')
    current_chunk = ""
    
    for line in lines:
        if len(current_chunk + line) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = line
        else:
            current_chunk += "\n" + line
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def process_text_chunk(text, chunk_index):
    """Process individual text chunk with advanced prompting"""
    
    # Advanced prompt with few-shot examples
    prompt = f"""<role>Expert tax document parser with 99.5% field accuracy</role>

<examples>
Input: "Employee: John Smith\nSSN: 123-45-6789\nWages: $50,000.00"
Output: {{"employee_name": {{"value": "John Smith", "confidence": 0.98}}, "employee_ssn": {{"value": "123-45-6789", "confidence": 0.99}}, "wages_tips_compensation": {{"value": "50000.00", "confidence": 0.97}}}}
</examples>

<document_text>
{text}
</document_text>

<extraction_rules>
1. Extract ONLY visible text values
2. Normalize currency: remove $, commas
3. Validate SSN/EIN format: XXX-XX-XXXX or XX-XXXXXXX
4. Confidence: 0.95+ for clear text, 0.8+ for partial, 0.6+ for inferred
5. Skip empty/unclear fields
</extraction_rules>

<field_definitions>
W-2: employer_name, employer_address, employer_ein, employee_name, employee_ssn, wages_tips_compensation, federal_income_tax_withheld, social_security_wages, social_security_tax_withheld, medicare_wages_tips, medicare_tax_withheld
1099: payer_name, payer_tin, recipient_name, recipient_tin, nonemployee_compensation, federal_income_tax_withheld
Invoice: vendor_name, invoice_number, invoice_date, total_amount
</field_definitions>

Return JSON only:
{{"document_type": "W-2|1099-NEC|1099-MISC|Invoice|Other", "fields": {{"field_name": {{"value": "clean_value", "confidence": 0.95}}}}}}"""

    try:
        # Streaming response for better performance
        response = bedrock.invoke_model_with_response_stream(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.05,  # Lower for consistency
                "top_p": 0.9,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        # Collect streaming response
        full_response = ""
        for event in response['body']:
            if 'chunk' in event:
                chunk_data = json.loads(event['chunk']['bytes'])
                if chunk_data['type'] == 'content_block_delta':
                    full_response += chunk_data['delta']['text']
        
        # Enhanced JSON extraction with multiple fallbacks
        return extract_json_with_fallbacks(full_response)
        
    except Exception as e:
        logger.error(f"Claude chunk {chunk_index} failed: {e}")
        return apply_advanced_regex_fallback(text)

def extract_json_with_fallbacks(response_text):
    """Robust JSON extraction with multiple strategies"""
    import re
    
    # Strategy 1: Standard JSON block
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Strategy 2: Extract field patterns
    field_pattern = r'"([^"]+)":\s*\{[^}]*"value":\s*"([^"]*)",\s*"confidence":\s*([0-9.]+)'
    matches = re.findall(field_pattern, response_text)
    
    if matches:
        fields = {}
        for field_name, value, confidence in matches:
            fields[field_name] = {
                "value": value,
                "confidence": float(confidence)
            }
        return {"document_type": "Unknown", "fields": fields}
    
    # Strategy 3: Simple key-value extraction
    kv_pattern = r'([a-z_]+):\s*([^\n,}]+)'
    kv_matches = re.findall(kv_pattern, response_text.lower())
    
    if kv_matches:
        fields = {}
        for key, value in kv_matches[:10]:  # Limit to prevent noise
            fields[key] = {
                "value": value.strip('"\' '),
                "confidence": 0.7
            }
        return {"document_type": "Other", "fields": fields}
    
    return {"document_type": "Unknown", "fields": {}}

def apply_advanced_regex_fallback(text):
    """Advanced regex with field-specific patterns"""
    import re
    
    fields = {}
    
    # High-precision patterns
    patterns = {
        'employee_ssn': (r'\b\d{3}-\d{2}-\d{4}\b', 0.95),
        'employer_ein': (r'\b\d{2}-\d{7}\b', 0.95),
        'wages_tips_compensation': (r'\$?([\d,]+\.\d{2})(?=\s|$)', 0.85),
        'federal_income_tax_withheld': (r'Federal.*?\$?([\d,]+\.\d{2})', 0.80),
        'employee_name': (r'Employee:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', 0.90),
        'employer_name': (r'Employer:?\s*([A-Z][^\n]{10,50})', 0.85),
        'invoice_number': (r'(?:Invoice|INV)\s*#?\s*([A-Z0-9-]{3,15})', 0.90),
        'total_amount': (r'Total:?\s*\$?([\d,]+\.\d{2})', 0.85)
    }
    
    for field, (pattern, confidence) in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            value = matches[0] if isinstance(matches[0], str) else matches[0]
            # Clean value
            if 'amount' in field or 'wage' in field:
                value = re.sub(r'[^\d.]', '', value)
            fields[field] = {
                "value": value,
                "confidence": confidence,
                "source": "advanced_regex"
            }
    
    return {"document_type": "Other", "fields": fields}

def merge_field_results(all_fields):
    """Merge results from multiple chunks with conflict resolution"""
    merged = {"document_type": "Unknown", "fields": {}}
    
    # Determine document type from field patterns
    field_names = set(all_fields.keys())
    if any(f in field_names for f in ['employee_ssn', 'employer_ein', 'wages_tips_compensation']):
        merged["document_type"] = "W-2"
    elif any(f in field_names for f in ['payer_tin', 'nonemployee_compensation']):
        merged["document_type"] = "1099-NEC"
    elif any(f in field_names for f in ['invoice_number', 'vendor_name']):
        merged["document_type"] = "Invoice"
    
    # Merge fields with confidence-based conflict resolution
    for field_name, field_data in all_fields.items():
        if field_name not in merged["fields"]:
            merged["fields"][field_name] = field_data
        else:
            # Keep higher confidence value
            existing_conf = merged["fields"][field_name].get("confidence", 0)
            new_conf = field_data.get("confidence", 0)
            if new_conf > existing_conf:
                merged["fields"][field_name] = field_data
    
    return merged

def validate_extracted_fields(data):
    """Advanced field validation with format checking"""
    import re
    
    fields = data.get('fields', {})
    validated_fields = {}
    
    for field_name, field_data in fields.items():
        if not isinstance(field_data, dict):
            continue
            
        value = str(field_data.get('value', '')).strip()
        confidence = field_data.get('confidence', 0.5)
        
        # Skip empty values
        if not value:
            continue
        
        # Field-specific validation and normalization
        if 'ssn' in field_name:
            # SSN: XXX-XX-XXXX
            clean_ssn = re.sub(r'[^\d]', '', value)
            if len(clean_ssn) == 9:
                value = f"{clean_ssn[:3]}-{clean_ssn[3:5]}-{clean_ssn[5:]}"
                confidence = min(confidence + 0.1, 1.0)
            elif not re.match(r'\d{3}-\d{2}-\d{4}', value):
                continue  # Skip invalid SSN
        
        elif 'ein' in field_name or 'tin' in field_name:
            # EIN: XX-XXXXXXX
            clean_ein = re.sub(r'[^\d]', '', value)
            if len(clean_ein) == 9:
                value = f"{clean_ein[:2]}-{clean_ein[2:]}"
                confidence = min(confidence + 0.1, 1.0)
            elif not re.match(r'\d{2}-\d{7}', value):
                continue  # Skip invalid EIN
        
        elif any(x in field_name for x in ['amount', 'wage', 'tax', 'compensation']):
            # Currency: clean and validate
            clean_amount = re.sub(r'[^\d.]', '', value)
            if re.match(r'^\d+\.\d{2}$', clean_amount):
                value = clean_amount
                confidence = min(confidence + 0.05, 1.0)
            elif re.match(r'^\d+$', clean_amount):
                value = f"{clean_amount}.00"
                confidence = max(confidence - 0.1, 0.1)
            else:
                continue  # Skip invalid amounts
        
        elif 'date' in field_name:
            # Date normalization
            date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', value)
            if date_match:
                month, day, year = date_match.groups()
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                value = f"{month.zfill(2)}/{day.zfill(2)}/{year}"
                confidence = min(confidence + 0.05, 1.0)
        
        elif 'name' in field_name or 'address' in field_name:
            # Name/address cleaning
            value = re.sub(r'\s+', ' ', value).title()
            if len(value) < 3:
                continue  # Skip too short names
        
        # Quality score adjustment
        if len(value) > 100:
            confidence = max(confidence - 0.2, 0.1)  # Penalize very long values
        
        validated_fields[field_name] = {
            "value": value,
            "confidence": round(confidence, 3),
            "validated": True
        }
    
    data['fields'] = validated_fields
    return data

def apply_regex_fallback(text, extracted_data):
    """Final regex fallback with advanced pattern matching"""
    import re
    
    fields = extracted_data.get('fields', {})
    
    # Get missing critical fields only
    critical_fields = {
        'employee_ssn': r'(?:SSN|Social Security)\s*:?\s*(\d{3}-\d{2}-\d{4})',
        'employer_ein': r'(?:EIN|Employer ID)\s*:?\s*(\d{2}-\d{7})',
        'wages_tips_compensation': r'(?:Wages|Box 1)\s*:?\s*\$?([\d,]+\.\d{2})',
        'federal_income_tax_withheld': r'(?:Federal|Box 2)\s*:?\s*\$?([\d,]+\.\d{2})',
        'employee_name': r'(?:Employee|Name)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        'employer_name': r'(?:Employer|Company)\s*:?\s*([A-Z][^\n]{5,40})',
    }
    
    for field, pattern in critical_fields.items():
        if field not in fields:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                value = matches[0].strip()
                # Additional validation
                if field == 'employee_ssn' and len(re.sub(r'[^\d]', '', value)) != 9:
                    continue
                if field == 'employer_ein' and len(re.sub(r'[^\d]', '', value)) != 9:
                    continue
                    
                fields[field] = {
                    'value': value,
                    'confidence': 0.75,
                    'source': 'regex_fallback'
                }
    
    extracted_data['fields'] = fields
    return extracted_data

def detect_format(header):
    """Detect file format from magic bytes"""
    if header.startswith(b"\x89PNG\r\n\x1a\n"): return "png"
    if header[:2] == b"\xff\xd8": return "jpeg"
    if header[:4] == b"%PDF": return "pdf"
    if header[:4] in (b"II*\x00", b"MM\x00*"): return "tiff"
    return "unknown"

def process_uploaded_document(file_content, filename):
    """Process uploaded document with proper format handling"""
    doc_id = str(uuid.uuid4())
    
    try:
        # Validate file size
        if len(file_content) > 10 * 1024 * 1024:
            return _response(413, {'error': 'File too large - max 10MB'})
        
        # Detect actual format
        magic = file_content[:8]
        fmt = detect_format(magic)
        logger.info(f"Processing {fmt} file: {len(file_content)} bytes, magic: {list(magic[:4])}")
        
        if not file_content:
            return _response(400, {'error': 'Empty file content after decoding'})
        
        if fmt == "unknown":
            return _response(400, {'error': 'Unsupported format', 'magic': list(magic)})
        
        # Call Textract with correct method based on format
        if fmt in ("png", "jpeg"):
            # Use bytes for PNG/JPEG
            textract_response = textract.analyze_document(
                Document={'Bytes': file_content},
                FeatureTypes=['FORMS', 'TABLES']
            )
        elif fmt in ("pdf", "tiff"):
            # Use S3 for PDF/TIFF (safer cross-SDK)
            s3_key = f"tmp/{doc_id}_{filename}"
            s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=file_content)
            textract_response = textract.analyze_document(
                Document={'S3Object': {'Bucket': BUCKET_NAME, 'Name': s3_key}},
                FeatureTypes=['FORMS', 'TABLES']
            )
        else:
            return _response(400, {'error': f'Unsupported format: {fmt}'})
        
        # Extract raw text
        raw_text = extract_text_from_textract(textract_response)
        
        # Step 2: Claude AI extraction
        extracted_data = extract_with_claude(raw_text)
        
        # Step 3: Regex fallback
        final_data = apply_regex_fallback(raw_text, extracted_data)
        
        # Enhanced result with field-level confidence
        field_count = len(final_data.get('fields', {}))
        avg_confidence = sum(f.get('confidence', 0.5) for f in final_data.get('fields', {}).values() if isinstance(f, dict)) / max(field_count, 1)
        
        result = {
            'DocumentID': doc_id,
            'DocumentType': final_data.get('document_type', 'Unknown'),
            'ClassificationConfidence': final_data.get('confidence', 0.95),
            'FieldExtractionConfidence': round(avg_confidence, 2),
            'UploadDate': datetime.utcnow().isoformat(),
            'ExtractedFields': final_data.get('fields', {}),
            'FieldCount': field_count,
            'ProcessingStatus': 'Completed',
            'ExtractionMetadata': {
                'textract_blocks': len(textract_response.get('Blocks', [])),
                'extracted_fields': field_count,
                'avg_field_confidence': round(avg_confidence, 2),
                'processing_engine': 'Textract+Claude+Regex'
            }
        }
        
        return _response(200, result)
        
    except Exception as e:
        logger.exception(f"Document processing error for {filename}")
        return _response(500, {'error': 'processing failed', 'detail': str(e)})