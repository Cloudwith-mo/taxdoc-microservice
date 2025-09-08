import json
import boto3
import uuid
import os
from datetime import datetime, timedelta

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET', 'taxflowsai-uploads')
INGEST_QUEUE_URL = os.environ.get('INGEST_QUEUE_URL', '')

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS,GET",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Content-Type": "application/json"
}

def ret(code, body):
    return {
        "statusCode": code,
        "headers": CORS,
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    method = event.get('httpMethod', '')
    
    if method == 'OPTIONS':
        return {"statusCode": 200, "headers": CORS, "body": ""}
    
    if method == 'GET' and event.get('path', '').endswith('/upload-url'):
        # Generate presigned URL for upload
        filename = event.get('queryStringParameters', {}).get('filename', 'document.pdf')
        content_type = event.get('queryStringParameters', {}).get('contentType', 'application/pdf')
        
        key = f"uploads/{uuid.uuid4()}_{filename}"
        
        try:
            presigned_url = s3.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': UPLOAD_BUCKET,
                    'Key': key,
                    'ContentType': content_type
                },
                ExpiresIn=300  # 5 minutes
            )
            
            return ret(200, {
                "url": presigned_url,
                "key": key,
                "bucket": UPLOAD_BUCKET
            })
        except Exception as e:
            return ret(500, {"error": "Failed to generate upload URL", "detail": str(e)})
    
    if method == 'POST' and event.get('path', '').endswith('/process'):
        # Process document from S3 key
        try:
            body = json.loads(event.get('body', '{}'))
            s3_key = body.get('s3Key')
            filename = body.get('filename', 'document')
            user_id = body.get('userId', 'ANON')
            
            if not s3_key:
                return ret(400, {"error": "s3Key required"})
            
            doc_id = str(uuid.uuid4())
            
            # Send to processing queue
            message = {
                "Records": [{
                    "s3": {
                        "bucket": {"name": UPLOAD_BUCKET},
                        "object": {"key": s3_key}
                    }
                }],
                "userId": user_id,
                "docId": doc_id,
                "filename": filename
            }
            
            if INGEST_QUEUE_URL:
                sqs.send_message(
                    QueueUrl=INGEST_QUEUE_URL,
                    MessageBody=json.dumps(message)
                )
            
            return ret(202, {
                "docId": doc_id,
                "status": "QUEUED",
                "message": "Document queued for processing"
            })
            
        except Exception as e:
            return ret(400, {"error": "Processing failed", "detail": str(e)})
    
    return ret(404, {"error": "Not found"})