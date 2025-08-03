import re
from typing import Dict, Any

class ClassifierService:
    def classify_document(self, textract_response: Dict[str, Any]) -> str:
        """Classify document type based on extracted text"""
        
        # Extract all text for classification
        text = self._extract_all_text(textract_response).lower()
        
        # Rule-based classification
        if self._is_w2_form(text):
            return "W-2 Tax Form"
        elif self._is_1099_form(text):
            return "1099 Tax Form"
        elif self._is_invoice(text):
            return "Invoice"
        elif self._is_receipt(text):
            return "Receipt"
        elif self._is_bank_statement(text):
            return "Bank Statement"
        else:
            return "Other Document"
    
    def _extract_all_text(self, response: Dict[str, Any]) -> str:
        """Extract all text from Textract response"""
        text_lines = []
        
        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
        elif 'ExpenseDocuments' in response:
            # Handle expense analysis response
            for doc in response['ExpenseDocuments']:
                for line_item in doc.get('LineItemGroups', []):
                    for item in line_item.get('LineItems', []):
                        for field in item.get('LineItemExpenseFields', []):
                            if 'ValueDetection' in field:
                                text_lines.append(field['ValueDetection']['Text'])
        
        return '\n'.join(text_lines)
    
    def _is_w2_form(self, text: str) -> bool:
        return bool(re.search(r'w-?2|wage and tax statement', text))
    
    def _is_1099_form(self, text: str) -> bool:
        return bool(re.search(r'1099|miscellaneous income', text))
    
    def _is_invoice(self, text: str) -> bool:
        invoice_patterns = [r'invoice\s*#?', r'bill\s*to', r'invoice\s*date']
        return any(re.search(pattern, text) for pattern in invoice_patterns)
    
    def _is_receipt(self, text: str) -> bool:
        receipt_patterns = [r'receipt', r'thank you', r'subtotal', r'total\s*amount']
        return any(re.search(pattern, text) for pattern in receipt_patterns)
    
    def _is_bank_statement(self, text: str) -> bool:
        return bool(re.search(r'statement|account\s*summary|beginning\s*balance', text))