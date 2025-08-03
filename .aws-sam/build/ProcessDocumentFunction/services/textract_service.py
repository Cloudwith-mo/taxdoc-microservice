import boto3
from typing import Dict, Any

class TextractService:
    def __init__(self):
        self.client = boto3.client('textract')
    
    def analyze_document(self, bucket: str, key: str) -> Dict[str, Any]:
        """Extract text and form data from document using Textract"""
        
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
    
    def _is_expense_document(self, key: str) -> bool:
        """Simple heuristic to determine if document is likely an expense/receipt"""
        expense_keywords = ['receipt', 'invoice', 'bill']
        return any(keyword in key.lower() for keyword in expense_keywords)
    
    def extract_text_blocks(self, response: Dict[str, Any]) -> str:
        """Extract all text from Textract response"""
        text_lines = []
        
        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)