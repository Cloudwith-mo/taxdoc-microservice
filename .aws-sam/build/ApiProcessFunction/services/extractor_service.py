import re
from typing import Dict, Any, Optional
from decimal import Decimal

class ExtractorService:
    def extract_fields(self, textract_response: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Extract key fields based on document type"""
        
        if doc_type == "Receipt":
            return self._extract_receipt_fields(textract_response)
        elif doc_type == "Invoice":
            return self._extract_invoice_fields(textract_response)
        elif doc_type == "W-2 Tax Form":
            return self._extract_w2_fields(textract_response)
        elif doc_type == "Bank Statement":
            return self._extract_bank_statement_fields(textract_response)
        else:
            return self._extract_generic_fields(textract_response)
    
    def _extract_receipt_fields(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields specific to receipts"""
        fields = {}
        
        if 'ExpenseDocuments' in response:
            # Use Textract's expense analysis
            for doc in response['ExpenseDocuments']:
                summary_fields = doc.get('SummaryFields', [])
                for field in summary_fields:
                    field_type = field.get('Type', {}).get('Text', '')
                    if field_type == 'TOTAL':
                        fields['Total'] = self._extract_amount(field.get('ValueDetection', {}).get('Text', ''))
                    elif field_type == 'VENDOR_NAME':
                        fields['Vendor'] = field.get('ValueDetection', {}).get('Text', '')
                    elif field_type == 'INVOICE_RECEIPT_DATE':
                        fields['Date'] = field.get('ValueDetection', {}).get('Text', '')
        else:
            # Fallback to form extraction
            fields = self._extract_form_fields(response)
        
        return fields
    
    def _extract_invoice_fields(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields specific to invoices"""
        return self._extract_receipt_fields(response)  # Similar structure
    
    def _extract_w2_fields(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields specific to W-2 forms"""
        fields = {}
        text = self._get_full_text(response)
        
        # Extract common W-2 fields using regex
        fields['Wages'] = self._extract_currency_after_label(text, r'wages.*?tips.*?compensation')
        fields['FederalTaxWithheld'] = self._extract_currency_after_label(text, r'federal.*?income.*?tax.*?withheld')
        fields['SocialSecurityWages'] = self._extract_currency_after_label(text, r'social.*?security.*?wages')
        
        return {k: v for k, v in fields.items() if v is not None}
    
    def _extract_bank_statement_fields(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields specific to bank statements"""
        fields = {}
        text = self._get_full_text(response)
        
        # Extract account info and balances
        fields['BeginningBalance'] = self._extract_currency_after_label(text, r'beginning.*?balance')
        fields['EndingBalance'] = self._extract_currency_after_label(text, r'ending.*?balance')
        
        return {k: v for k, v in fields.items() if v is not None}
    
    def _extract_generic_fields(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract generic fields from any document"""
        text = self._get_full_text(response)
        
        # Extract common patterns
        fields = {
            'Dates': self._extract_dates(text),
            'Amounts': self._extract_amounts(text),
            'PhoneNumbers': self._extract_phone_numbers(text)
        }
        
        return {k: v for k, v in fields.items() if v}
    
    def _extract_form_fields(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key-value pairs from form analysis"""
        fields = {}
        
        if 'Blocks' not in response:
            return fields
        
        # Build relationships between keys and values
        key_map = {}
        value_map = {}
        
        for block in response['Blocks']:
            if block['BlockType'] == 'KEY_VALUE_SET':
                if 'KEY' in block.get('EntityTypes', []):
                    key_map[block['Id']] = block
                elif 'VALUE' in block.get('EntityTypes', []):
                    value_map[block['Id']] = block
        
        # Match keys with values
        for key_id, key_block in key_map.items():
            key_text = self._get_text_from_block(key_block, response['Blocks'])
            
            # Find corresponding value
            for relationship in key_block.get('Relationships', []):
                if relationship['Type'] == 'VALUE':
                    for value_id in relationship['Ids']:
                        if value_id in value_map:
                            value_text = self._get_text_from_block(value_map[value_id], response['Blocks'])
                            fields[key_text] = value_text
        
        return fields
    
    def _get_text_from_block(self, block: Dict[str, Any], all_blocks: list) -> str:
        """Get text content from a block by following relationships"""
        text_parts = []
        
        for relationship in block.get('Relationships', []):
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child_block = next((b for b in all_blocks if b['Id'] == child_id), None)
                    if child_block and child_block['BlockType'] == 'WORD':
                        text_parts.append(child_block['Text'])
        
        return ' '.join(text_parts)
    
    def _get_full_text(self, response: Dict[str, Any]) -> str:
        """Get all text from response"""
        text_lines = []
        
        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amount from text"""
        if not text:
            return None
        
        # Remove currency symbols and extract number
        amount_match = re.search(r'[\d,]+\.?\d*', text.replace('$', '').replace(',', ''))
        if amount_match:
            try:
                return float(amount_match.group())
            except ValueError:
                return None
        return None
    
    def _extract_currency_after_label(self, text: str, label_pattern: str) -> Optional[float]:
        """Extract currency amount that appears after a label"""
        pattern = label_pattern + r'.*?(\$?[\d,]+\.?\d*)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return self._extract_amount(match.group(1))
        return None
    
    def _extract_dates(self, text: str) -> list:
        """Extract date patterns from text"""
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\w+ \d{1,2}, \d{4}'
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text))
        
        return list(set(dates))
    
    def _extract_amounts(self, text: str) -> list:
        """Extract all monetary amounts from text"""
        amounts = re.findall(r'\$[\d,]+\.?\d*', text)
        return [self._extract_amount(amount) for amount in amounts if self._extract_amount(amount)]
    
    def _extract_phone_numbers(self, text: str) -> list:
        """Extract phone numbers from text"""
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        return re.findall(phone_pattern, text)