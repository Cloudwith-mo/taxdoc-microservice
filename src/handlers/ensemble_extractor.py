"""
Ensemble extraction with multiple sources and confidence scoring
"""
import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class FieldValue:
    value: Optional[str]
    confidence: float
    source: str
    bbox: Optional[Dict] = None

@dataclass
class PayStub:
    classification: Dict[str, Any]
    fields: Dict[str, FieldValue]
    line_items: Dict[str, List[Dict]]
    needs_review: bool

class EnsembleExtractor:
    """Multi-source extraction with fallbacks and validation"""
    
    def __init__(self):
        self.sources = ['textract_query', 'textract_form', 'pattern', 'tesseract']
        self.required_fields = [
            'employee_name', 'employer_name', 'pay_date', 
            'gross_pay_current', 'net_pay_current'
        ]
    
    def extract_paystub(self, document_bytes: bytes, full_text: str) -> PayStub:
        """Extract paystub using ensemble approach"""
        
        # Step 1: Primary extraction (Textract Queries)
        textract_fields = self.extract_with_textract_queries(document_bytes)
        
        # Step 2: Fallback extraction (Patterns)
        pattern_fields = self.extract_with_patterns(full_text)
        
        # Step 3: Merge with confidence-based precedence
        merged_fields = self.merge_extractions(textract_fields, pattern_fields)
        
        # Step 4: Validate and determine review status
        needs_review = self.validate_extraction(merged_fields)
        
        # Step 5: Extract line items
        line_items = self.extract_line_items(full_text)
        
        classification = {
            'type': 'PAYSTUB',
            'confidence': self.calculate_overall_confidence(merged_fields)
        }
        
        return PayStub(
            classification=classification,
            fields=merged_fields,
            line_items=line_items,
            needs_review=needs_review
        )
    
    def extract_with_textract_queries(self, document_bytes: bytes) -> Dict[str, FieldValue]:
        """Primary extraction using Textract Queries"""
        # Placeholder - would call actual Textract API
        return {
            'employee_name': FieldValue('John Doe', 0.95, 'textract_query', 
                                      {'Left': 0.1, 'Top': 0.15, 'Width': 0.3, 'Height': 0.03}),
            'employer_name': FieldValue('ACME Corp', 0.92, 'textract_query',
                                      {'Left': 0.1, 'Top': 0.08, 'Width': 0.25, 'Height': 0.03}),
            'gross_pay_current': FieldValue('2500.00', 0.94, 'textract_query',
                                          {'Left': 0.7, 'Top': 0.4, 'Width': 0.15, 'Height': 0.03}),
            'net_pay_current': FieldValue('1875.00', 0.96, 'textract_query',
                                        {'Left': 0.7, 'Top': 0.7, 'Width': 0.15, 'Height': 0.03})
        }
    
    def extract_with_patterns(self, text: str) -> Dict[str, FieldValue]:
        """Fallback extraction using regex patterns"""
        fields = {}
        
        # Date patterns
        pay_date_match = re.search(r'pay\s+date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.I)
        if pay_date_match:
            fields['pay_date'] = FieldValue(
                self.normalize_date(pay_date_match.group(1)), 
                0.75, 'pattern'
            )
        
        # Money patterns
        gross_match = re.search(r'gross\s+pay[:\s]+\$?([0-9,]+\.?\d{0,2})', text, re.I)
        if gross_match:
            fields['gross_pay_current'] = FieldValue(
                self.normalize_money(gross_match.group(1)), 
                0.70, 'pattern'
            )
        
        net_match = re.search(r'net\s+pay[:\s]+\$?([0-9,]+\.?\d{0,2})', text, re.I)
        if net_match:
            fields['net_pay_current'] = FieldValue(
                self.normalize_money(net_match.group(1)), 
                0.70, 'pattern'
            )
        
        return fields
    
    def merge_extractions(self, primary: Dict[str, FieldValue], 
                         fallback: Dict[str, FieldValue]) -> Dict[str, FieldValue]:
        """Merge extractions with confidence-based precedence"""
        merged = {}
        
        # Get all unique field names
        all_fields = set(primary.keys()) | set(fallback.keys())
        
        for field_name in all_fields:
            primary_field = primary.get(field_name)
            fallback_field = fallback.get(field_name)
            
            # Choose based on confidence and availability
            if primary_field and primary_field.confidence >= 0.6:
                merged[field_name] = primary_field
            elif fallback_field and fallback_field.confidence >= 0.5:
                merged[field_name] = fallback_field
            elif primary_field:  # Use primary even if low confidence
                merged[field_name] = primary_field
            elif fallback_field:  # Use fallback as last resort
                merged[field_name] = fallback_field
        
        return merged
    
    def validate_extraction(self, fields: Dict[str, FieldValue]) -> bool:
        """Validate extraction and determine if review is needed"""
        needs_review = False
        
        # Check required fields
        for field_name in self.required_fields:
            if field_name not in fields or not fields[field_name].value:
                needs_review = True
                break
        
        # Check confidence thresholds
        for field in fields.values():
            if field.confidence < 0.6:
                needs_review = True
                break
        
        # Math validation
        try:
            gross = float(fields.get('gross_pay_current', FieldValue('0', 0, '')).value or '0')
            net = float(fields.get('net_pay_current', FieldValue('0', 0, '')).value or '0')
            
            # Simple validation: net should be less than gross
            if net > gross:
                needs_review = True
        except (ValueError, TypeError):
            needs_review = True
        
        return needs_review
    
    def extract_line_items(self, text: str) -> Dict[str, List[Dict]]:
        """Extract earnings and deductions line items"""
        earnings = []
        deductions = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            # Look for earnings patterns
            if any(keyword in line.lower() for keyword in ['regular', 'overtime', 'bonus']):
                amount_match = re.search(r'\$?([0-9,]+\.?\d{0,2})', line)
                if amount_match:
                    earnings.append({
                        'type': line.split()[0] if line.split() else 'Unknown',
                        'amount_current': self.normalize_money(amount_match.group(1)),
                        'amount_ytd': '0.00'  # Would extract YTD if available
                    })
            
            # Look for deduction patterns
            elif any(keyword in line.lower() for keyword in ['tax', 'insurance', '401k', 'medicare']):
                amount_match = re.search(r'\$?([0-9,]+\.?\d{0,2})', line)
                if amount_match:
                    deductions.append({
                        'type': line.split()[0] if line.split() else 'Unknown',
                        'amount_current': self.normalize_money(amount_match.group(1)),
                        'amount_ytd': '0.00'
                    })
        
        return {'earnings': earnings, 'deductions': deductions}
    
    def calculate_overall_confidence(self, fields: Dict[str, FieldValue]) -> float:
        """Calculate overall document confidence"""
        if not fields:
            return 0.0
        
        confidences = [field.confidence for field in fields.values()]
        return sum(confidences) / len(confidences)
    
    def normalize_money(self, value: str) -> str:
        """Normalize money to standard format"""
        if not value:
            return '0.00'
        
        # Remove non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', value)
        try:
            return f"{float(cleaned):.2f}"
        except ValueError:
            return '0.00'
    
    def normalize_date(self, value: str) -> str:
        """Normalize date to YYYY-MM-DD format"""
        if not value:
            return ''
        
        # Try common date formats
        from datetime import datetime
        formats = ['%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%m/%d/%y']
        
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return value  # Return original if no format matches

# Usage example
def process_document(document_bytes: bytes, full_text: str) -> dict:
    """Process document and return structured result"""
    extractor = EnsembleExtractor()
    result = extractor.extract_paystub(document_bytes, full_text)
    
    # Convert to JSON-serializable format
    return {
        'classification': result.classification,
        'fields': {
            name: {
                'value': field.value,
                'confidence': field.confidence,
                'source': field.source,
                'bbox': field.bbox
            }
            for name, field in result.fields.items()
        },
        'line_items': result.line_items,
        'needs_review': result.needs_review
    }