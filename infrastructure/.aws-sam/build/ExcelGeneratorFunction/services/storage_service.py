import boto3
import json
from datetime import datetime
from typing import Dict, Any

class StorageService:
    def __init__(self):
        import os
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ.get('RESULTS_TABLE', 'TaxDocuments-dev')
        
    def save_document_metadata(self, document_data: Dict[str, Any]) -> None:
        """Save document metadata to DynamoDB"""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # Prepare item for DynamoDB
            item = {
                'DocumentID': document_data['DocumentID'],
                'DocumentType': document_data['DocumentType'],
                'UploadDate': document_data['UploadDate'],
                'S3Location': document_data['S3Location'],
                'ProcessingStatus': document_data['ProcessingStatus'],
                'Data': json.dumps(document_data['Data']),  # Store as JSON string
                'CreatedAt': datetime.utcnow().isoformat()
            }
            
            # Add error info if processing failed
            if 'Error' in document_data:
                item['Error'] = document_data['Error']
            
            table.put_item(Item=item)
            
        except Exception as e:
            print(f"Error saving to DynamoDB: {str(e)}")
            # Fallback: save to S3
            self._save_to_s3_fallback(document_data)
    
    def get_document_metadata(self, document_id: str) -> Dict[str, Any]:
        """Retrieve document metadata from DynamoDB"""
        try:
            table = self.dynamodb.Table(self.table_name)
            response = table.get_item(Key={'DocumentID': document_id})
            
            if 'Item' in response:
                item = response['Item']
                # Parse JSON data back to dict
                if 'Data' in item:
                    item['Data'] = json.loads(item['Data'])
                return item
            else:
                return {}
                
        except Exception as e:
            print(f"Error retrieving from DynamoDB: {str(e)}")
            return {}
    
    def _save_to_s3_fallback(self, document_data: Dict[str, Any]) -> None:
        """Fallback method to save results to S3 if DynamoDB fails"""
        try:
            s3 = boto3.client('s3')
            bucket = 'taxdoc-results'  # Environment variable in production
            key = f"processed/{document_data['DocumentID']}.json"
            
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(document_data, indent=2),
                ContentType='application/json'
            )
            
        except Exception as e:
            print(f"Error saving to S3 fallback: {str(e)}")