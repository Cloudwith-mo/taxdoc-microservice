import json
import base64
import boto3
from typing import Dict, Any
from services.tax_form_processor import TaxFormProcessor

def lambda_handler(event, context):
    """MVP API handler - simplified for W-2 and 1099 forms only"""
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', '')
        file_content = body.get('file_content', '')
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No file content provided'})
            }
        
        # Decode file
        document_bytes = base64.b64decode(file_content)
        
        # Process document
        processor = TaxFormProcessor()
        result = processor.process_tax_document(document_bytes, filename)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }