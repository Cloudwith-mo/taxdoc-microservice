from typing import Dict, Any, List
from .enhanced_textract_service import EnhancedTextractService
from .bedrock_claude_service import BedrockClaudeService
from .regex_fallback_service import RegexFallbackService
from config.document_config import DOCUMENT_CONFIGS

class ThreeLayerOrchestrator:
    """Orchestrates the three-layer AI extraction pipeline"""
    
    def __init__(self):
        self.textract_service = EnhancedTextractService()
        self.claude_service = BedrockClaudeService()
        self.regex_service = RegexFallbackService()
        self.confidence_threshold = 0.85
    
    def extract_document_fields(self, document_bytes: bytes, document_type: str) -> Dict[str, Any]:
        """Main extraction method using three-layer approach"""
        
        if document_type not in DOCUMENT_CONFIGS:
            # Return basic extraction for unsupported types
            return {
                'DocumentType': document_type,
                'error': f'Unsupported document type: {document_type}',
                'ExtractionMetadata': {
                    'textract_fields': 0,
                    'llm_fields': 0,
                    'regex_fields': 0,
                    'processing_layers': [],
                    'total_fields': 0,
                    'overall_confidence': 0.0,
                    'needs_review': True
                }
            }
        
        config = DOCUMENT_CONFIGS[document_type]
        
        # Layer 1: Textract Queries
        textract_results = self._layer1_textract_queries(document_bytes, config["queries"])
        
        # Layer 2: Claude LLM for low-confidence fields
        llm_results = self._layer2_claude_llm(document_bytes, document_type, textract_results)
        
        # Layer 3: Regex fallback for missing fields
        regex_results = self._layer3_regex_fallback(document_bytes, textract_results, llm_results)
        
        # Orchestrate final results
        return self._orchestrate_results(textract_results, llm_results, regex_results, document_type)
    
    def _layer1_textract_queries(self, document_bytes: bytes, queries: List[Dict]) -> Dict[str, Any]:
        """Layer 1: Textract Queries extraction"""
        
        print(f"Layer 1: Running {len(queries)} Textract queries")
        
        response = self.textract_service.analyze_with_queries(document_bytes, queries)
        results = self.textract_service.extract_query_answers(response)
        
        print(f"Layer 1: Extracted {len(results)} fields")
        return results
    
    def _layer2_claude_llm(self, document_bytes: bytes, document_type: str, textract_results: Dict) -> Dict[str, Any]:
        """Layer 2: Claude LLM for low-confidence fields"""
        
        # Identify low-confidence fields
        low_confidence_fields = []
        for field, data in textract_results.items():
            if data['confidence'] < self.confidence_threshold:
                low_confidence_fields.append(field)
        
        if not low_confidence_fields:
            print("Layer 2: All Textract fields have high confidence, skipping LLM")
            return {}
        
        print(f"Layer 2: Processing {len(low_confidence_fields)} low-confidence fields with Claude")
        
        # Extract document text
        document_text = self._extract_document_text(document_bytes)
        
        # Use Claude for low-confidence fields
        results = self.claude_service.extract_fields(document_text, document_type, low_confidence_fields)
        
        print(f"Layer 2: Claude extracted {len(results)} fields")
        return results
    
    def _layer3_regex_fallback(self, document_bytes: bytes, textract_results: Dict, llm_results: Dict) -> Dict[str, Any]:
        """Layer 3: Regex fallback for still-missing fields"""
        
        # Find fields still missing
        all_extracted_fields = set(textract_results.keys()) | set(llm_results.keys())
        
        # For now, assume we want common critical fields
        critical_fields = ['ssn', 'ein', 'total_amount', 'date', 'phone']
        missing_fields = [field for field in critical_fields if field not in all_extracted_fields]
        
        if not missing_fields:
            print("Layer 3: No critical fields missing, skipping regex")
            return {}
        
        print(f"Layer 3: Using regex fallback for {len(missing_fields)} missing fields")
        
        # Extract document text
        document_text = self._extract_document_text(document_bytes)
        
        # Use regex fallback
        results = self.regex_service.extract_missing_fields(document_text, missing_fields)
        
        print(f"Layer 3: Regex extracted {len(results)} fields")
        return results
    
    def _orchestrate_results(self, textract_results: Dict, llm_results: Dict, regex_results: Dict, document_type: str) -> Dict[str, Any]:
        """Orchestrate and merge results from all three layers"""
        
        final_results = {
            'DocumentType': document_type,
            'ExtractionMetadata': {
                'textract_fields': len(textract_results),
                'llm_fields': len(llm_results),
                'regex_fields': len(regex_results),
                'processing_layers': []
            }
        }
        
        all_fields = set(textract_results.keys()) | set(llm_results.keys()) | set(regex_results.keys())
        confidence_scores = []
        
        for field in all_fields:
            # Priority: High-confidence Textract > LLM > Low-confidence Textract > Regex
            if field in textract_results and textract_results[field]['confidence'] >= self.confidence_threshold:
                # Use high-confidence Textract
                result_data = textract_results[field]
                final_results[field] = result_data['value']
                final_results[f'{field}_confidence'] = result_data['confidence']
                final_results[f'{field}_source'] = 'textract'
                confidence_scores.append(result_data['confidence'])
                
            elif field in llm_results:
                # Use LLM result
                result_data = llm_results[field]
                final_results[field] = result_data['value']
                final_results[f'{field}_confidence'] = result_data['confidence']
                final_results[f'{field}_source'] = 'claude'
                confidence_scores.append(result_data['confidence'])
                
                # Cross-validate with Textract if available
                if field in textract_results:
                    if self._values_agree(textract_results[field]['value'], result_data['value']):
                        final_results[f'{field}_confidence'] = min(0.95, result_data['confidence'] + 0.1)
                        final_results[f'{field}_cross_validated'] = True
                
            elif field in textract_results:
                # Use low-confidence Textract
                result_data = textract_results[field]
                final_results[field] = result_data['value']
                final_results[f'{field}_confidence'] = result_data['confidence']
                final_results[f'{field}_source'] = 'textract_low'
                confidence_scores.append(result_data['confidence'])
                
            elif field in regex_results:
                # Use regex fallback
                result_data = regex_results[field]
                final_results[field] = result_data['value']
                final_results[f'{field}_confidence'] = result_data['confidence']
                final_results[f'{field}_source'] = 'regex'
                confidence_scores.append(result_data['confidence'])
        
        # Calculate overall metrics
        final_results['ExtractionMetadata']['total_fields'] = len(all_fields)
        if confidence_scores:
            final_results['ExtractionMetadata']['overall_confidence'] = sum(confidence_scores) / len(confidence_scores)
            final_results['ExtractionMetadata']['needs_review'] = final_results['ExtractionMetadata']['overall_confidence'] < 0.8
        
        # Track which layers were used
        if textract_results:
            final_results['ExtractionMetadata']['processing_layers'].append('textract')
        if llm_results:
            final_results['ExtractionMetadata']['processing_layers'].append('claude')
        if regex_results:
            final_results['ExtractionMetadata']['processing_layers'].append('regex')
        
        print(f"Final extraction: {len(all_fields)} fields, {final_results['ExtractionMetadata']['overall_confidence']:.2f} confidence")
        return final_results
    
    def _extract_document_text(self, document_bytes: bytes) -> str:
        """Extract plain text from document"""
        import boto3
        
        textract = boto3.client('textract')
        response = textract.detect_document_text(Document={'Bytes': document_bytes})
        
        text_lines = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)
    
    def _values_agree(self, val1: Any, val2: Any) -> bool:
        """Check if two values agree for cross-validation"""
        if val1 is None or val2 is None:
            return False
        
        # For numeric values
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            return abs(val1 - val2) / max(abs(val1), abs(val2), 1) < 0.05
        
        # For text values
        return str(val1).strip().lower() == str(val2).strip().lower()