import json
import boto3
import base64
from typing import Dict, Any
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.textract_service import TextractService
from services.enhanced_classifier import EnhancedClassifier
from services.multi_form_extractor import MultiFormExtractor
from services.storage_service import StorageService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway handler for synchronous document processing"""
    
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        if http_method == 'POST' and path == '/process-document':
            return process_document_sync(event)
        elif http_method == 'GET' and '/result/' in path:
            doc_id = event['pathParameters']['doc_id']
            return get_processing_result(doc_id)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def process_document_sync(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process document synchronously via API using real AWS services only"""
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'unknown')
        file_content = body.get('file_content')  # Base64 encoded file
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No file content provided'})
            }
        
        # Decode base64 file content
        document_bytes = base64.b64decode(file_content)
        
        # Initialize services
        textract_service = TextractService()
        classifier = EnhancedClassifier()
        extractor = MultiFormExtractor()
        
        # Step 1: Extract text with Textract
        textract_response = textract_service.detect_document_text(document_bytes)
        
        # Step 2: Classify document type
        doc_type, classification_confidence = classifier.classify_document(textract_response)
        
        # Step 3: Extract fields using multi-form extractor
        extraction_result = extractor.extract_document_fields(
            document_bytes=document_bytes,
            document_type=doc_type
        )
        
        # Format result for API response
        import time
        result = {
            "DocumentID": filename,
            "DocumentType": extraction_result.get('DocumentType', doc_type),
            "ClassificationConfidence": classification_confidence,
            "UploadDate": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "S3Location": f"api-upload/{filename}",
            "ProcessingStatus": "Completed",
            "Data": {}
        }
        
        # Extract actual data fields from extraction result
        exclude_fields = ['DocumentType', 'ExtractionMetadata']
        for key, value in extraction_result.items():
            if key not in exclude_fields:
                result['Data'][key] = value
        
        # Add extraction metadata
        if 'ExtractionMetadata' in extraction_result:
            result['ExtractionMetadata'] = extraction_result['ExtractionMetadata']
        
        # Store in DynamoDB
        storage = StorageService()
        storage.save_document_metadata(result)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Processing failed: {str(e)}'})
        }

def get_processing_result(doc_id: str) -> Dict[str, Any]:
    """Get processing result by document ID"""
    
    try:
        storage = StorageService()
        result = storage.get_document_metadata(doc_id)
        
        if result:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Document not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

