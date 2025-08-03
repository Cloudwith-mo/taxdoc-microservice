import boto3
from typing import Dict, Any

class TextractService:
    def __init__(self):
        self.client = boto3.client('textract')
    
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