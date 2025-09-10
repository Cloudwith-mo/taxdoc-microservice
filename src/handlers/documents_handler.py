import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ParsePilot-Facts')  # Use facts table instead

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': 'https://d11rn2gcciu6ti.cloudfront.net',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        method = event.get('httpMethod', 'GET')
        
        if method == 'GET':
            return get_documents(event, headers)
        elif method == 'POST':
            return save_document(event, headers)
        else:
            return {'statusCode': 405, 'headers': headers, 'body': json.dumps({'error': 'Method not allowed'})}
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def get_documents(event, headers):
    user_id = event.get('queryStringParameters', {}).get('userId', 'guest')
    
    try:
        # Query facts table for unique documents
        response = table.query(
            KeyConditionExpression='PK = :pk',
            ExpressionAttributeValues={':pk': user_id}
        )
        
        # Group facts by document
        docs = {}
        for item in response.get('Items', []):
            doc_id = item.get('doc_id')
            if doc_id and doc_id not in docs:
                docs[doc_id] = {
                    'docId': doc_id,
                    'docType': item.get('doc_type', 'Unknown'),
                    'filename': f"{doc_id}.pdf",
                    'status': 'completed',
                    'fields': {},
                    'uploadDate': item.get('created_at', 0)
                }
            
            if doc_id and item.get('field_key'):
                field_key = item.get('field_key')
                value = item.get('value_str') or item.get('value_num')
                if value:
                    docs[doc_id]['fields'][field_key] = value
        
        items = list(docs.values())
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'items': items})
        }
        
    except Exception as e:
        print(f"Get documents error: {e}")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'items': []})
        }

def save_document(event, headers):
    try:
        body = json.loads(event.get('body', '{}'))
        
        doc_id = body.get('docId') or f"doc_{int(datetime.now().timestamp())}"
        user_id = body.get('userId', 'guest')
        doc_type = body.get('docType', 'Unknown')
        fields = body.get('fields', {})
        timestamp = int(datetime.now().timestamp() * 1000)
        
        # Save document metadata as a fact
        from decimal import Decimal
        metadata_item = {
            'PK': user_id,
            'SK': f"{doc_id}#metadata#{timestamp}",
            'doc_id': doc_id,
            'doc_type': doc_type,
            'field_key': 'metadata',
            'value_str': body.get('filename', ''),
            'confidence': Decimal(str(body.get('docTypeConfidence', 0.9))),
            'created_at': timestamp
        }
        
        table.put_item(Item=metadata_item)
        
        # Save each field as a separate fact
        for field_key, field_value in fields.items():
            if field_value:
                fact_item = {
                    'PK': user_id,
                    'SK': f"{doc_id}#{field_key}#{timestamp}",
                    'doc_id': doc_id,
                    'doc_type': doc_type,
                    'field_key': field_key,
                    'created_at': timestamp
                }
                
                # Store value by type (use Decimal for DynamoDB)
                if isinstance(field_value, (int, float)):
                    from decimal import Decimal
                    fact_item['value_num'] = Decimal(str(field_value))
                else:
                    fact_item['value_str'] = str(field_value)
                
                fact_item['confidence'] = Decimal('0.9')
                table.put_item(Item=fact_item)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'success': True, 'docId': doc_id})
        }
        
    except Exception as e:
        print(f"Save document error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }