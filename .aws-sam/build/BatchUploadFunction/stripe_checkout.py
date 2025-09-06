import json
import boto3
import stripe
import os

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_...')

def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        plan = body.get('plan', 'starter')
        user_email = body.get('email')
        
        # Price mapping
        prices = {
            'starter': 'price_1234starter',  # Replace with real Stripe price IDs
            'professional': 'price_1234professional',
            'enterprise': 'price_1234enterprise'
        }
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': prices[plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url='http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html?success=true',
            cancel_url='http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html?canceled=true',
            customer_email=user_email,
            metadata={
                'plan': plan,
                'user_email': user_email
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'checkout_url': session.url,
                'session_id': session.id
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }