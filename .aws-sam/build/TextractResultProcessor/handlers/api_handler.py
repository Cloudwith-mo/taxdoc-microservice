import json
import boto3
import base64
import time
from typing import Dict, Any
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.any_doc_processor import AnyDocProcessor
from services.storage_service import StorageService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway handler for Any-Doc processing"""
    
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        if http_method == 'POST' and path == '/process-document':
            return process_document_sync(event)
        elif http_method == 'POST' and path == '/process-batch':
            return process_batch_documents(event)
        elif http_method == 'GET' and '/result/' in path:
            doc_id = event['pathParameters']['doc_id']
            return get_processing_result(doc_id)
        elif http_method == 'GET' and path == '/supported-types':
            return get_supported_types()
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
    """Process any document type synchronously via API using Any-Doc processor"""
    
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
        
        # Initialize Any-Doc processor
        processor = AnyDocProcessor()
        
        # Process document through complete pipeline
        processing_result = processor.process_document(document_bytes, filename)
        
        # Format result for API response
        result = {
            "DocumentID": filename,
            "DocumentType": processing_result.get('DocumentType', 'Unknown'),
            "UploadDate": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "S3Location": f"api-upload/{filename}",
            "ProcessingStatus": "Completed" if processing_result.get('QualityMetrics', {}).get('overall_confidence', 0) > 0 else "Failed",
            "ProcessingMetadata": processing_result.get('ProcessingMetadata', {}),
            "QualityMetrics": processing_result.get('QualityMetrics', {}),
            "Data": processing_result.get('ExtractedData', {}),
            "ExtractionMetadata": processing_result.get('ExtractionMetadata', {})
        }
        
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

def process_batch_documents(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process multiple documents in batch"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        files = body.get('files', [])
        
        if not files:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No files provided'})
            }
        
        # Prepare files for batch processing
        batch_files = []
        for i, file_data in enumerate(files):
            batch_files.append({
                'id': file_data.get('id', f'batch_{i}'),
                'filename': file_data.get('filename', f'unknown_{i}'),
                'bytes': base64.b64decode(file_data['file_content'])
            })
        
        # Process batch
        processor = AnyDocProcessor()
        results = processor.process_batch(batch_files)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'batch_id': f'batch_{len(files)}_{int(time.time())}',
                'total_files': len(files),
                'results': results
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Batch processing failed: {str(e)}'})
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

def get_supported_types() -> Dict[str, Any]:
    """Get list of supported file types"""
    
    try:
        processor = AnyDocProcessor()
        supported_types = processor.get_supported_file_types()
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'supported_types': supported_types,
                'total_types': len(supported_types)
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }