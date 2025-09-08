import json

def lambda_handler(event, context):
    """Working auth handler with proper CORS"""
    
    # CORS headers for all responses
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': ''
        }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        action = body.get('action', 'login')
        email = body.get('email', '')
        
        if action == 'register':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'User registered successfully',
                    'email': email
                })
            }
        elif action == 'login':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'access_token': 'demo-token-' + email.split('@')[0],
                    'message': 'Login successful',
                    'email': email
                })
            }
        else:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid action'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }