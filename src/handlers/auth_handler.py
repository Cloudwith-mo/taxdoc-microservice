import json
import boto3
import hashlib
import uuid
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
users_table = dynamodb.Table('TaxDoc-Users')

def lambda_handler(event, context):
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        if http_method == 'POST' and path == '/auth/register':
            return handle_register(event)
        elif http_method == 'POST' and path == '/auth/login':
            return handle_login(event)
        elif http_method == 'POST' and path == '/auth/logout':
            return handle_logout(event)
        elif http_method == 'GET' and path == '/auth/profile':
            return handle_profile(event)
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }

def handle_register(event):
    try:
        body = json.loads(event['body'])
        email = body.get('email', '').lower().strip()
        password = body.get('password', '')
        name = body.get('name', '').strip()
        
        if not email or not password or not name:
            return error_response('Email, password, and name are required', 400)
        
        if len(password) < 6:
            return error_response('Password must be at least 6 characters', 400)
        
        # Check if user already exists
        try:
            existing_user = users_table.get_item(Key={'email': email})
            if 'Item' in existing_user:
                return error_response('User already exists', 409)
        except Exception:
            pass
        
        # Create new user
        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user_data = {
            'email': email,
            'userId': user_id,
            'name': name,
            'passwordHash': password_hash,
            'createdAt': datetime.utcnow().isoformat(),
            'plan': 'free',
            'documentsProcessed': 0,
            'lastLogin': datetime.utcnow().isoformat()
        }
        
        users_table.put_item(Item=user_data)
        
        # Generate session token
        session_token = generate_session_token(user_id)
        
        return success_response({
            'userId': user_id,
            'email': email,
            'name': name,
            'plan': 'free',
            'sessionToken': session_token
        })
        
    except Exception as e:
        print(f"Register error: {str(e)}")
        return error_response('Registration failed', 500)

def handle_login(event):
    try:
        body = json.loads(event['body'])
        email = body.get('email', '').lower().strip()
        password = body.get('password', '')
        
        if not email or not password:
            return error_response('Email and password are required', 400)
        
        # Get user
        try:
            response = users_table.get_item(Key={'email': email})
            if 'Item' not in response:
                return error_response('Invalid credentials', 401)
            
            user = response['Item']
        except Exception:
            return error_response('Invalid credentials', 401)
        
        # Verify password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user['passwordHash'] != password_hash:
            return error_response('Invalid credentials', 401)
        
        # Update last login
        users_table.update_item(
            Key={'email': email},
            UpdateExpression='SET lastLogin = :timestamp',
            ExpressionAttributeValues={':timestamp': datetime.utcnow().isoformat()}
        )
        
        # Generate session token
        session_token = generate_session_token(user['userId'])
        
        return success_response({
            'userId': user['userId'],
            'email': user['email'],
            'name': user['name'],
            'plan': user.get('plan', 'free'),
            'sessionToken': session_token
        })
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return error_response('Login failed', 500)

def handle_logout(event):
    # For now, just return success - client will clear local storage
    return success_response({'message': 'Logged out successfully'})

def handle_profile(event):
    try:
        # Extract user ID from session token (simplified)
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return error_response('Unauthorized', 401)
        
        session_token = auth_header[7:]  # Remove 'Bearer '
        user_id = verify_session_token(session_token)
        
        if not user_id:
            return error_response('Invalid session', 401)
        
        # Get user by scanning (in production, use GSI)
        response = users_table.scan(
            FilterExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        
        if not response['Items']:
            return error_response('User not found', 404)
        
        user = response['Items'][0]
        
        return success_response({
            'userId': user['userId'],
            'email': user['email'],
            'name': user['name'],
            'plan': user.get('plan', 'free'),
            'documentsProcessed': user.get('documentsProcessed', 0),
            'createdAt': user.get('createdAt')
        })
        
    except Exception as e:
        print(f"Profile error: {str(e)}")
        return error_response('Failed to get profile', 500)

def generate_session_token(user_id):
    # Simple token generation (in production, use JWT)
    timestamp = datetime.utcnow().isoformat()
    token_data = f"{user_id}:{timestamp}"
    return hashlib.sha256(token_data.encode()).hexdigest()

def verify_session_token(token):
    # Simplified verification (in production, use proper JWT verification)
    # For now, just return a placeholder user ID
    return "user_123" if token else None

def success_response(data):
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(data)
    }

def error_response(message, status_code):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps({'error': message})
    }