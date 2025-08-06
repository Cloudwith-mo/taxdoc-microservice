"""
Enhanced API Handler with Three-Layer Extraction
Replaces MVP handler with comprehensive AI extraction
"""
import json
import boto3
import base64
import os
from typing import Dict, Any
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
textract = boto3.client('textract')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Import services
import sys
sys.path.append('/opt/python')
sys.path.append('/var/task')

from services.tax_classifier import TaxClassifier
from services.enhanced_tax_extractor import EnhancedTaxExtractor

def lambda_handler(event, context):
    """Enhanced handler with three-layer extraction"""
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
        
        # Process with enhanced three-layer extraction
        result = process_with_three_layers(file_bytes, filename)
        
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

def process_with_three_layers(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process document with three-layer extraction pipeline"""
    
    logger.info(f"Processing document with three-layer extraction: {filename}")
    
    # Step 1: OCR with Textract
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
            'message': 'Only W-2 and 1099 tax forms are supported',
            'filename': filename
        }
    
    # Step 3: Enhanced extraction with three layers
    extractor = EnhancedTaxExtractor()
    extracted_data = extractor.extract_with_three_layers(textract_response, doc_type)
    
    # Step 4: Format enhanced response
    return {
        'success': True,
        'filename': filename,
        'document_type': doc_type,
        'extracted_data': extracted_data,
        'processing_info': {
            'ocr_blocks': len(textract_response.get('Blocks', [])),
            'extraction_method': 'three_layer_pipeline',
            'layers_used': extracted_data.get('layers_used', []),
            'confidence_scores': extracted_data.get('confidence_scores', {}),
            'version': 'enhanced-v1'
        }
    }