"""
DocumentGPT Lambda Handler
Handles document upload and processing requests
"""

import json
import boto3
import base64
import uuid
from datetime import datetime, timedelta
import os

s3_client = boto3.client('s3')
textract_client = boto3.client('textract')

# Configuration
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'documentgpt-uploads')
UPLOAD_URL_EXPIRY = 300  # 5 minutes

def create_response(status_code, body, headers=None):
    """Create HTTP response with CORS headers"""
    default_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body) if not isinstance(body, str) else body
    }

def handler(event, context):
    """Main Lambda handler"""
    
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, '')
    
    # Get the path to determine which endpoint was called
    path = event.get('path', '')
    method = event.get('httpMethod', '')
    
    try:
        if path.endswith('/upload-url') and method == 'POST':
            return handle_upload_url(event)
        elif path.endswith('/process-document') and method == 'POST':
            return handle_process_document(event)
        else:
            return create_response(404, {'error': 'Endpoint not found'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {'error': str(e)})

def handle_upload_url(event):
    """Generate presigned URL for S3 upload"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'document')
        content_type = body.get('contentType', 'application/octet-stream')
        
        # Generate unique document ID
        document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Generate S3 key
        file_extension = filename.split('.')[-1] if '.' in filename else 'bin'
        s3_key = f"uploads/{document_id}/{filename}"
        
        # Generate presigned URL for upload
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=UPLOAD_URL_EXPIRY
        )
        
        return create_response(200, {
            'uploadUrl': presigned_url,
            'documentId': document_id,
            's3Key': s3_key
        })
    
    except Exception as e:
        print(f"Error generating upload URL: {str(e)}")
        return create_response(500, {'error': f'Failed to generate upload URL: {str(e)}'})

def handle_process_document(event):
    """Process uploaded document with Textract"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Check if we have base64 content (direct upload) or documentId (S3 upload)
        if 'contentBase64' in body:
            # Direct base64 upload
            return process_base64_document(body)
        elif 'documentId' in body:
            # S3 upload
            return process_s3_document(body)
        else:
            return create_response(400, {'error': 'Missing contentBase64 or documentId'})
    
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return create_response(500, {'error': f'Failed to process document: {str(e)}'})

def process_base64_document(body):
    """Process document from base64 content"""
    
    try:
        filename = body.get('filename', 'document')
        content_base64 = body.get('contentBase64', '')
        
        # Decode base64 content
        document_bytes = base64.b64decode(content_base64)
        
        # Call Textract
        response = textract_client.detect_document_text(
            Document={'Bytes': document_bytes}
        )
        
        # Extract text and key-value pairs
        extracted_data = extract_textract_data(response)
        
        # Determine document type
        doc_type = determine_document_type(extracted_data.get('text', ''))
        
        return create_response(200, {
            'docType': doc_type,
            'docTypeConfidence': 0.85,
            'fields': extracted_data.get('fields', {}),
            'keyValues': extracted_data.get('keyValues', []),
            'text': extracted_data.get('text', ''),
            'filename': filename,
            'processedAt': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error processing base64 document: {str(e)}")
        return create_response(500, {'error': f'Failed to process document: {str(e)}'})

def process_s3_document(body):
    """Process document from S3"""
    
    try:
        document_id = body.get('documentId')
        filename = body.get('filename', 'document')
        
        # Construct S3 key
        s3_key = f"uploads/{document_id}/{filename}"
        
        # Call Textract with S3 document
        response = textract_client.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': S3_BUCKET,
                    'Name': s3_key
                }
            }
        )
        
        # Extract text and key-value pairs
        extracted_data = extract_textract_data(response)
        
        # Determine document type
        doc_type = determine_document_type(extracted_data.get('text', ''))
        
        return create_response(200, {
            'docType': doc_type,
            'docTypeConfidence': 0.85,
            'fields': extracted_data.get('fields', {}),
            'keyValues': extracted_data.get('keyValues', []),
            'text': extracted_data.get('text', ''),
            'filename': filename,
            'documentId': document_id,
            'processedAt': datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"Error processing S3 document: {str(e)}")
        return create_response(500, {'error': f'Failed to process document: {str(e)}'})

def extract_textract_data(textract_response):
    """Extract text and structured data from Textract response"""
    
    extracted_text = []
    key_values = []
    fields = {}
    
    # Extract all text
    for block in textract_response.get('Blocks', []):
        if block['BlockType'] == 'LINE':
            extracted_text.append(block.get('Text', ''))
    
    full_text = '\n'.join(extracted_text)
    
    # Extract common fields based on patterns
    fields = extract_common_fields(full_text)
    
    # Create key-value pairs from detected fields
    for key, value in fields.items():
        if value:
            key_values.append({
                'key': key.replace('_', ' ').title(),
                'value': value
            })
    
    return {
        'text': full_text,
        'fields': fields,
        'keyValues': key_values
    }

def extract_common_fields(text):
    """Extract common fields from document text"""
    
    import re
    
    fields = {}
    
    # Extract date patterns
    date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
    dates = re.findall(date_pattern, text)
    if dates:
        fields['document_date'] = dates[0]
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    if emails:
        fields['email'] = emails[0]
    
    # Extract phone numbers
    phone_pattern = r'\b(\+?1?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})\b'
    phones = re.findall(phone_pattern, text)
    if phones:
        fields['phone'] = phones[0]
    
    # Extract amounts/currency
    amount_pattern = r'\$[\d,]+\.?\d*'
    amounts = re.findall(amount_pattern, text)
    if amounts:
        fields['total_amount'] = amounts[0]
    
    # Extract names (simple heuristic - lines with proper case)
    lines = text.split('\n')
    for line in lines[:10]:  # Check first 10 lines
        if line and line[0].isupper() and ' ' in line and len(line) < 50:
            # Likely a name
            if 'name' not in fields:
                fields['name'] = line.strip()
    
    # Extract address (multi-line pattern)
    address_lines = []
    zip_pattern = r'\b\d{5}(-\d{4})?\b'
    for i, line in enumerate(lines):
        if re.search(zip_pattern, line):
            # Found zip code, collect surrounding lines as address
            start = max(0, i-2)
            end = min(len(lines), i+1)
            address_lines = lines[start:end]
            fields['address'] = ' '.join(address_lines).strip()
            break
    
    return fields

def determine_document_type(text):
    """Determine document type based on content"""
    
    text_lower = text.lower()
    
    # Check for specific document types
    if 'invoice' in text_lower or 'bill to' in text_lower:
        return 'Invoice'
    elif 'receipt' in text_lower or 'payment received' in text_lower:
        return 'Receipt'
    elif 'contract' in text_lower or 'agreement' in text_lower:
        return 'Contract'
    elif 'form w-2' in text_lower or 'wage and tax' in text_lower:
        return 'W-2 Form'
    elif 'form 1099' in text_lower:
        return '1099 Form'
    elif 'resume' in text_lower or 'curriculum vitae' in text_lower:
        return 'Resume'
    elif 'statement' in text_lower and ('bank' in text_lower or 'account' in text_lower):
        return 'Bank Statement'
    elif 'pay stub' in text_lower or 'payroll' in text_lower:
        return 'Pay Stub'
    else:
        return 'General Document'

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'httpMethod': 'POST',
        'path': '/upload-url',
        'body': json.dumps({
            'filename': 'test.pdf',
            'contentType': 'application/pdf'
        })
    }
    
    result = handler(test_event, None)
    print(json.dumps(result, indent=2))