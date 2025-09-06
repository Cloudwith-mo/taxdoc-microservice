import json
import boto3
import os
from datetime import datetime, timezone
from functools import wraps

def check_entitlements(required_feature=None, quota_check=True):
    """
    Decorator to check user entitlements and quotas
    """
    def decorator(handler_func):
        @wraps(handler_func)
        def wrapper(event, context):
            try:
                # Extract user info from JWT token
                user_email = extract_user_from_token(event)
                if not user_email:
                    return {
                        'statusCode': 401,
                        'headers': get_cors_headers(),
                        'body': json.dumps({'error': 'Authentication required'})
                    }
                
                # Get user from DynamoDB
                user_data = get_user_data(user_email)
                if not user_data:
                    return {
                        'statusCode': 403,
                        'headers': get_cors_headers(),
                        'body': json.dumps({'error': 'User not found'})
                    }
                
                # Check quota if required
                if quota_check:
                    quota_result = check_quota(user_data)
                    if not quota_result['allowed']:
                        return {
                            'statusCode': 402,
                            'headers': get_cors_headers(),
                            'body': json.dumps({
                                'error': 'Monthly quota exceeded',
                                'message': quota_result['message'],
                                'upgrade_url': '/subscriptions'
                            })
                        }
                
                # Check feature access if required
                if required_feature:
                    feature_result = check_feature_access(user_data, required_feature)
                    if not feature_result['allowed']:
                        return {
                            'statusCode': 402,
                            'headers': get_cors_headers(),
                            'body': json.dumps({
                                'error': 'Feature not available',
                                'message': feature_result['message'],
                                'upgrade_url': '/subscriptions'
                            })
                        }
                
                # Add user data to event for handler use
                event['user_data'] = user_data
                
                # Call the original handler
                return handler_func(event, context)
                
            except Exception as e:
                print(f"Entitlement check error: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'error': 'Internal server error'})
                }
        
        return wrapper
    return decorator

def extract_user_from_token(event):
    """Extract user email from JWT token"""
    try:
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        # In production, decode and verify JWT properly
        # For now, extract from mock token
        token = auth_header.split('Bearer ')[1]
        
        # Mock extraction - replace with proper JWT decoding
        if token.startswith('mock_'):
            return token.replace('mock_', '') + '@example.com'
        
        # For real tokens, use JWT library to decode
        import jwt
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get('email')
        except:
            return None
            
    except Exception as e:
        print(f"Token extraction error: {e}")
        return None

def get_user_data(email):
    """Get user data from DynamoDB"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('USERS_TABLE', 'DrDocUsers-prod'))
        
        response = table.get_item(Key={'email': email})
        
        if 'Item' not in response:
            # Create new user with free plan
            user_data = {
                'email': email,
                'plan': 'free',
                'docQuotaMonthly': 20,
                'usedThisMonth': 0,
                'features': get_plan_features('free'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            table.put_item(Item=user_data)
            return user_data
        
        return response['Item']
        
    except Exception as e:
        print(f"Error getting user data: {e}")
        return None

def check_quota(user_data):
    """Check if user has quota remaining"""
    try:
        plan = user_data.get('plan', 'free')
        quota = user_data.get('docQuotaMonthly', 20)
        used = user_data.get('usedThisMonth', 0)
        
        # Unlimited plans
        if quota == -1:
            return {'allowed': True, 'message': 'Unlimited'}
        
        # Check if quota exceeded
        if used >= quota:
            return {
                'allowed': False,
                'message': f'Monthly limit reached ({used}/{quota}). Upgrade your plan to continue.'
            }
        
        return {
            'allowed': True,
            'message': f'{quota - used} documents remaining this month'
        }
        
    except Exception as e:
        print(f"Quota check error: {e}")
        return {'allowed': False, 'message': 'Error checking quota'}

def check_feature_access(user_data, feature):
    """Check if user has access to specific feature"""
    try:
        features = user_data.get('features', {})
        
        if feature == 'exports':
            # Check export formats
            allowed_formats = features.get('exports', ['csv'])
            return {
                'allowed': True,
                'message': f'Available formats: {", ".join(allowed_formats)}',
                'formats': allowed_formats
            }
        
        elif feature == 'aiInsights':
            allowed = features.get('aiInsights', False)
            return {
                'allowed': allowed,
                'message': 'AI insights available' if allowed else 'AI insights require paid plan'
            }
        
        elif feature == 'api':
            allowed = features.get('api', False)
            return {
                'allowed': allowed,
                'message': 'API access available' if allowed else 'API access requires paid plan'
            }
        
        elif feature == 'batchProcessing':
            allowed = features.get('batchProcessing', False)
            return {
                'allowed': allowed,
                'message': 'Batch processing available' if allowed else 'Batch processing requires Professional plan'
            }
        
        else:
            return {'allowed': True, 'message': 'Feature check passed'}
            
    except Exception as e:
        print(f"Feature check error: {e}")
        return {'allowed': False, 'message': 'Error checking feature access'}

def increment_usage(user_email):
    """Increment user's monthly usage count"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('USERS_TABLE', 'DrDocUsers-prod'))
        
        table.update_item(
            Key={'email': user_email},
            UpdateExpression='ADD usedThisMonth :inc SET updated_at = :timestamp',
            ExpressionAttributeValues={
                ':inc': 1,
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
        
        print(f"Incremented usage for {user_email}")
        
    except Exception as e:
        print(f"Error incrementing usage: {e}")

def reset_monthly_quotas():
    """Reset all users' monthly quotas (called by cron)"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('USERS_TABLE', 'DrDocUsers-prod'))
        
        # Scan all users
        response = table.scan()
        users = response['Items']
        
        # Reset counters
        for user in users:
            if user['email'].startswith('webhook_event_'):
                continue  # Skip webhook event records
                
            # Store previous month's usage in history
            previous_usage = user.get('usedThisMonth', 0)
            current_month = datetime.now(timezone.utc).strftime('%Y-%m')
            
            table.update_item(
                Key={'email': user['email']},
                UpdateExpression='SET usedThisMonth = :zero, updated_at = :timestamp, usageHistory.#month = :usage',
                ExpressionAttributeNames={
                    '#month': current_month
                },
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':timestamp': datetime.utcnow().isoformat(),
                    ':usage': previous_usage
                }
            )
        
        print(f"Reset quotas for {len(users)} users")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'reset_count': len(users)})
        }
        
    except Exception as e:
        print(f"Error resetting quotas: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

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

def get_cors_headers():
    """Get CORS headers"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

# Lambda handler for monthly quota reset (triggered by EventBridge)
def quota_reset_handler(event, context):
    """Handler for monthly quota reset"""
    return reset_monthly_quotas()