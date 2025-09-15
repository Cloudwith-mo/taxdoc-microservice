import json
import boto3
import logging
import requests
from datetime import datetime

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')
ssm = boto3.client('ssm')

# Table
table = dynamodb.Table('documentgpt-docs')

def lambda_handler(event, context):
    logger.info(f"Processing event: {json.dumps(event)}")
    
    for record in event['Records']:
        try:
            # Parse SQS message
            body = json.loads(record['body'])
            logger.info(f"Processing message: {body}")
            
            doc_id = body.get('docId')
            doc_name = body.get('docName')
            bucket = body.get('bucket')
            key = body.get('key')
            
            if not all([doc_id, doc_name, bucket, key]):
                logger.error(f"Missing required fields: {body}")
                continue
            
            # Update status to processing
            update_status(doc_id, 'processing')
            
            # Check if S3 object exists
            try:
                s3.head_object(Bucket=bucket, Key=key)
                logger.info(f"S3 object found: s3://{bucket}/{key}")
            except Exception as e:
                logger.error(f"S3 object not found: s3://{bucket}/{key} - {str(e)}")
                update_status(doc_id, 'error', f"File not found: {str(e)}")
                continue
            
            # Process with Textract
            logger.info(f"Starting Textract processing for {key}")
            textract_response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                }
            )
            
            # Extract text
            extracted_text = ""
            for block in textract_response['Blocks']:
                if block['BlockType'] == 'LINE':
                    extracted_text += block['Text'] + "\n"
            
            logger.info(f"Extracted {len(extracted_text)} characters of text")
            
            if len(extracted_text.strip()) < 10:
                logger.warning("Very little text extracted, marking as completed without indexing")
                update_status(doc_id, 'completed', "No meaningful text found")
                continue
            
            # Get OpenAI API key
            openai_key = get_parameter('/documentgpt/openai_api_key')
            
            # Create embeddings
            logger.info("Creating embeddings with OpenAI")
            embedding = create_embedding(extracted_text, openai_key)
            
            # Update DynamoDB with results (fixed reserved keyword issue)
            table.update_item(
                Key={
                    'tenant': 'default',
                    'docId': doc_id
                },
                UpdateExpression='SET #status = :status, extractedText = :text, processedAt = :timestamp, isIndexed = :indexed, embeddingSize = :embedding',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':text': extracted_text[:5000],
                    ':timestamp': datetime.utcnow().isoformat(),
                    ':indexed': True,
                    ':embedding': len(embedding)
                }
            )
            
            logger.info(f"Successfully processed and indexed document {doc_id}")
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            if 'doc_id' in locals():
                update_status(doc_id, 'error', str(e))

def get_parameter(param_name):
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise

def create_embedding(text, openai_key):
    try:
        # Chunk text if too long (OpenAI limit ~8000 tokens)
        if len(text) > 6000:
            text = text[:6000]
        
        response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {openai_key}',
                'Content-Type': 'application/json'
            },
            json={
                'input': text,
                'model': 'text-embedding-ada-002'
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        embedding = response.json()['data'][0]['embedding']
        logger.info(f"Created embedding with {len(embedding)} dimensions")
        return embedding
        
    except Exception as e:
        logger.error(f"Failed to create embedding: {str(e)}")
        raise

def update_status(doc_id, status, error_msg=None):
    try:
        update_expr = 'SET #status = :status, updatedAt = :timestamp'
        expr_values = {
            ':status': status,
            ':timestamp': datetime.utcnow().isoformat()
        }
        
        if error_msg:
            update_expr += ', errorMessage = :error'
            expr_values[':error'] = error_msg
        
        table.update_item(
            Key={
                'tenant': 'default',
                'docId': doc_id
            },
            UpdateExpression=update_expr,
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues=expr_values
        )
        logger.info(f"Updated status for {doc_id}: {status}")
    except Exception as e:
        logger.error(f"Failed to update status: {str(e)}")