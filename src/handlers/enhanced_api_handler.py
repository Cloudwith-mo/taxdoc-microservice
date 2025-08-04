import json
import boto3
import base64
import time
from typing import Dict, Any
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.three_layer_orchestrator import ThreeLayerOrchestrator
from services.enhanced_classifier import EnhancedClassifier
from services.storage_service import StorageService
from services.monitoring_service import MonitoringService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Enhanced API Gateway handler with three-layer processing"""
    
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        # CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        if http_method == 'OPTIONS':
            return {'statusCode': 200, 'headers': cors_headers, 'body': ''}
        
        if http_method == 'POST' and path == '/process-document':
            return process_document_enhanced(event, cors_headers)
        elif http_method == 'GET' and '/result/' in path:
            doc_id = event['pathParameters']['doc_id']
            return get_processing_result(doc_id, cors_headers)
        elif http_method == 'GET' and '/download-excel/' in path:
            doc_id = event['pathParameters']['doc_id']
            return generate_excel_download(doc_id, cors_headers)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def process_document_enhanced(event: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Process document using enhanced three-layer pipeline"""
    
    start_time = time.time()
    monitoring = MonitoringService()
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'unknown')
        file_content = body.get('file_content')
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No file content provided'})
            }
        
        # Decode file
        document_bytes = base64.b64decode(file_content)
        
        # Step 1: Classify document
        classifier = EnhancedClassifier()
        # First get basic text for classification
        textract_basic = boto3.client('textract').detect_document_text(
            Document={'Bytes': document_bytes}
        )
        doc_type, confidence = classifier.classify_document(textract_basic)
        
        # Step 2: Three-layer extraction
        orchestrator = ThreeLayerOrchestrator()
        extraction_result = orchestrator.extract_document_fields(document_bytes, doc_type)
        
        # Step 3: Format result
        processing_time = time.time() - start_time
        result = {
            "DocumentID": filename,
            "DocumentType": doc_type,
            "ClassificationConfidence": confidence,
            "UploadDate": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ProcessingStatus": "Completed",
            "ProcessingTime": processing_time,
            "Data": extraction_result,
            "ExtractionMetadata": extraction_result.get('ExtractionMetadata', {})
        }
        
        # Step 4: Store results
        storage = StorageService()
        storage.save_document_metadata(result)
        
        # Step 5: Log enhanced metrics
        from services.cloudwatch_metrics import CloudWatchMetrics
        metrics = CloudWatchMetrics()
        
        metadata = extraction_result.get('ExtractionMetadata', {})
        metrics.put_document_processed(
            doc_type, 
            processing_time, 
            metadata.get('overall_confidence', 0)
        )
        metrics.put_layer_usage(
            metadata.get('processing_layers', []), 
            doc_type
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        from services.cloudwatch_metrics import CloudWatchMetrics
        metrics = CloudWatchMetrics()
        metrics.put_error_metric(type(e).__name__, 'EnhancedApiFunction')
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': f'Processing failed: {str(e)}',
                'processing_time': processing_time
            })
        }

def get_processing_result(doc_id: str, cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Get processing result by document ID"""
    
    try:
        storage = StorageService()
        result = storage.get_document_metadata(doc_id)
        
        if result:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Document not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }

def generate_excel_download(doc_id: str, cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Generate Excel download for document results"""
    
    try:
        storage = StorageService()
        result = storage.get_document_metadata(doc_id)
        
        if not result:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Document not found'})
            }
        
        # Generate presigned URL for Excel download
        s3 = boto3.client('s3')
        bucket = os.environ.get('UPLOAD_BUCKET')
        excel_key = f"excel-exports/{doc_id}.xlsx"
        
        # Create simple Excel content (in production, use openpyxl)
        excel_data = f"Document ID,{doc_id}\nDocument Type,{result.get('DocumentType', 'Unknown')}\n"
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket,
            Key=excel_key,
            Body=excel_data,
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Generate presigned URL
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': excel_key},
            ExpiresIn=3600
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'download_url': download_url})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }