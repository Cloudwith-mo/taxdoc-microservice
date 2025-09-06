import json
import boto3
import stripe
import os
from datetime import datetime

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def lambda_handler(event, context):
    """Handle Stripe payment operations"""
    
    try:
        # Parse the request
        if event.get('httpMethod') == 'POST':
            body = json.loads(event.get('body', '{}'))
            path = event.get('path', '')
            
            if '/create-checkout-session' in path:
                return create_checkout_session(body, event)
            elif '/webhook' in path:
                return handle_webhook(event)
        
        return {
            'statusCode': 404,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Not found'})
        }
        
    except Exception as e:
        print(f"Error in stripe_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': str(e)})
        }

def create_checkout_session(body, event):
    """Create a Stripe checkout session"""
    
    try:
        # Get user info from JWT token (simplified for MVP)
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            raise Exception('Authentication required')
        
        # Extract user ID from token (you'd decode JWT properly in production)
        user_id = 'user_' + auth_header.split('Bearer ')[1][:10]
        
        price_id = body.get('price_id')
        success_url = body.get('success_url')
        cancel_url = body.get('cancel_url')
        
        if not all([price_id, success_url, cancel_url]):
            raise Exception('Missing required parameters')
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user_id,
            metadata={
                'user_id': user_id
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'checkout_url': session.url,
                'session_id': session.id
            })
        }
        
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        raise e

def handle_webhook(event):
    """Handle Stripe webhooks"""
    
    try:
        payload = event.get('body', '')
        sig_header = event.get('headers', {}).get('stripe-signature', '')
        endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        # Verify webhook signature
        stripe_event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        
        # Handle the event
        if stripe_event['type'] == 'checkout.session.completed':
            session = stripe_event['data']['object']
            user_id = session.get('client_reference_id')
            
            if user_id:
                # Update user tier in DynamoDB
                update_user_tier(user_id, 'premium')
                
        elif stripe_event['type'] == 'customer.subscription.deleted':
            subscription = stripe_event['data']['object']
            customer_id = subscription.get('customer')
            
            # Get user ID from customer and downgrade
            # (Implementation depends on your user-customer mapping)
            
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'received': True})
        }
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def update_user_tier(user_id, tier):
    """Update user tier in DynamoDB"""
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('USERS_TABLE', 'DrDocUsers-prod'))
        
        table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET user_tier = :tier, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':tier': tier,
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
        
        print(f"Updated user {user_id} to tier {tier}")
        
    except Exception as e:
        print(f"Error updating user tier: {str(e)}")
        raise e