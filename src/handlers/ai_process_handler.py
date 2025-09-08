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
BUCKET_NAME = 'taxdoc-documents-bucket'
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
            
            # Decode base64 content
            file_content = base64.b64decode(content_base64)
            
            # Determine file type and validate
            file_ext = filename.lower().split('.')[-1]
            if file_ext not in ['png', 'jpg', 'jpeg', 'pdf']:
                return _response(400, {'error': f'Unsupported file type: {file_ext}'})
            
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
    """Enhanced Claude AI for Parseur-level field extraction"""
    
    prompt = f"""You are an expert document parser. Extract ALL fields from this tax document with high precision.

Document Text:
{text[:4000]}

Extract these fields with confidence scores (0.0-1.0):

W-2 Fields:
- employer_name, employer_address, employer_ein
- employee_name, employee_address, employee_ssn
- wages_tips_compensation, federal_income_tax_withheld
- social_security_wages, social_security_tax_withheld
- medicare_wages_tips, medicare_tax_withheld
- state_wages_tips, state_income_tax, locality_name

1099 Fields:
- payer_name, payer_address, payer_tin
- recipient_name, recipient_address, recipient_tin
- nonemployee_compensation, federal_income_tax_withheld
- state_tax_withheld, state_payer_state_no

Invoice/Receipt Fields:
- vendor_name, vendor_address, invoice_number, invoice_date
- total_amount, tax_amount, line_items

Return ONLY valid JSON:
{{
  "document_type": "W-2|1099-NEC|1099-MISC|Invoice|Receipt|Other",
  "confidence": 0.95,
  "fields": {{
    "field_name": {{"value": "extracted_value", "confidence": 0.95, "location": "box_1"}}
  }}
}}"""

    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        claude_response = result['content'][0]['text']
        
        # Enhanced JSON parsing
        import re
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', claude_response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            # Validate and enhance fields
            return validate_extracted_fields(parsed)
        
    except Exception as e:
        logger.error(f"Claude extraction failed: {e}")
    
    return {"document_type": "Unknown", "confidence": 0.5, "fields": {}}

def validate_extracted_fields(data):
    """Validate and enhance extracted field data"""
    fields = data.get('fields', {})
    
    # Normalize field values
    for field_name, field_data in fields.items():
        if isinstance(field_data, dict):
            value = field_data.get('value', '')
            # Clean currency values
            if 'amount' in field_name or 'wage' in field_name or 'tax' in field_name:
                value = re.sub(r'[^\d.,]', '', str(value))
            # Clean TIN/SSN
            if 'tin' in field_name or 'ssn' in field_name or 'ein' in field_name:
                value = re.sub(r'[^\d-]', '', str(value))
            field_data['value'] = value
    
    return data

def apply_regex_fallback(text, extracted_data):
    """Enhanced regex patterns for missing critical fields"""
    import re
    
    fields = extracted_data.get('fields', {})
    
    # Enhanced patterns with validation
    patterns = {
        'employer_ein': r'\b\d{2}-\d{7}\b',
        'employee_ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'payer_tin': r'\b\d{2}-\d{7}\b',
        'recipient_tin': r'\b\d{3}-\d{2}-\d{4}\b',
        'wages_tips_compensation': r'\$?[\d,]+\.\d{2}',
        'federal_income_tax_withheld': r'Federal.*?\$?[\d,]+\.\d{2}',
        'nonemployee_compensation': r'\$?[\d,]+\.\d{2}',
        'invoice_number': r'(?:Invoice|INV)\s*#?\s*([A-Z0-9-]+)',
        'invoice_date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    }
    
    for field, pattern in patterns.items():
        if field not in fields or not fields.get(field, {}).get('value'):
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                fields[field] = {
                    'value': matches[0] if isinstance(matches[0], str) else matches[0],
                    'confidence': 0.7,
                    'source': 'regex_fallback'
                }
    
    extracted_data['fields'] = fields
    return extracted_data

def process_uploaded_document(file_content, filename):
    """Process uploaded document content directly"""
    doc_id = str(uuid.uuid4())
    
    try:
        # Textract supports PNG directly, no conversion needed
        logger.info(f"Processing {filename} with {len(file_content)} bytes")
        
        # Process with Textract using document bytes (supports PNG, JPEG, PDF)
        textract_response = textract.detect_document_text(
            Document={'Bytes': file_content}
        )
        
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