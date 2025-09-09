import json
import boto3

ddb = boto3.resource('dynamodb')
table = ddb.Table('DrDocDocuments-prod')

def get_user_id(event):
    """Extract user ID from event context or headers"""
    # Try to get from API Gateway context
    if event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub"):
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    
    # Try to get from headers
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return "user_" + str(hash(auth_header))[-8:]
    
    return "anonymous_user"

def lambda_handler(event, context):
    try:
        user_id = get_user_id(event)
        
        # Query documents for this user
        response = table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'user#{user_id}'}
        )
        items = response.get('Items', [])
        
        documents = []
        for item in items:
            doc = {
                'docId': item.get('sk', '').replace('doc#', ''),
                'filename': item.get('filename') or item.get('s3', {}).get('key', '').split('/')[-1],
                'docType': item.get('docType', 'Unknown'),
                'docTypeConfidence': float(item.get('docTypeConfidence', 0)),
                'fields': item.get('fields', {}),
                'keyValues': item.get('keyValues', []),
                'summary': item.get('summary', ''),
                's3': item.get('s3', {}),
                'timestamp': item.get('ts', ''),
                'status': 'completed'
            }
            documents.append(doc)
        
        # Sort by timestamp descending
        documents.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({'documents': documents})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }