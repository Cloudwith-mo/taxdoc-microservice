import json
import boto3
import os
from urllib.parse import unquote_plus

def lambda_handler(event, context):
    """S3 event handler - queues documents for processing"""
    
    sqs = boto3.client('sqs')
    queue_url = os.environ['PROCESSING_QUEUE_URL']
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        
        # Extract document ID from S3 key (format: doc_id/filename)
        doc_id = key.split('/')[0]
        filename = key.split('/')[-1]
        
        # Send to processing queue
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'DocumentID': doc_id,
                'S3Bucket': bucket,
                'S3Key': key,
                'FileName': filename
            })
        )
        
        print(f"Queued document {doc_id} for processing")
    
    return {'statusCode': 200}