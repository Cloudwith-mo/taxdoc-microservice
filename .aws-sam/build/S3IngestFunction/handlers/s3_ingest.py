import json
import boto3
from typing import Dict, Any
import uuid
import os

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """S3 event handler that queues documents for processing"""
    
    print(f"S3 ingest event: {json.dumps(event)}")
    
    sqs = boto3.client('sqs')
    queue_url = os.environ['PROCESSING_QUEUE_URL']
    
    try:
        # Process each S3 record
        for record in event.get('Records', []):
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Skip non-document files
            if not key.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.txt')):
                continue
            
            # Generate job ID
            job_id = str(uuid.uuid4())
            
            # Create SQS message
            message = {
                'job_id': job_id,
                'bucket': bucket,
                'key': key,
                'event_time': record['eventTime']
            }
            
            # Send to processing queue
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'DocumentType': {
                        'StringValue': 'unknown',
                        'DataType': 'String'
                    }
                }
            )
            
            print(f"Queued job {job_id} for s3://{bucket}/{key}")
        
        return {'statusCode': 200, 'body': 'Queued for processing'}
        
    except Exception as e:
        print(f"Error in S3 ingest: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}