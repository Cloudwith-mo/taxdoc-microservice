import json
import boto3
import os
import uuid
import base64
import zipfile
import io
from datetime import datetime
from entitlement_middleware import check_entitlements, increment_usage

@check_entitlements(required_feature='batchProcessing', quota_check=True)
def lambda_handler(event, context):
    """
    Handle batch file uploads including ZIP processing
    """
    
    try:
        user_data = event.get('user_data', {})
        user_email = user_data.get('email')
        
        # Parse request
        body = json.loads(event.get('body', '{}'))
        upload_type = body.get('type', 'files')  # 'files' or 'zip'
        
        if upload_type == 'zip':
            return handle_zip_upload(body, user_email)
        else:
            return handle_batch_files(body, user_email)
            
    except Exception as e:
        print(f"Batch upload error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def handle_zip_upload(body, user_email):
    """Handle ZIP file upload and extraction"""
    
    try:
        zip_content = body.get('zip_content')  # Base64 encoded ZIP
        if not zip_content:
            raise Exception('ZIP content required')
        
        # Decode ZIP content
        zip_data = base64.b64decode(zip_content)
        
        # Extract files from ZIP
        extracted_files = []
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                if file_info.is_dir():
                    continue
                
                # Check file extension
                filename = file_info.filename
                if not is_supported_file(filename):
                    print(f"Skipping unsupported file: {filename}")
                    continue
                
                # Extract file content
                file_content = zip_ref.read(file_info)
                file_base64 = base64.b64encode(file_content).decode('utf-8')
                
                extracted_files.append({
                    'filename': filename,
                    'content': file_base64,
                    'size': len(file_content)
                })
        
        if not extracted_files:
            raise Exception('No supported files found in ZIP')
        
        # Process extracted files
        return process_batch_files(extracted_files, user_email, 'zip')
        
    except Exception as e:
        print(f"ZIP processing error: {str(e)}")
        raise e

def handle_batch_files(body, user_email):
    """Handle multiple individual files"""
    
    try:
        files = body.get('files', [])
        if not files:
            raise Exception('No files provided')
        
        # Validate files
        validated_files = []
        for file_data in files:
            filename = file_data.get('filename')
            content = file_data.get('content')
            
            if not filename or not content:
                continue
            
            if not is_supported_file(filename):
                continue
            
            validated_files.append({
                'filename': filename,
                'content': content,
                'size': len(base64.b64decode(content))
            })
        
        if not validated_files:
            raise Exception('No valid files provided')
        
        return process_batch_files(validated_files, user_email, 'batch')
        
    except Exception as e:
        print(f"Batch files error: {str(e)}")
        raise e

def process_batch_files(files, user_email, source_type):
    """Process batch of files"""
    
    try:
        s3_client = boto3.client('s3')
        sqs_client = boto3.client('sqs')
        
        bucket_name = os.environ.get('UPLOAD_BUCKET', 'drdoc-uploads-prod-995805900737')
        queue_url = os.environ.get('PROCESSING_QUEUE_URL')
        
        batch_id = str(uuid.uuid4())
        processed_files = []
        
        for file_data in files:
            try:
                # Generate unique document ID
                document_id = str(uuid.uuid4())
                
                # Upload to S3
                s3_key = f"batch/{batch_id}/{document_id}/{file_data['filename']}"
                
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=base64.b64decode(file_data['content']),
                    ContentType=get_content_type(file_data['filename']),
                    Metadata={
                        'user_email': user_email,
                        'batch_id': batch_id,
                        'source_type': source_type,
                        'original_filename': file_data['filename']
                    }
                )
                
                # Send to processing queue
                if queue_url:
                    sqs_client.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps({
                            'document_id': document_id,
                            's3_bucket': bucket_name,
                            's3_key': s3_key,
                            'filename': file_data['filename'],
                            'user_email': user_email,
                            'batch_id': batch_id,
                            'source_type': source_type
                        })
                    )
                
                processed_files.append({
                    'document_id': document_id,
                    'filename': file_data['filename'],
                    'status': 'queued',
                    's3_key': s3_key
                })
                
                # Increment usage for each file
                increment_usage(user_email)
                
            except Exception as e:
                print(f"Error processing file {file_data['filename']}: {e}")
                processed_files.append({
                    'filename': file_data['filename'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Store batch info in DynamoDB
        store_batch_info(batch_id, user_email, processed_files, source_type)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'batch_id': batch_id,
                'files': processed_files,
                'total_files': len(files),
                'queued_files': len([f for f in processed_files if f.get('status') == 'queued']),
                'failed_files': len([f for f in processed_files if f.get('status') == 'failed'])
            })
        }
        
    except Exception as e:
        print(f"Batch processing error: {str(e)}")
        raise e

def store_batch_info(batch_id, user_email, files, source_type):
    """Store batch processing info in DynamoDB"""
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('BATCH_TABLE', 'DrDocBatches-prod'))
        
        table.put_item(
            Item={
                'batch_id': batch_id,
                'user_email': user_email,
                'source_type': source_type,
                'files': files,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'processing',
                'total_files': len(files),
                'completed_files': 0
            }
        )
        
    except Exception as e:
        print(f"Error storing batch info: {e}")

def is_supported_file(filename):
    """Check if file type is supported"""
    supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.heic', '.tiff', '.tif']
    return any(filename.lower().endswith(ext) for ext in supported_extensions)

def get_content_type(filename):
    """Get content type for file"""
    extension = filename.lower().split('.')[-1]
    content_types = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'heic': 'image/heic',
        'tiff': 'image/tiff',
        'tif': 'image/tiff'
    }
    return content_types.get(extension, 'application/octet-stream')

def get_cors_headers():
    """Get CORS headers"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

# Handler for batch status checking
def get_batch_status(event, context):
    """Get batch processing status"""
    
    try:
        batch_id = event['pathParameters']['batch_id']
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('BATCH_TABLE', 'DrDocBatches-prod'))
        
        response = table.get_item(Key={'batch_id': batch_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Batch not found'})
            }
        
        batch_info = response['Item']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(batch_info)
        }
        
    except Exception as e:
        print(f"Batch status error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }