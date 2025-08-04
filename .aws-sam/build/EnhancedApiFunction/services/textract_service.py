import boto3
from typing import Dict, Any

class TextractService:
    def __init__(self):
        self.client = boto3.client('textract')
    
    def detect_document_text_bytes(self, document_bytes: bytes) -> Dict[str, Any]:
        """Extract text from document bytes using Textract"""
        try:
            return self.client.detect_document_text(
                Document={'Bytes': document_bytes}
            )
        except Exception as e:
            print(f"Textract detect_document_text failed: {e}")
            return {'Blocks': []}
    
    def analyze_document(self, bucket: str, key: str) -> Dict[str, Any]:
        """Extract text and form data from document using Textract"""
        
        # Check if file is a text file (Textract doesn't support plain text)
        if key.lower().endswith('.txt'):
            return self._handle_text_file(bucket, key)
        
        try:
            # Determine if it's likely an expense document
            if self._is_expense_document(key):
                return self.client.analyze_expense(
                    Document={'S3Object': {'Bucket': bucket, 'Name': key}}
                )
            else:
                # Use general document analysis with forms
                return self.client.analyze_document(
                    Document={'S3Object': {'Bucket': bucket, 'Name': key}},
                    FeatureTypes=['FORMS', 'TABLES']
                )
        except Exception as e:
            if 'UnsupportedDocumentException' in str(e):
                return self._handle_text_file(bucket, key)
            else:
                raise e
    
    def _is_expense_document(self, key: str) -> bool:
        """Simple heuristic to determine if document is likely an expense/receipt"""
        expense_keywords = ['receipt', 'invoice', 'bill']
        return any(keyword in key.lower() for keyword in expense_keywords)
    
    def _handle_text_file(self, bucket: str, key: str) -> Dict[str, Any]:
        """Handle plain text files by reading content directly from S3"""
        import boto3
        
        s3_client = boto3.client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        text_content = response['Body'].read().decode('utf-8')
        
        # Convert text to Textract-like format
        lines = text_content.strip().split('\n')
        blocks = []
        
        for i, line in enumerate(lines):
            if line.strip():
                blocks.append({
                    'BlockType': 'LINE',
                    'Id': f'line_{i}',
                    'Text': line.strip(),
                    'Confidence': 99.0
                })
        
        return {
            'Blocks': blocks,
            'DocumentMetadata': {
                'Pages': 1
            }
        }
    
    def extract_text_blocks(self, response: Dict[str, Any]) -> str:
        """Extract all text from Textract response"""
        text_lines = []
        
        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)
    
    def get_text_from_response(self, textract_response: Dict[str, Any]) -> str:
        """Extract plain text from Textract response for Bedrock"""
        return self.extract_text_blocks(textract_response)
    
    def start_async_analysis(self, bucket: str, key: str) -> str:
        """Start async Textract job and return JobId"""
        import os
        
        try:
            if self._is_expense_document(key):
                response = self.client.start_expense_analysis(
                    DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}},
                    NotificationChannel={
                        'SNSTopicArn': os.environ['TEXTRACT_SNS_TOPIC'],
                        'RoleArn': os.environ['TEXTRACT_ROLE_ARN']
                    },
                    JobTag='TaxDoc-Expense'
                )
            else:
                response = self.client.start_document_analysis(
                    DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}},
                    FeatureTypes=['FORMS', 'TABLES'],
                    NotificationChannel={
                        'SNSTopicArn': os.environ['TEXTRACT_SNS_TOPIC'],
                        'RoleArn': os.environ['TEXTRACT_ROLE_ARN']
                    },
                    JobTag='TaxDoc-Analysis'
                )
            
            return response['JobId']
        except Exception as e:
            print(f"Error starting async Textract job: {e}")
            raise e
    
    def get_async_results(self, job_id: str, job_type: str = 'analysis') -> Dict[str, Any]:
        """Retrieve async Textract results with pagination"""
        pages = []
        next_token = None
        
        try:
            while True:
                if job_type == 'expense':
                    if next_token:
                        response = self.client.get_expense_analysis(JobId=job_id, NextToken=next_token)
                    else:
                        response = self.client.get_expense_analysis(JobId=job_id)
                else:
                    if next_token:
                        response = self.client.get_document_analysis(JobId=job_id, NextToken=next_token)
                    else:
                        response = self.client.get_document_analysis(JobId=job_id)
                
                pages.append(response)
                next_token = response.get('NextToken')
                if not next_token:
                    break
            
            # Combine all pages
            if job_type == 'expense':
                combined_docs = []
                for page in pages:
                    combined_docs.extend(page.get('ExpenseDocuments', []))
                return {'ExpenseDocuments': combined_docs}
            else:
                combined_blocks = []
                for page in pages:
                    combined_blocks.extend(page.get('Blocks', []))
                return {'Blocks': combined_blocks}
                
        except Exception as e:
            print(f"Error retrieving async results: {e}")
            raise e