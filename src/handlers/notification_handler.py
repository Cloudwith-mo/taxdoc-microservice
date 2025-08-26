import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    Handle SNS notifications for document processing events
    """
    
    try:
        # Parse the event
        if 'Records' in event:
            # Called from SQS/S3 trigger
            for record in event['Records']:
                if 'Sns' in record:
                    # SNS message
                    message = json.loads(record['Sns']['Message'])
                    handle_notification(message)
                else:
                    # Direct invocation
                    handle_notification(record)
        else:
            # Direct invocation
            handle_notification(event)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Notifications processed'})
        }
        
    except Exception as e:
        print(f"Notification handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_notification(message):
    """Handle individual notification"""
    
    try:
        event_type = message.get('event_type')
        
        if event_type == 'document_ready':
            send_document_ready_notification(message)
        elif event_type == 'document_failed':
            send_document_failed_notification(message)
        elif event_type == 'batch_completed':
            send_batch_completed_notification(message)
        elif event_type == 'export_ready':
            send_export_ready_notification(message)
        else:
            print(f"Unknown event type: {event_type}")
            
    except Exception as e:
        print(f"Error handling notification: {e}")

def send_document_ready_notification(message):
    """Send document ready notification"""
    
    try:
        sns_client = boto3.client('sns')
        
        tenant_id = message.get('tenant_id', 'unknown')
        doc_id = message.get('doc_id')
        filename = message.get('filename', 'Unknown Document')
        document_type = message.get('document_type', 'Document')
        confidence = message.get('confidence', 0)
        summary_url = message.get('summary_url', '')
        
        # Create notification message (no PII)
        notification_message = {
            'event_type': 'document_ready',
            'tenant_id': tenant_id,
            'doc_id': doc_id,
            'document_type': document_type,
            'confidence_score': f"{int(confidence * 100)}%",
            'processed_at': datetime.utcnow().isoformat(),
            'summary_url': summary_url
        }
        
        # Send to doc-ready topic
        topic_arn = os.environ.get('DOC_READY_TOPIC_ARN')
        if topic_arn:
            sns_client.publish(
                TopicArn=topic_arn,
                Subject=f'Document Ready: {document_type}',
                Message=json.dumps(notification_message, indent=2)
            )
            
            print(f"Document ready notification sent for {doc_id}")
        
        # Send user-specific notification if email available
        user_email = message.get('user_email')
        if user_email:
            send_user_email_notification(
                user_email,
                'Document Processing Complete',
                f"""
Your document "{filename}" has been processed successfully!

Document Type: {document_type}
Confidence Score: {int(confidence * 100)}%
Processed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

You can now view and export your document data.

{summary_url if summary_url else ''}

Best regards,
TaxDoc Team
                """.strip()
            )
        
    except Exception as e:
        print(f"Error sending document ready notification: {e}")

def send_document_failed_notification(message):
    """Send document failed notification"""
    
    try:
        sns_client = boto3.client('sns')
        
        tenant_id = message.get('tenant_id', 'unknown')
        doc_id = message.get('doc_id')
        filename = message.get('filename', 'Unknown Document')
        error_message = message.get('error', 'Processing failed')
        
        # Create notification message (no PII)
        notification_message = {
            'event_type': 'document_failed',
            'tenant_id': tenant_id,
            'doc_id': doc_id,
            'error_type': 'processing_failure',
            'failed_at': datetime.utcnow().isoformat()
        }
        
        # Send to doc-failed topic
        topic_arn = os.environ.get('DOC_FAILED_TOPIC_ARN')
        if topic_arn:
            sns_client.publish(
                TopicArn=topic_arn,
                Subject=f'Document Processing Failed',
                Message=json.dumps(notification_message, indent=2)
            )
            
            print(f"Document failed notification sent for {doc_id}")
        
        # Send user-specific notification if email available
        user_email = message.get('user_email')
        if user_email:
            send_user_email_notification(
                user_email,
                'Document Processing Failed',
                f"""
We encountered an issue processing your document "{filename}".

Error: {error_message}
Failed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Please try uploading the document again. If the issue persists, contact our support team.

