import re
from typing import Dict, Any, List

class RegexFallbackService:
    """Layer 3: Regex fallback for critical field extraction"""
    
    def __init__(self):
        self.patterns = {
            # Common patterns across document types
            'ssn': r'(?:ssn|social security|ss#)[\s:]*(\d{3}-\d{2}-\d{4})',
            'ein': r'(?:ein|employer id|tax id)[\s:]*(\d{2}-\d{7})',
            'phone': r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
            'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            'amount': r'\$?([\d,]+\.?\d{0,2})',
            'zip_code': r'(\d{5}(?:-\d{4})?)',
            'year': r'(20\d{2})'
        }
    
    def extract_missing_fields(self, document_text: str, missing_fields: List[str]) -> Dict[str, Any]:
        """Extract fields using regex patterns as fallback"""
        
        results = {}
        text_lower = document_text.lower()
        
        for field in missing_fields:
            pattern = self._get_pattern_for_field(field)
            if pattern:
                match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
                    results[field] = {
                        'value': self._clean_value(value, field),
                        'confidence': 0.6,  # Medium confidence for regex
                        'source': 'regex_fallback'
                    }
        
        return results
    
    def _get_pattern_for_field(self, field_name: str) -> str:
        """Get regex pattern for field based on field name"""
        
        field_lower = field_name.lower()
        
        # SSN patterns
        if 'ssn' in field_lower or 'social' in field_lower:
            return self.patterns['ssn']
        
        # EIN patterns
        if 'ein' in field_lower or 'employer' in field_lower:
            return self.patterns['ein']
        
        # Phone patterns
        if 'phone' in field_lower:
            return self.patterns['phone']
        
        # Email patterns
        if 'email' in field_lower:
            return self.patterns['email']
        
        # Date patterns
        if 'date' in field_lower:
            return self.patterns['date']
        
        # Amount/monetary patterns
        if any(keyword in field_lower for keyword in ['amount', 'wage', 'tax', 'income', 'pay']):
            return self.patterns['amount']
        
        # Zip code patterns
        if 'zip' in field_lower or 'postal' in field_lower:
            return self.patterns['zip_code']
        
        # Year patterns
        if 'year' in field_lower:
            return self.patterns['year']
        
        return None
    
    def _clean_value(self, value: str, field_name: str) -> Any:
        """Clean extracted value based on field type"""
        
        if not value:
            return None
        
        field_lower = field_name.lower()
        
        # Monetary values
        if any(keyword in field_lower for keyword in ['amount', 'wage', 'tax', 'income', 'pay']):
            cleaned = re.sub(r'[^\d.]', '', value)
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        
        # Year values
        if 'year' in field_lower:
            try:
                return int(value)
            except ValueError:
                return None
        
        # Default: return cleaned string
        return value.strip()