"""
Tax-Focused Three-Layer Orchestrator
Template-first pipeline with header-hash routing and IRS validation
"""
import hashlib
import re
from typing import Dict, Any, List
from .enhanced_textract_service import EnhancedTextractService
from .bedrock_claude_service import BedrockClaudeService
from .regex_fallback_service import RegexFallbackService
from .tax_validation_service import TaxValidationService
from config.tax_document_config import TAX_DOCUMENT_CONFIGS, SUPPORTED_TAX_FORMS, PII_MASKING_RULES

class UnsupportedTaxDocument(Exception):
    """Raised when document is not a supported tax form"""
    pass

class TaxOrchestrator:
    """Tax-focused document processor with template-first approach"""
    
    def __init__(self):
        self.textract_service = EnhancedTextractService()
        self.claude_service = BedrockClaudeService()
        self.regex_service = RegexFallbackService()
        self.validation_service = TaxValidationService()
        self.confidence_threshold = 0.85
        
        # Template cache for header-hash routing
        self.template_cache = {}
    
    def extract_tax_document(self, document_bytes: bytes, document_type: str = None) -> Dict[str, Any]:
        """Main tax extraction with template-first pipeline"""
        
        # Step 1: Document type validation
        if document_type and document_type not in SUPPORTED_TAX_FORMS:
            raise UnsupportedTaxDocument(f"Only federal tax forms supported. Email sales@taxflowsai.com")
        
        # Step 2: Header-hash routing for template selection
        if not document_type:
            document_type = self._detect_tax_form_type(document_bytes)
        
        if document_type not in SUPPORTED_TAX_FORMS:
            raise UnsupportedTaxDocument(f"Unsupported document type: {document_type}. Only federal tax forms supported.")
        
        # Step 3: Template-based extraction
        config = TAX_DOCUMENT_CONFIGS[document_type]
        
        # Layer 1: Textract TABLES + FORMS with bounding boxes
        textract_results = self._layer1_textract_structured(document_bytes, config)
        
        # Layer 2: Claude JSON mode with fixed schema
        claude_results = self._layer2_claude_json(document_bytes, document_type, textract_results)
        
        # Layer 3: Regex patterns for critical fields
        regex_results = self._layer3_regex_critical(document_bytes, document_type, textract_results, claude_results)
        
        # Step 4: Orchestrate results
        final_results = self._orchestrate_tax_results(textract_results, claude_results, regex_results, document_type)
        
        # Step 5: IRS validation layer
        validation_results = self.validation_service.validate_form_data(document_type, final_results['ExtractedData'])
        final_results['ValidationResults'] = validation_results
        
        # Step 6: PII masking
        final_results['ExtractedData'] = self._apply_pii_masking(final_results['ExtractedData'])
        
        return final_results
    
    def _detect_tax_form_type(self, document_bytes: bytes) -> str:
        """Header-hash routing for quick form detection"""
        
        # Extract first 2KB for header analysis
        header_text = self._extract_header_text(document_bytes, max_chars=2000)
        header_hash = hashlib.md5(header_text.encode()).hexdigest()[:8]
        
        # Check template cache first
        if header_hash in self.template_cache:
            return self.template_cache[header_hash]
        
        # Pattern matching for tax forms
        header_lower = header_text.lower()
        
        if any(keyword in header_lower for keyword in ["form 1040", "1040", "individual income tax"]):
            form_type = "1040"
        elif any(keyword in header_lower for keyword in ["w-2", "w2", "wage and tax statement"]):
            form_type = "W-2"
        elif "1099-nec" in header_lower or "nonemployee compensation" in header_lower:
            form_type = "1099-NEC"
        elif "1099-misc" in header_lower:
            form_type = "1099-MISC"
        elif "1099-div" in header_lower:
            form_type = "1099-DIV"
        elif "1099-int" in header_lower:
            form_type = "1099-INT"
        elif "schedule k-1" in header_lower and "1065" in header_lower:
            form_type = "K-1_1065"
        elif "schedule k-1" in header_lower and "1120s" in header_lower:
            form_type = "K-1_1120S"
        elif "form 941" in header_lower or "quarterly federal tax" in header_lower:
            form_type = "941"
        else:
            raise UnsupportedTaxDocument("Document type not recognized as federal tax form")
        
        # Cache the result
        self.template_cache[header_hash] = form_type
        return form_type
    
    def _layer1_textract_structured(self, document_bytes: bytes, config: Dict) -> Dict[str, Any]:
        """Layer 1: Textract with TABLES + FORMS analysis"""
        
        print(f"Layer 1: Textract structured extraction with {len(config['queries'])} queries")
        
        # Use both queries and form analysis
        response = self.textract_service.analyze_with_queries(document_bytes, config["queries"])
        results = self.textract_service.extract_query_answers(response)
        
        # Also analyze document structure for tables/forms
        try:
            form_response = self.textract_service.analyze_document_forms(document_bytes)
            form_results = self.textract_service.extract_form_fields(form_response)
            
            # Merge form results with query results
            for field, data in form_results.items():
                if field not in results or results[field]['confidence'] < data['confidence']:
                    results[field] = data
        except Exception as e:
            print(f"Form analysis failed: {e}")
        
        print(f"Layer 1: Extracted {len(results)} fields")
        return results
    
    def _layer2_claude_json(self, document_bytes: bytes, document_type: str, textract_results: Dict) -> Dict[str, Any]:
        """Layer 2: Claude JSON mode with fixed schema"""
        
        # Only process low-confidence fields to save costs
        low_confidence_fields = []
        for field, data in textract_results.items():
            if data['confidence'] < self.confidence_threshold:
                low_confidence_fields.append(field)
        
        if not low_confidence_fields:
            print("Layer 2: All Textract fields high confidence, skipping Claude (cost optimization)")
            return {}
        
        print(f"Layer 2: Claude JSON extraction for {len(low_confidence_fields)} low-confidence fields")
        
        # Extract document text
        document_text = self._extract_document_text(document_bytes)
        
        # Use deterministic Claude prompt with JSON schema
        config = TAX_DOCUMENT_CONFIGS[document_type]
        schema_fields = [field['name'] for field in config['fields']]
        
        enhanced_prompt = f\"\"\"{config['claude_prompt']}
        
        CRITICAL: Return ONLY valid JSON. If field not found, use null.
        Required schema: {{{', '.join([f'"{field}": null' for field in schema_fields])}}}
        Focus on these low-confidence fields: {low_confidence_fields}
        \"\"\"
        
        results = self.claude_service.extract_fields_json_mode(document_text, enhanced_prompt, schema_fields)
        
        print(f"Layer 2: Claude extracted {len(results)} fields")
        return results
    
    def _layer3_regex_critical(self, document_bytes: bytes, document_type: str, textract_results: Dict, claude_results: Dict) -> Dict[str, Any]:
        """Layer 3: Regex patterns for critical missing fields"""
        
        config = TAX_DOCUMENT_CONFIGS[document_type]
        required_fields = [field['name'] for field in config['fields'] if field.get('required', False)]
        
        # Find critical fields still missing
        all_extracted = set(textract_results.keys()) | set(claude_results.keys())
        missing_critical = [field for field in required_fields if field not in all_extracted]
        
        if not missing_critical:
            print("Layer 3: No critical fields missing, skipping regex")
            return {}
        
        print(f"Layer 3: Regex fallback for {len(missing_critical)} critical fields")
        
        document_text = self._extract_document_text(document_bytes)
        
        # Use tax-specific regex patterns
        results = {}
        for field in missing_critical:
            if field in config.get('regex_patterns', {}):
                pattern = config['regex_patterns'][field]
                match = re.search(pattern, document_text, re.IGNORECASE)
                if match:
                    results[field] = {
                        'value': match.group(1),
                        'confidence': 0.7,  # Lower confidence for regex
                        'source': 'regex'
                    }
        
        print(f"Layer 3: Regex extracted {len(results)} fields")
        return results
    
    def _orchestrate_tax_results(self, textract_results: Dict, claude_results: Dict, regex_results: Dict, document_type: str) -> Dict[str, Any]:
        """Orchestrate results with tax-specific logic"""
        
        final_results = {
            'DocumentType': document_type,
            'ExtractedData': {},
            'ExtractionMetadata': {
                'textract_fields': len(textract_results),
                'claude_fields': len(claude_results),
                'regex_fields': len(regex_results),
                'processing_layers': [],
                'processing_status': 'completed',
                'template_used': f"{document_type}_2024"
            },
            'QualityMetrics': {
                'overall_confidence': 0.0,
                'field_confidence_scores': {},
                'extraction_quality': 'good',
                'cost_optimization': {
                    'textract_primary': len(textract_results),
                    'claude_fallback': len(claude_results),
                    'regex_safety': len(regex_results)
                }
            }
        }
        
        # Merge results with priority: High-confidence Textract > Claude > Low-confidence Textract > Regex
        all_fields = set(textract_results.keys()) | set(claude_results.keys()) | set(regex_results.keys())
        confidence_scores = []
        
        for field in all_fields:
            if field in textract_results and textract_results[field]['confidence'] >= self.confidence_threshold:
                # High-confidence Textract wins
                result_data = textract_results[field]
                final_results['ExtractedData'][field] = result_data['value']
                final_results['QualityMetrics']['field_confidence_scores'][field] = result_data['confidence']
                final_results['ExtractedData'][f'{field}_source'] = 'textract_high'
                confidence_scores.append(result_data['confidence'])
                
            elif field in claude_results:
                # Claude fallback
                result_data = claude_results[field]
                final_results['ExtractedData'][field] = result_data['value']
                final_results['QualityMetrics']['field_confidence_scores'][field] = result_data['confidence']
                final_results['ExtractedData'][f'{field}_source'] = 'claude'
                confidence_scores.append(result_data['confidence'])
                
                # Cross-validation bonus
                if field in textract_results:
                    if self._values_agree(textract_results[field]['value'], result_data['value']):
                        final_results['QualityMetrics']['field_confidence_scores'][field] = min(0.95, result_data['confidence'] + 0.1)
                        final_results['ExtractedData'][f'{field}_cross_validated'] = True
                
            elif field in textract_results:
                # Low-confidence Textract
                result_data = textract_results[field]
                final_results['ExtractedData'][field] = result_data['value']
                final_results['QualityMetrics']['field_confidence_scores'][field] = result_data['confidence']
                final_results['ExtractedData'][f'{field}_source'] = 'textract_low'
                confidence_scores.append(result_data['confidence'])
                
            elif field in regex_results:
                # Regex safety net
                result_data = regex_results[field]
                final_results['ExtractedData'][field] = result_data['value']
                final_results['QualityMetrics']['field_confidence_scores'][field] = result_data['confidence']
                final_results['ExtractedData'][f'{field}_source'] = 'regex'
                confidence_scores.append(result_data['confidence'])
        
        # Calculate metrics
        if confidence_scores:
            overall_confidence = sum(confidence_scores) / len(confidence_scores)
            final_results['ExtractionMetadata']['overall_confidence'] = overall_confidence
            final_results['QualityMetrics']['overall_confidence'] = overall_confidence
            final_results['ExtractionMetadata']['needs_review'] = overall_confidence < 0.85
        
        # Track processing layers
        if textract_results:
            final_results['ExtractionMetadata']['processing_layers'].append('textract')
        if claude_results:
            final_results['ExtractionMetadata']['processing_layers'].append('claude')
        if regex_results:
            final_results['ExtractionMetadata']['processing_layers'].append('regex')
        
        return final_results
    
    def _apply_pii_masking(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply PII masking rules"""
        
        masked_data = data.copy()
        
        for field, value in data.items():
            if not isinstance(value, str):
                continue
                
            # SSN masking
            if 'ssn' in field.lower() and re.match(r'\\d{3}-\\d{2}-\\d{4}', value):
                masked_data[field] = f"***-**-{value[-4:]}"
                masked_data[f'{field}_masked'] = True
            
            # EIN masking
            elif 'ein' in field.lower() and re.match(r'\\d{2}-\\d{7}', value):
                masked_data[field] = f"**-*****{value[-2:]}"
                masked_data[f'{field}_masked'] = True
        
        return masked_data
    
    def _extract_header_text(self, document_bytes: bytes, max_chars: int = 2000) -> str:
        """Extract header text for form detection"""
        import boto3
        
        textract = boto3.client('textract')
        response = textract.detect_document_text(Document={'Bytes': document_bytes})
        
        text_lines = []
        char_count = 0
        
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE' and char_count < max_chars:
                line_text = block['Text']
                text_lines.append(line_text)
                char_count += len(line_text)
        
        return '\\n'.join(text_lines)
    
    def _extract_document_text(self, document_bytes: bytes) -> str:
        """Extract full document text"""
        import boto3
        
        textract = boto3.client('textract')
        response = textract.detect_document_text(Document={'Bytes': document_bytes})
        
        text_lines = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_lines.append(block['Text'])
        
        return '\\n'.join(text_lines)
    
    def _values_agree(self, val1: Any, val2: Any) -> bool:
        """Check if two values agree for cross-validation"""
        if val1 is None or val2 is None:
            return False
        
        # For numeric values
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            return abs(val1 - val2) / max(abs(val1), abs(val2), 1) < 0.05
        
        # For text values
        return str(val1).strip().lower() == str(val2).strip().lower()