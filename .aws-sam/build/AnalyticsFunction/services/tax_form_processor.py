import boto3
import json
from typing import Dict, Any, Tuple
from .tax_form_classifier import TaxFormClassifier
from .textract_extractor import TextractExtractor
from .claude_extractor import ClaudeExtractor
from .field_validator import FieldValidator

class TaxFormProcessor:
    """Simplified processor for W-2 and 1099 forms only"""
    
    def __init__(self):
        self.classifier = TaxFormClassifier()
        self.textract = TextractExtractor()
        self.claude = ClaudeExtractor()
        self.validator = FieldValidator()
    
    def process_tax_document(self, document_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Main processing pipeline for tax documents"""
        
        try:
            # Step 1: Extract text with Textract
            textract_response = self.textract.extract_text(document_bytes)
            
            # Step 2: Classify form type
            form_type, confidence = self.classifier.classify_form(textract_response)
            
            if form_type not in ['W-2', '1099-NEC', '1099-INT', '1099-DIV', '1099-MISC']:
                return {
                    'success': False,
                    'error': f'Unsupported form type: {form_type}',
                    'supported_forms': ['W-2', '1099-NEC', '1099-INT', '1099-DIV', '1099-MISC']
                }
            
            # Step 3: Extract fields with Claude
            extracted_fields = self.claude.extract_fields(textract_response, form_type)
            
            # Step 4: Validate and format results
            validated_fields = self.validator.validate_fields(extracted_fields, form_type)
            
            return {
                'success': True,
                'form_type': form_type,
                'classification_confidence': confidence,
                'extracted_fields': validated_fields,
                'field_count': len(validated_fields),
                'filename': filename
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }