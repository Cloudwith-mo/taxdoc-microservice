import json
import boto3
from typing import Dict, Any, List
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.textract_service import TextractService
from services.enhanced_classifier import EnhancedClassifier
from services.multi_form_extractor import MultiFormExtractor
from services.storage_service import StorageService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """SQS processor for document processing jobs"""
    
    print(f"Processing SQS event: {json.dumps(event)}")
    
    # Process each SQS record
    for record in event.get('Records', []):
        try:
            # Parse SQS message
            message_body = json.loads(record['body'])
            bucket = message_body['bucket']
            key = message_body['key']
            job_id = message_body.get('job_id', key.split('/')[-1])
            
            print(f"Processing job {job_id}: s3://{bucket}/{key}")
            
            # Initialize services
            textract = TextractService()
            classifier = EnhancedClassifier()
            extractor = MultiFormExtractor()
            storage = StorageService()
            
            # Start async Textract job
            textract_job_id = textract.start_async_analysis(bucket, key)
            
            # Update job status
            storage.update_job_status(job_id, {
                'ProcessingStatus': 'TextractStarted',
                'TextractJobId': textract_job_id
            })
            
            print(f"Started Textract job {textract_job_id} for {job_id}")
            
        except Exception as e:
            print(f"Error processing SQS record: {str(e)}")
            # Update job with error status
            try:
                storage = StorageService()
                storage.update_job_status(job_id, {
                    'ProcessingStatus': 'Failed',
                    'Error': str(e)
                })
            except:
                pass
    
    return {'statusCode': 200, 'body': 'Processed'}