Best regards,
TaxDoc Team
                """.strip()
            )
        
    except Exception as e:
        print(f"Error sending document failed notification: {e}")

def send_batch_completed_notification(message):
    """Send batch processing completed notification"""
    
    try:
        sns_client = boto3.client('sns')
        
        tenant_id = message.get('tenant_id', 'unknown')
        batch_id = message.get('batch_id')
        total_files = message.get('total_files', 0)
        successful_files = message.get('successful_files', 0)
        failed_files = message.get('failed_files', 0)
        
        # Create notification message
        notification_message = {
            'event_type': 'batch_completed',
            'tenant_id': tenant_id,
            'batch_id': batch_id,
            'total_files': total_files,
            'successful_files': successful_files,
            'failed_files': failed_files,
            'completed_at': datetime.utcnow().isoformat()
        }
        
        # Send to batch topic
        topic_arn = os.environ.get('BATCH_COMPLETED_TOPIC_ARN')
        if topic_arn:
            sns_client.publish(
                TopicArn=topic_arn,
                Subject=f'Batch Processing Complete: {successful_files}/{total_files} successful',
                Message=json.dumps(notification_message, indent=2)
            )
            
            print(f"Batch completed notification sent for {batch_id}")
        
        # Send user-specific notification if email available
        user_email = message.get('user_email')
        if user_email:
            send_user_email_notification(
                user_email,
                'Batch Processing Complete',
                f"""
Your batch upload has been processed!

Total Files: {total_files}
Successfully Processed: {successful_files}
Failed: {failed_files}
Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

You can now view and export your processed documents.

Best regards,
TaxDoc Team
                """.strip()
            )
        
    except Exception as e:
        print(f"Error sending batch completed notification: {e}")

def send_export_ready_notification(message):
    """Send export ready notification"""
    
    try:
        user_email = message.get('user_email')
        export_type = message.get('export_type', 'document')
        export_format = message.get('export_format', 'csv')
        download_url = message.get('download_url', '')
        
        if user_email:
            send_user_email_notification(
                user_email,
                'Export Ready for Download',
                f"""
Your {export_type} export is ready for download!

Format: {export_format.upper()}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

Download Link: {download_url}

Note: This link expires in 15 minutes for security.

Best regards,
TaxDoc Team
                """.strip()
            )
        
    except Exception as e:
        print(f"Error sending export ready notification: {e}")

def send_user_email_notification(email, subject, body):
    """Send email notification to user via SES"""
    
    try:
        ses_client = boto3.client('ses')
        
        # Create HTML version
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">🛡️ TaxDoc</h1>
        </div>
        
        <div style="background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px;">
            <h2 style="color: #2c3e50; margin-top: 0;">{subject}</h2>
            
            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                {body.replace(chr(10), '<br>')}
            </div>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 14px; color: #6c757d;">
                <p>This is an automated message from TaxDoc. Please do not reply to this email.</p>
                <p>If you have questions, contact us at support@taxflowsai.com</p>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        ses_client.send_email(
            Source=os.environ.get('FROM_EMAIL', 'noreply@taxflowsai.com'),
            Destination={'ToAddresses': [email]},
            Message={
                'Subject': {'Data': f'TaxDoc: {subject}'},
                'Body': {
                    'Text': {'Data': body},
                    'Html': {'Data': html_body}
                }
            }
        )
        
        print(f"Email notification sent to {email}")
        
    except Exception as e:
        print(f"Error sending email notification: {e}")

# Utility functions for triggering notifications
def trigger_document_ready(tenant_id, doc_id, filename, document_type, confidence, user_email=None, summary_url=None):
    """Trigger document ready notification"""
    
    message = {
        'event_type': 'document_ready',
        'tenant_id': tenant_id,
        'doc_id': doc_id,
        'filename': filename,
        'document_type': document_type,
        'confidence': confidence,
        'user_email': user_email,
        'summary_url': summary_url
    }
    
    handle_notification(message)

def trigger_document_failed(tenant_id, doc_id, filename, error, user_email=None):
    """Trigger document failed notification"""
    
    message = {
        'event_type': 'document_failed',
        'tenant_id': tenant_id,
        'doc_id': doc_id,
        'filename': filename,
        'error': error,
        'user_email': user_email
    }
    
    handle_notification(message)

def trigger_batch_completed(tenant_id, batch_id, total_files, successful_files, failed_files, user_email=None):
    """Trigger batch completed notification"""
    
    message = {
        'event_type': 'batch_completed',
        'tenant_id': tenant_id,
        'batch_id': batch_id,
        'total_files': total_files,
        'successful_files': successful_files,
        'failed_files': failed_files,
        'user_email': user_email
    }
    
    handle_notification(message)

def trigger_export_ready(user_email, export_type, export_format, download_url):
    """Trigger export ready notification"""
    
    message = {
        'event_type': 'export_ready',
        'user_email': user_email,
        'export_type': export_type,
        'export_format': export_format,
        'download_url': download_url
    }
    
    handle_notification(message)