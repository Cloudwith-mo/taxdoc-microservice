"""
Tax Document Classifier for V1 MVP
Focuses only on W-2 and 1099 forms
"""
import re
from typing import Dict, Any

class TaxClassifier:
    """Simple classifier for tax documents"""
    
    def __init__(self):
        # Keywords for tax form identification
        self.tax_keywords = {
            "W-2": [
                "w-2", "w2", "wage and tax statement", 
                "employee's social security", "employer identification",
                "wages, tips, other compensation"
            ],
            "1099-NEC": [
                "1099-nec", "1099 nec", "nonemployee compensation",
                "payer's federal identification", "recipient's identification"
            ],
            "1099-MISC": [
                "1099-misc", "1099 misc", "miscellaneous income",
                "rents", "royalties"
            ],
            "1099-DIV": [
                "1099-div", "1099 div", "dividends and distributions",
                "ordinary dividends", "qualified dividends"
            ],
            "1099-INT": [
                "1099-int", "1099 int", "interest income",
                "interest income"
            ]
        }
    
    def classify_tax_document(self, textract_response: Dict[str, Any]) -> str:
        """
        Classify document based on Textract OCR output
        Returns: Document type or "Unsupported"
        """
        # Extract all text from Textract response
        text_content = self._extract_text_from_textract(textract_response)
        text_lower = text_content.lower()
        
        # Check for each tax form type
        for form_type, keywords in self.tax_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return form_type
        
        # If no tax form keywords found, it's unsupported
        return "Unsupported"
    
    def _extract_text_from_textract(self, textract_response: Dict[str, Any]) -> str:
        """Extract all text content from Textract response"""
        text_blocks = []
        
        for block in textract_response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                text = block.get('Text', '').strip()
                if text:
                    text_blocks.append(text)
        
        return ' '.join(text_blocks)