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
            # Validate input type
            if not isinstance(document_data, dict):
                print(f"ERROR: document_data is not a dict: {type(document_data)} - {document_data}")
                return
                
            table = self.dynamodb.Table(self.table_name)
            
            # Prepare item for DynamoDB
            item = {
                'DocumentID': document_data.get('DocumentID', 'unknown'),
                'DocumentType': document_data.get('DocumentType', 'Unknown'),
                'UploadDate': document_data.get('UploadDate', datetime.utcnow().isoformat()),
                'S3Location': document_data.get('S3Location', ''),
                'ProcessingStatus': document_data.get('ProcessingStatus', 'Pending'),
                'CreatedAt': datetime.utcnow().isoformat()
            }
            
            # Add data if present
            if 'Data' in document_data:
                item['Data'] = json.dumps(document_data['Data'])
            
            # Add job metadata
            if 'TextractJobId' in document_data:
                item['TextractJobId'] = document_data['TextractJobId']
            
            # Add error info if processing failed
            if 'Error' in document_data:
                item['Error'] = document_data['Error']
            if 'ErrorType' in document_data:
                item['ErrorType'] = document_data['ErrorType']
            
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
    
    def update_job_status(self, job_id: str, status_data: Dict[str, Any]) -> None:
        """Update job status in DynamoDB"""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # Build update expression
            update_expr = "SET "
            expr_values = {}
            
            for key, value in status_data.items():
                update_expr += f"{key} = :{key.lower()}, "
                expr_values[f":{key.lower()}"] = value
            
            update_expr = update_expr.rstrip(", ")
            update_expr += ", UpdatedAt = :updated"
            expr_values[":updated"] = datetime.utcnow().isoformat()
            
            table.update_item(
                Key={'DocumentID': job_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
            
        except Exception as e:
            print(f"Error updating job status: {str(e)}")
    
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