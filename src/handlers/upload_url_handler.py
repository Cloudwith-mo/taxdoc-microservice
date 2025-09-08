import json
import boto3
import uuid
from datetime import datetime, timedelta

s3 = boto3.client('s3')
BUCKET = 'taxflowsai-uploads'

def lambda_handler(event, context):
    try:
        params = event.get('queryStringParameters') or {}
        filename = params.get('filename', 'document.png')
        content_type = params.get('contentType', 'image/png')
        
        # Generate unique S3 key
        key = f"uploads/{uuid.uuid4()}_{filename}"
        
        # Generate presigned URL
        url = s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': BUCKET, 'Key': key, 'ContentType': content_type},
            ExpiresIn=3600
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'uploadUrl': url,
                's3Key': key,
                'bucket': BUCKET
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }