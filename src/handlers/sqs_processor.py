import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """SQS processor - processes documents from queue"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['RESULTS_TABLE'])
    textract = boto3.client('textract')
    
    for record in event['Records']:
        message = json.loads(record['body'])
        doc_id = message['DocumentID']
        bucket = message['S3Bucket']
        key = message['S3Key']
        
        try:
            # Update status to processing
            table.update_item(
                Key={'DocumentID': doc_id},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={':status': 'processing'}
            )
            
            # Start Textract analysis
            response = textract.analyze_document(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}},
                FeatureTypes=['FORMS', 'TABLES']
            )
            
            # Extract basic data
            extracted_data = {}
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'KEY_VALUE_SET' and 'KEY' in block.get('EntityTypes', []):
                    key_text = ''
                    value_text = ''
                    
                    # Get key text
                    for relationship in block.get('Relationships', []):
                        if relationship['Type'] == 'CHILD':
                            for child_id in relationship['Ids']:
                                child_block = next((b for b in response['Blocks'] if b['Id'] == child_id), None)
                                if child_block and child_block['BlockType'] == 'WORD':
                                    key_text += child_block['Text'] + ' '
                    
                    # Get value text
                    for relationship in block.get('Relationships', []):
                        if relationship['Type'] == 'VALUE':
                            for value_id in relationship['Ids']:
                                value_block = next((b for b in response['Blocks'] if b['Id'] == value_id), None)
                                if value_block:
                                    for val_rel in value_block.get('Relationships', []):
                                        if val_rel['Type'] == 'CHILD':
                                            for child_id in val_rel['Ids']:
                                                child_block = next((b for b in response['Blocks'] if b['Id'] == child_id), None)
                                                if child_block and child_block['BlockType'] == 'WORD':
                                                    value_text += child_block['Text'] + ' '
                    
                    if key_text.strip() and value_text.strip():
                        extracted_data[key_text.strip()] = value_text.strip()
            
            # Update with results
            table.update_item(
                Key={'DocumentID': doc_id},
                UpdateExpression='SET #status = :status, #data = :data, ProcessedAt = :processed_at',
                ExpressionAttributeNames={
                    '#status': 'Status',
                    '#data': 'Data'
                },
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':data': extracted_data,
                    ':processed_at': datetime.now().isoformat()
                }
            )
            
            print(f"Successfully processed document {doc_id}")
            
        except Exception as e:
            print(f"Error processing document {doc_id}: {str(e)}")
            
            # Update status to failed
            table.update_item(
                Key={'DocumentID': doc_id},
                UpdateExpression='SET #status = :status, ErrorMessage = :error',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': str(e)
                }
            )
    
    return {'statusCode': 200}