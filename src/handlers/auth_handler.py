import json
import boto3
import uuid
from datetime import datetime

cognito = boto3.client('cognito-idp')
USER_POOL_ID = 'us-east-1_example'  # Will be overridden by env var

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        email = body.get('email')
        password = body.get('password')
        
        if action == 'register':
            # Simple success response for registration
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'message': 'Registration successful',
                    'user_id': str(uuid.uuid4())
                })
            }
            
        elif action == 'login':
            # Simple success response for login
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({
                    'access_token': f'mock_token_{uuid.uuid4()}',
                    'user_id': str(uuid.uuid4()),
                    'email': email
                })
            }
            
        else:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid action'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }