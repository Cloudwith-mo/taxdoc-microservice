import re
from typing import Dict, Any

class FieldValidator:
    """Basic field validation for tax forms"""
    
    def validate_fields(self, fields: Dict[str, Any], form_type: str) -> Dict[str, Any]:
        """Validate and clean extracted fields"""
        
        validated = {}
        
        for field_name, value in fields.items():
            if value is None or value == "":
                continue
                
            # Clean and validate based on field type
            if 'ssn' in field_name.lower():
                validated[field_name] = self._validate_ssn(value)
            elif 'ein' in field_name.lower() or 'tin' in field_name.lower():
                validated[field_name] = self._validate_ein(value)
            elif 'box' in field_name.lower() or 'wages' in field_name.lower() or 'tax' in field_name.lower():
                validated[field_name] = self._validate_amount(value)
            else:
                validated[field_name] = str(value).strip()
        
        return validated
    
    def _validate_ssn(self, value: str) -> str:
        """Validate and format SSN"""
        
        # Extract digits only
        digits = re.sub(r'[^\d]', '', str(value))
        
        if len(digits) == 9:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        
        return str(value).strip()
    
    def _validate_ein(self, value: str) -> str:
        """Validate and format EIN"""
        
        # Extract digits only
        digits = re.sub(r'[^\d]', '', str(value))
        
        if len(digits) == 9:
            return f"{digits[:2]}-{digits[2:]}"
        
        return str(value).strip()
    
    def _validate_amount(self, value: Any) -> float:
        """Validate and convert monetary amounts"""
        
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.]', '', str(value))
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0