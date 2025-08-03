import pytest
from src.services.classifier_service import ClassifierService

class TestClassifierService:
    def setup_method(self):
        self.classifier = ClassifierService()
    
    def test_classify_w2_form(self):
        # Mock Textract response with W-2 text
        mock_response = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'W-2 Wage and Tax Statement'
                },
                {
                    'BlockType': 'LINE', 
                    'Text': 'Employee Social Security Number'
                }
            ]
        }
        
        result = self.classifier.classify_document(mock_response)
        assert result == "W-2 Tax Form"
    
    def test_classify_receipt(self):
        mock_response = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'Thank you for your purchase'
                },
                {
                    'BlockType': 'LINE',
                    'Text': 'Subtotal: $25.99'
                }
            ]
        }
        
        result = self.classifier.classify_document(mock_response)
        assert result == "Receipt"
    
    def test_classify_invoice(self):
        mock_response = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'Invoice #12345'
                },
                {
                    'BlockType': 'LINE',
                    'Text': 'Bill To: Customer Name'
                }
            ]
        }
        
        result = self.classifier.classify_document(mock_response)
        assert result == "Invoice"
    
    def test_classify_unknown_document(self):
        mock_response = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'Some random document text'
                }
            ]
        }
        
        result = self.classifier.classify_document(mock_response)
        assert result == "Other Document"