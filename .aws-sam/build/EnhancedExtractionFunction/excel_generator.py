import json
import boto3
import os
from datetime import datetime
from typing import Dict, Any
import sys

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.storage_service import StorageService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Generate Excel file from processed document data"""
    
    try:
        # Get document ID from path parameters
        doc_id = event['pathParameters']['doc_id']
        print(f"Generating Excel for document: {doc_id}")
        
        # Retrieve document data from DynamoDB
        storage = StorageService()
        document_data = storage.get_document_metadata(doc_id)
        
        if not document_data:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({'error': 'Document not found'})
            }
        
        # Generate Excel content (simplified - in production use openpyxl)
        excel_content = generate_excel_content(document_data)
        
        # Upload to S3 and create presigned URL
        s3_client = boto3.client('s3')
        bucket_name = os.environ['UPLOAD_BUCKET']
        s3_key = f"exports/{doc_id}.xlsx"
        
        # Upload Excel content to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=excel_content,
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Generate presigned URL (valid for 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'downloadUrl': presigned_url,
                'filename': f"{doc_id}.xlsx"
            })
        }
        
    except Exception as e:
        print(f"Error generating Excel: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def generate_excel_content(document_data: Dict[str, Any]) -> bytes:
    """Generate Excel file content from document data"""
    
    # Simple CSV-like content (in production, use openpyxl for real Excel)
    csv_content = f"""TaxDoc Processing Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Document Information:
Document ID,{document_data.get('DocumentID', 'N/A')}
Document Type,{document_data.get('DocumentType', 'N/A')}
Upload Date,{document_data.get('UploadDate', 'N/A')}
Processing Status,{document_data.get('ProcessingStatus', 'N/A')}
S3 Location,{document_data.get('S3Location', 'N/A')}

Extracted Data:"""
    
    # Add extracted data fields
    data = document_data.get('Data', {})
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            data = {}
    
    for key, value in data.items():
        csv_content += f"\n{key},{value}"
    
    # Add summary if available
    if document_data.get('Summary'):
        csv_content += f"\n\nAI Summary:\n{document_data['Summary']}"
    
    # Add ML classification info if available
    if document_data.get('MLClassificationUsed'):
        csv_content += f"\n\nML Classification Used: Yes"
        csv_content += f"\nML Confidence: {document_data.get('MLConfidence', 0):.3f}"
    
    return csv_content.encode('utf-8')