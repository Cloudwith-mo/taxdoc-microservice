"""
TaxDoc V1 MVP Handler
Simple tax document extraction for W-2 and 1099 forms
"""
import json
import boto3
import base64
import os
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
textract = boto3.client('textract')
s3 = boto3.client('s3')

# Import our services
import sys
sys.path.append('/opt/python')
sys.path.append('/var/task')

from services.tax_classifier import TaxClassifier
from services.tax_extractor import TaxExtractor

def lambda_handler(event, context):
    """
    Main handler for tax document processing
    Expects: POST /process-document with JSON body containing filename and base64 content
    """
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
                },
                'body': ''
            }
        
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
            
        filename = body.get('filename')
        file_content = body.get('file_content')
        
        if not filename or not file_content:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Missing filename or file_content',
                    'message': 'Please provide both filename and base64-encoded file content'
                })
            }
        
        # Decode file content
        try:
            file_bytes = base64.b64decode(file_content)
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Invalid base64 content',
                    'message': str(e)
                })
            }
        
        # Process document
        result = process_tax_document(file_bytes, filename)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Processing failed',
                'message': str(e)
            })
        }

def process_tax_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process tax document through extraction pipeline"""
    
    # Step 1: OCR with Textract
    logger.info(f"Processing document: {filename}")
    
    try:
        textract_response = textract.analyze_document(
            Document={'Bytes': file_bytes},
            FeatureTypes=['FORMS', 'TABLES']
        )
    except Exception as e:
        logger.error(f"Textract failed: {str(e)}")
        raise Exception(f"OCR processing failed: {str(e)}")
    
    # Step 2: Classify document type
    classifier = TaxClassifier()
    doc_type = classifier.classify_tax_document(textract_response)
    
    if doc_type == "Unsupported":
        return {
            'success': False,
            'error': 'Unsupported document type',
            'message': 'Only W-2 and 1099 tax forms are supported in this version',
            'filename': filename
        }
    
    # Step 3: Extract data using Claude
    extractor = TaxExtractor()
    extracted_data = extractor.extract_tax_data(textract_response, doc_type)
    
    # Step 4: Format response
    return {
        'success': True,
        'filename': filename,
        'document_type': doc_type,
        'extracted_data': extracted_data,
        'processing_info': {
            'ocr_blocks': len(textract_response.get('Blocks', [])),
            'extraction_method': 'Claude + Textract',
            'version': 'v1-mvp'
        }
    }

def handle_options(event, context):
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
        },
        'body': ''
    }