import json
import boto3
import base64
from typing import Dict, Any
from ..services.textract_service import TextractService
from ..services.classifier_service import ClassifierService
from ..services.extractor_service import ExtractorService
from ..services.storage_service import StorageService

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
    """Process document synchronously via API"""
    
    try:
        # Parse multipart form data (simplified)
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body)
        
        # For demo, assume file is uploaded to S3 first
        # In production, handle multipart upload properly
        bucket = 'taxdoc-uploads-dev'  # From environment
        key = 'api-uploads/temp-document.pdf'  # Generate unique key
        
        # Initialize services
        textract = TextractService()
        classifier = ClassifierService()
        extractor = ExtractorService()
        
        # Process document
        textract_response = textract.analyze_document(bucket, key)
        doc_type = classifier.classify_document(textract_response)
        extracted_data = extractor.extract_fields(textract_response, doc_type)
        
        # Return result immediately
        result = {
            "DocumentType": doc_type,
            "Data": extracted_data,
            "ProcessingStatus": "Completed"
        }
        
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
            'body': json.dumps({'error': str(e)})
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
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Document not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }