import json
import stripe
import os
from decimal import Decimal

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body']) if event.get('body') else {}
        path = event.get('path', '')
        method = event.get('httpMethod', 'GET')
        
        if '/create-checkout' in path and method == 'POST':
            return create_checkout_session(body)
        elif '/webhook' in path and method == 'POST':
            return handle_webhook(event)
        elif '/subscription-status' in path and method == 'GET':
            return get_subscription_status(event)
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def create_checkout_session(body):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': body.get('plan', 'Pro Plan')},
                    'unit_amount': int(body.get('amount', 2900)),
                    'recurring': {'interval': 'month'}
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=body.get('success_url', 'https://example.com/success'),
            cancel_url=body.get('cancel_url', 'https://example.com/cancel'),
            customer_email=body.get('email')
        )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'checkout_url': session.url})
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def handle_webhook(event):
    payload = event['body']
    sig_header = event['headers'].get('stripe-signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        stripe_event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        
        if stripe_event['type'] == 'checkout.session.completed':
            session = stripe_event['data']['object']
            # Update user subscription status in DynamoDB
            
        return {'statusCode': 200, 'body': json.dumps({'received': True})}
    except Exception as e:
        return {'statusCode': 400, 'body': json.dumps({'error': str(e)})}

def get_subscription_status(event):
    customer_id = event.get('queryStringParameters', {}).get('customer_id')
    
    try:
        subscriptions = stripe.Subscription.list(customer=customer_id, limit=1)
        status = subscriptions.data[0].status if subscriptions.data else 'inactive'
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'status': status})
        }
    except Exception as e:
        return {
            'statusCode': 400,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }