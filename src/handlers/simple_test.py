import json

def lambda_handler(event, context):
    """Simple test handler for API Gateway"""
    
    print(f"Received event: {json.dumps(event)}")
    
    # Extract body from API Gateway event
    body = event.get('body', '{}')
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except:
            body = {}
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'message': 'Test endpoint working',
            'received_filename': body.get('filename', 'unknown'),
            'content_size': len(body.get('contentBase64', '')),
            'status': 'success'
        })
    }