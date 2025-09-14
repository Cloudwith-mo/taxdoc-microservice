import json
import boto3
import base64
import uuid
from typing import Dict, Any
import os

ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

def with_cors(resp):
    h = resp.get("headers", {})
    h.update({
        "Access-Control-Allow-Origin": ORIGIN,
        "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,Idempotency-Key,x-amz-meta-userid,x-amz-meta-docid"
    })
    resp["headers"] = h
    return resp

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway handler that processes documents via S3 key"""
    
    print(f"API Gateway event: {json.dumps(event)}")
    
    try:
        # Parse API Gateway body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        # HARD GUARD: reject legacy base64 calls clearly (no 502)
        if "contentBase64" in body:
            return with_cors({
                "statusCode": 413,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Use /upload-url + S3 PUT, then POST /process with {s3Key}."})
            })
        
        s3_key = body.get('s3Key', '')
        filename = body.get('filename', 'document.png')
        
        if not s3_key:
            return with_cors({
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No s3Key provided'})
            })
        
        # Process document from S3 key
        bucket_name = 'taxflowsai-uploads'
        
        # Validate s3Key format
        if not s3_key.startswith('uploads/'):
            s3_key = f'uploads/{s3_key}'
        
        # Invoke the real processor directly
        lambda_client = boto3.client('lambda')
        
        # Create S3 event structure
        s3_event = {
            "Records": [{
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "eventTime": "2025-01-01T00:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": s3_key}
                }
            }]
        }
        
        # Invoke processor
        response = lambda_client.invoke(
            FunctionName='TaxDoc-ProcessDocument-dev',
            InvocationType='RequestResponse',
            Payload=json.dumps(s3_event)
        )
        
        # Parse response
        payload = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            # Parse the response body
            result_body = json.loads(payload.get('body', '{}'))
            
            return with_cors({
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(result_body)
            })
        else:
            return with_cors({
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Processing failed'})
            })
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return with_cors({
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        })