import boto3
import json
from typing import Dict, Any, Tuple
from .enhanced_textract_service import EnhancedTextractService
from .three_layer_orchestrator import ThreeLayerOrchestrator
from .enhanced_classifier import EnhancedClassifier
from config.document_config import DOCUMENT_CONFIGS

class TaxFormProcessor:
    """Enhanced processor using three-layer extraction like production"""
    
    def __init__(self):
        self.classifier = EnhancedClassifier()
        self.orchestrator = ThreeLayerOrchestrator()
        self.textract = EnhancedTextractService()
    
    def process_tax_document(self, document_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Enhanced processing pipeline using three-layer extraction"""
        
        try:
            # Step 1: Basic text extraction for classification
            textract_response = self.textract.client.detect_document_text(
                Document={'Bytes': document_bytes}
            )
            
            # Step 2: Classify document type
            form_type, confidence = self.classifier.classify_document(textract_response)
            
            if form_type not in DOCUMENT_CONFIGS:
                return {
                    'success': False,
                    'error': f'Unsupported form type: {form_type}',
                    'supported_forms': list(DOCUMENT_CONFIGS.keys())
                }
            
            # Step 3: Use three-layer orchestrator for comprehensive extraction
            extraction_result = self.orchestrator.extract_document_fields(document_bytes, form_type)
            
            # Convert to MVP format for compatibility
            return {
                'success': True,
                'form_type': form_type,
                'classification_confidence': confidence,
                'extracted_fields': extraction_result.get('ExtractedData', {}),
                'field_count': len(extraction_result.get('ExtractedData', {})),
                'filename': filename,
                'DocumentType': extraction_result.get('DocumentType'),
                'ExtractedData': extraction_result.get('ExtractedData', {}),
                'ExtractionMetadata': extraction_result.get('ExtractionMetadata', {}),
                'QualityMetrics': extraction_result.get('QualityMetrics', {})
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }