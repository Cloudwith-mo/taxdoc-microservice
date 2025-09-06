import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """Enhanced batch upload with progress tracking"""
    
    try:
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        files = body.get('files', [])
        user_id = body.get('user_id', 'anonymous')
        
        if not files:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No files provided'})
            }
        
        # Create batch job
        batch_id = f"batch_{int(datetime.now().timestamp())}"
        
        # Store batch info in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        batch_table = dynamodb.Table('BatchJobs-prod')
        
        batch_table.put_item(
            Item={
                'batch_id': batch_id,
                'user_id': user_id,
                'total_files': len(files),
                'processed_files': 0,
                'status': 'processing',
                'created_at': datetime.now().isoformat(),
                'files': files
            }
        )
        
        # Send files to SQS for processing
        sqs = boto3.client('sqs')
        queue_url = 'https://sqs.us-east-1.amazonaws.com/995805900737/DrDoc-Processing-prod'
        
        for i, file_data in enumerate(files):
            message = {
                'batch_id': batch_id,
                'file_index': i,
                'filename': file_data.get('filename'),
                'file_content': file_data.get('file_content'),
                'user_id': user_id,
                'enable_ai': True
            }
            
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'batch_id': {'StringValue': batch_id, 'DataType': 'String'},
                    'user_id': {'StringValue': user_id, 'DataType': 'String'}
                }
            )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'batch_id': batch_id,
                'status': 'processing',
                'total_files': len(files),
                'message': 'Batch processing started'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }