import json

def lambda_handler(event, context):
    method = event.get('httpMethod', 'POST')
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    }
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    body = json.loads(event.get('body', '{}'))
    plan = body.get('price_id', 'unknown')
    
    # Map price IDs to plan names
    plan_mapping = {
        'price_1S59HJBgGYaywldnGTnB64ha': 'micro',
        'price_1S59HtBgGYaywldnpTk4ReM9': 'pro',
        'price_1S59IIBgGYaywldnnvkWZxTb': 'enterprise'
    }
    
    plan_name = plan_mapping.get(plan, 'micro')
    checkout_url = f'http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/redirect.html?plan={plan_name}'
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'checkout_url': checkout_url,
            'session_id': f'stripe_{plan}'
        })
    }