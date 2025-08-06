import boto3
from typing import Dict, Any

class TextractExtractor:
    """Simple Textract text extraction"""
    
    def __init__(self):
        self.client = boto3.client('textract', region_name='us-east-1')
    
    def extract_text(self, document_bytes: bytes) -> Dict[str, Any]:
        """Extract text using Textract synchronous API"""
        
        try:
            response = self.client.detect_document_text(
                Document={'Bytes': document_bytes}
            )
            return response
            
        except Exception as e:
            print(f"Textract extraction failed: {e}")
            return {'Blocks': []}