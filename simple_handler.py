import json
import boto3
import base64
from datetime import datetime

def lambda_handler(event, context):
    """Simple API handler for document processing"""
    
    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Handle GET request for results
        if event.get('httpMethod') == 'GET':
            path_params = event.get('pathParameters', {})
            doc_id = path_params.get('doc_id')
            
            if not doc_id:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Missing document ID'})
                }
            
            # Get from DynamoDB
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('DrDocDocuments-prod')
            
            response = table.get_item(Key={'DocumentID': doc_id})
            
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({'error': 'Document not found'})
                }
            
            item = response['Item']
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'document_id': doc_id,
                    'status': item.get('Status', 'unknown'),
                    'filename': item.get('FileName', ''),
                    'created_at': item.get('CreatedAt', ''),
                    'data': item.get('Data', {})
                })
            }
        
        # Parse request body
        if 'body' not in event or not event['body']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing request body'})
            }
        
        body = json.loads(event['body'])
        filename = body.get('filename', 'document.pdf')
        file_content = body.get('file_content', '')
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing file_content'})
            }
        
        # Generate document ID
        doc_id = f"doc_{int(datetime.now().timestamp())}"
        
        # Store in S3
        s3 = boto3.client('s3')
        bucket = 'drdoc-uploads-prod-995805900737'
        
        # Decode base64 content
        file_data = base64.b64decode(file_content)
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket,
            Key=f"{doc_id}/{filename}",
            Body=file_data,
            ContentType='application/pdf'
        )
        
        # Send message to SQS to trigger processing
        sqs = boto3.client('sqs')
        queue_url = 'https://sqs.us-east-1.amazonaws.com/995805900737/DrDoc-Processing-prod'
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'DocumentID': doc_id,
                'S3Bucket': bucket,
                'S3Key': f"{doc_id}/{filename}",
                'FileName': filename
            })
        )
        
        # Store metadata in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('DrDocDocuments-prod')
        
        table.put_item(
            Item={
                'DocumentID': doc_id,
                'FileName': filename,
                'Status': 'processing',
                'CreatedAt': datetime.now().isoformat(),
                'S3Key': f"{doc_id}/{filename}"
            }
        )
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'document_id': doc_id,
                'status': 'processing',
                'message': 'Document uploaded successfully'
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }