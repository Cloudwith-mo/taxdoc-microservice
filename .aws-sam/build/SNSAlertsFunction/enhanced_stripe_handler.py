import json
import boto3
import os
import stripe
import hashlib
import hmac
from datetime import datetime

def lambda_handler(event, context):
    """
    Handle Stripe webhook events with signature verification
    """
    
    try:
        # Get environment variables
        stripe_secret = os.environ.get('STRIPE_SECRET_KEY')
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        users_table_name = os.environ.get('USERS_TABLE', 'DrDocUsers-prod')
        
        if not stripe_secret or not webhook_secret:
            print("Missing Stripe configuration")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Missing Stripe configuration'})
            }
        
        # Set Stripe API key
        stripe.api_key = stripe_secret
        
        # Get the raw body and signature
        payload = event['body']
        sig_header = event['headers'].get('stripe-signature') or event['headers'].get('Stripe-Signature')
        
        if not sig_header:
            print("Missing Stripe signature")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing signature'})
            }
        
        # Verify webhook signature
        try:
            webhook_event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            print(f"Signature verified for event: {webhook_event['id']}")
        except ValueError as e:
            print(f"Invalid payload: {e}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid payload'})
            }
        except stripe.error.SignatureVerificationError as e:
            print(f"Invalid signature: {e}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid signature'})
            }
        
        # Initialize DynamoDB
        dynamodb = boto3.resource('dynamodb')
        users_table = dynamodb.Table(users_table_name)
        
        # Check for idempotency
        event_id = webhook_event['id']
        try:
            # Try to get existing event record
            existing = users_table.get_item(
                Key={'email': f'webhook_event_{event_id}'}
            )
            if 'Item' in existing:
                print(f"Event {event_id} already processed")
                return {
                    'statusCode': 200,
                    'body': json.dumps({'received': True, 'already_processed': True})
                }
        except Exception as e:
            print(f"Error checking idempotency: {e}")
        
        # Process the event
        event_type = webhook_event['type']
        print(f"Processing Stripe webhook: {event_type}")
        
        if event_type == 'checkout.session.completed':
            session = webhook_event['data']['object']
            customer_email = session.get('customer_email')
            
            # Extract plan from metadata
            plan = 'starter'  # Default
            if 'metadata' in session and 'plan' in session['metadata']:
                plan = session['metadata']['plan']
            
            # Update user tier in DynamoDB
            if customer_email:
                users_table.update_item(
                    Key={'email': customer_email},
                    UpdateExpression='SET plan = :plan, docQuotaMonthly = :quota, updated_at = :timestamp, features = :features',
                    ExpressionAttributeValues={
                        ':plan': plan,
                        ':quota': get_plan_quota(plan),
                        ':timestamp': datetime.utcnow().isoformat(),
                        ':features': get_plan_features(plan)
                    },
                    ReturnValues='UPDATED_NEW'
                )
                
                # Record event for idempotency
                users_table.put_item(
                    Item={
                        'email': f'webhook_event_{event_id}',
                        'event_type': event_type,
                        'processed_at': datetime.utcnow().isoformat(),
                        'customer_email': customer_email,
                        'plan': plan
                    }
                )
                
                print(f"Updated user {customer_email} to {plan} plan")
        
        elif event_type == 'customer.subscription.deleted':
            subscription = webhook_event['data']['object']
            customer_id = subscription.get('customer')
            
            # Get customer email from Stripe
            try:
                customer = stripe.Customer.retrieve(customer_id)
                customer_email = customer.email
                
                if customer_email:
                    # Downgrade user to free tier
                    users_table.update_item(
                        Key={'email': customer_email},
                        UpdateExpression='SET plan = :plan, docQuotaMonthly = :quota, updated_at = :timestamp, features = :features',
                        ExpressionAttributeValues={
                            ':plan': 'free',
                            ':quota': 20,
                            ':timestamp': datetime.utcnow().isoformat(),
                            ':features': get_plan_features('free')
                        },
                        ReturnValues='UPDATED_NEW'
                    )
                    
                    # Record event for idempotency
                    users_table.put_item(
                        Item={
                            'email': f'webhook_event_{event_id}',
                            'event_type': event_type,
                            'processed_at': datetime.utcnow().isoformat(),
                            'customer_email': customer_email,
                            'plan': 'free'
                        }
                    )
                    
                    print(f"Downgraded user {customer_email} to free plan")
            except Exception as e:
                print(f"Error retrieving customer: {e}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'received': True, 'event_id': event_id})
        }
        
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }

def get_plan_quota(plan):
    """Get document quota for plan"""
    quotas = {
        'free': 20,
        'starter': 100,
        'professional': 500,
        'enterprise': -1  # Unlimited
    }
    return quotas.get(plan, 20)

def get_plan_features(plan):
    """Get features for plan"""
    features = {
        'free': {
            'exports': ['csv'],
            'aiInsights': False,
            'api': False,
            'prioritySupport': False
        },
        'starter': {
            'exports': ['csv', 'json', 'xlsx'],
            'aiInsights': True,
            'api': True,
            'prioritySupport': True
        },
        'professional': {
            'exports': ['csv', 'json', 'xlsx', 'pdf'],
            'aiInsights': True,
            'api': True,
            'prioritySupport': True,
            'batchProcessing': True,
            'customIntegrations': True
        },
        'enterprise': {
            'exports': ['csv', 'json', 'xlsx', 'pdf'],
            'aiInsights': True,
            'api': True,
            'prioritySupport': True,
            'batchProcessing': True,
            'customIntegrations': True,
            'customModels': True,
            'dedicatedSupport': True
        }
    }
    return features.get(plan, features['free'])