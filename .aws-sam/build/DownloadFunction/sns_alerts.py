import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """SNS alerts for document processing events"""
    
    try:
        # Parse the event (could be from SQS, DynamoDB stream, etc.)
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:dynamodb':
                    handle_dynamodb_event(record)
                elif record.get('eventSource') == 'aws:sqs':
                    handle_sqs_event(record)
        else:
            # Direct invocation
            handle_direct_event(event)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Alerts processed successfully'})
        }
        
    except Exception as e:
        print(f"Alert processing error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_dynamodb_event(record):
    """Handle DynamoDB stream events"""
    event_name = record.get('eventName')
    
    if event_name == 'INSERT':
        # New document processed
        new_image = record['dynamodb'].get('NewImage', {})
        doc_id = new_image.get('document_id', {}).get('S', '')
        user_id = new_image.get('user_id', {}).get('S', '')
        doc_type = new_image.get('document_type', {}).get('S', '')
        
        send_processing_complete_alert(doc_id, user_id, doc_type)
        
    elif event_name == 'MODIFY':
        # Document updated (e.g., edited)
        new_image = record['dynamodb'].get('NewImage', {})
        doc_id = new_image.get('document_id', {}).get('S', '')
        
        send_document_updated_alert(doc_id)

def handle_sqs_event(record):
    """Handle SQS events"""
    try:
        body = json.loads(record['body'])
        alert_type = body.get('alert_type')
        
        if alert_type == 'processing_failed':
            send_processing_failed_alert(body)
        elif alert_type == 'batch_complete':
            send_batch_complete_alert(body)
            
    except Exception as e:
        print(f"SQS event handling error: {e}")

def handle_direct_event(event):
    """Handle direct Lambda invocation"""
    alert_type = event.get('alert_type')
    
    if alert_type == 'user_registered':
        send_welcome_alert(event.get('user_id'), event.get('email'))
    elif alert_type == 'payment_received':
        send_payment_confirmation(event.get('user_id'), event.get('amount'))

def send_processing_complete_alert(doc_id, user_id, doc_type):
    """Send alert when document processing is complete"""
    sns = boto3.client('sns')
    topic_arn = 'arn:aws:sns:us-east-1:995805900737:TaxDoc-Alerts'
    
    message = {
        'alert_type': 'processing_complete',
        'document_id': doc_id,
        'user_id': user_id,
        'document_type': doc_type,
        'timestamp': datetime.now().isoformat(),
        'message': f'Document {doc_id} ({doc_type}) has been processed successfully'
    }
    
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject=f'TaxDoc: Document {doc_type} Processed',
            Message=json.dumps(message, indent=2)
        )
    except Exception as e:
        print(f"SNS publish error: {e}")

def send_processing_failed_alert(event_data):
    """Send alert when document processing fails"""
    sns = boto3.client('sns')
    topic_arn = 'arn:aws:sns:us-east-1:995805900737:TaxDoc-Alerts'
    
    message = {
        'alert_type': 'processing_failed',
        'document_id': event_data.get('document_id'),
        'user_id': event_data.get('user_id'),
        'error': event_data.get('error'),
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject='TaxDoc: Processing Failed',
            Message=json.dumps(message, indent=2)
        )
    except Exception as e:
        print(f"SNS publish error: {e}")

def send_batch_complete_alert(event_data):
    """Send alert when batch processing is complete"""
    sns = boto3.client('sns')
    topic_arn = 'arn:aws:sns:us-east-1:995805900737:TaxDoc-Alerts'
    
    message = {
        'alert_type': 'batch_complete',
        'batch_id': event_data.get('batch_id'),
        'user_id': event_data.get('user_id'),
        'total_files': event_data.get('total_files'),
        'successful': event_data.get('successful', 0),
        'failed': event_data.get('failed', 0),
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject='TaxDoc: Batch Processing Complete',
            Message=json.dumps(message, indent=2)
        )
    except Exception as e:
        print(f"SNS publish error: {e}")

def send_welcome_alert(user_id, email):
    """Send welcome alert for new user registration"""
    sns = boto3.client('sns')
    topic_arn = 'arn:aws:sns:us-east-1:995805900737:TaxDoc-Alerts'
    
    message = {
        'alert_type': 'user_registered',
        'user_id': user_id,
        'email': email,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject='TaxDoc: New User Registration',
            Message=json.dumps(message, indent=2)
        )
    except Exception as e:
        print(f"SNS publish error: {e}")

def send_payment_confirmation(user_id, amount):
    """Send payment confirmation alert"""
    sns = boto3.client('sns')
    topic_arn = 'arn:aws:sns:us-east-1:995805900737:TaxDoc-Alerts'
    
    message = {
        'alert_type': 'payment_received',
        'user_id': user_id,
        'amount': amount,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject='TaxDoc: Payment Received',
            Message=json.dumps(message, indent=2)
        )
    except Exception as e:
        print(f"SNS publish error: {e}")