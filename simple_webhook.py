import json

def lambda_handler(event, context):
    """Simple webhook handler for testing"""
    
    print(f"Received event: {json.dumps(event)}")
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Webhook received successfully',
            'path': event.get('path', ''),
            'method': event.get('httpMethod', ''),
            'headers': event.get('headers', {})
        })
    }