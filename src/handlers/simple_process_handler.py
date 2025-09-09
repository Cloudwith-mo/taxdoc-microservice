import json
import base64
import boto3
import uuid
import re
from datetime import datetime

def lambda_handler(event, context):
    """Simple document processing handler"""
    
    print(f"Event: {json.dumps(event)}")
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    # Handle OPTIONS for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'document.pdf')
        content_base64 = body.get('contentBase64', '')
        
        if not content_base64:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No contentBase64 provided'})
            }
        
        # Clean and decode base64
        content_base64 = re.sub(r'^data:.*;base64,', '', content_base64, flags=re.I)
        content_base64 = re.sub(r'\s+', '', content_base64)
        
        try:
            document_bytes = base64.b64decode(content_base64)
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Invalid base64 content: {str(e)}'})
            }
        
        if not document_bytes:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Empty document'})
            }
        
        # Use Textract to extract text
        textract = boto3.client('textract')
        
        try:
            response = textract.detect_document_text(Document={'Bytes': document_bytes})
            
            # Extract text lines
            text_lines = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_lines.append(block.get('Text', ''))
            
            full_text = '\n'.join(text_lines)
            
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': f'Textract failed: {str(e)}'})
            }
        
        if not full_text.strip():
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'No text found in document'})
            }
        
        # Simple document classification
        doc_type = classify_document(full_text)
        
        # Extract basic fields
        fields = extract_basic_fields(full_text, doc_type)
        
        # Create key-value pairs for frontend
        key_values = []
        for key, value in fields.items():
            if value:
                key_values.append({
                    'key': key,
                    'value': str(value)
                })
        
        # Generate response
        doc_id = str(uuid.uuid4())
        
        result = {
            'docId': doc_id,
            'docType': doc_type,
            'docTypeConfidence': 0.85,
            'summary': f'Successfully processed {doc_type} document',
            'fields': fields,
            'keyValues': key_values
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def classify_document(text):
    """Simple document classification based on keywords"""
    text_lower = text.lower()
    
    if 'w-2' in text_lower or 'wage and tax statement' in text_lower:
        return 'W-2'
    elif '1099-nec' in text_lower:
        return '1099-NEC'
    elif '1099-misc' in text_lower:
        return '1099-MISC'
    elif 'invoice' in text_lower and ('total' in text_lower or 'amount' in text_lower):
        return 'INVOICE'
    elif 'receipt' in text_lower:
        return 'RECEIPT'
    else:
        return 'UNKNOWN'

def extract_basic_fields(text, doc_type):
    """Extract basic fields based on document type"""
    fields = {}
    lines = text.split('\n')
    
    if doc_type == 'W-2':
        # Look for W-2 specific patterns
        for line in lines:
            line = line.strip()
            if 'wages' in line.lower() and any(c.isdigit() for c in line):
                fields['Wages'] = extract_amount(line)
            elif 'federal' in line.lower() and 'tax' in line.lower():
                fields['Federal Tax Withheld'] = extract_amount(line)
            elif 'social security' in line.lower() and 'wages' in line.lower():
                fields['Social Security Wages'] = extract_amount(line)
    
    elif doc_type in ['INVOICE', 'RECEIPT']:
        # Look for common invoice/receipt fields
        for line in lines:
            line = line.strip()
            if 'total' in line.lower() and any(c.isdigit() for c in line):
                fields['Total Amount'] = extract_amount(line)
            elif 'date' in line.lower():
                date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', line)
                if date_match:
                    fields['Date'] = date_match.group()
    
    # Extract any key-value pairs with colons
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value and len(key) < 50 and len(value) < 200:
                    fields[key] = value
    
    return fields

def extract_amount(text):
    """Extract monetary amount from text"""
    # Look for patterns like $123.45 or 123.45
    amount_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
    if amount_match:
        return amount_match.group(1)
    return None