"""
Any-Doc Processor - Main Pipeline
Orchestrates the complete document processing pipeline from file detection to extraction
"""

import json
import boto3
from typing import Dict, Any, Optional, List
from .file_type_detector import FileTypeDetector
from .document_structure_extractor import DocumentStructureExtractor
from .template_matcher import TemplateMatcher
from .multi_form_extractor import MultiFormExtractor
from .comprehend_insights_service import ComprehendInsightsService

class AnyDocProcessor:
    def __init__(self):
        self.file_detector = FileTypeDetector()
        self.structure_extractor = DocumentStructureExtractor()
        self.template_matcher = TemplateMatcher()
        self.form_extractor = MultiFormExtractor()
        self.insights_service = ComprehendInsightsService()
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.claude_model_id = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
    
    def process_document(self, file_bytes: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Main processing pipeline for any document type
        Returns comprehensive extraction results with metadata
        """
        try:
            # Stage 1: File Type Detection
            print("Stage 1: Detecting file type...")
            file_info = self.file_detector.detect_file_type(file_bytes, filename)
            
            if not file_info['is_supported']:
                return self._create_error_result(
                    f"Unsupported file type: {file_info['mime_type']}",
                    file_info
                )
            
            # Stage 2: Document Structure Extraction
            print("Stage 2: Extracting document structure...")
            structure = self.structure_extractor.extract_structure(file_bytes, file_info)
            
            if 'error' in structure:
                return self._create_error_result(
                    f"Structure extraction failed: {structure['error']}",
                    file_info
                )
            
            # Stage 3: Template Matching
            print("Stage 3: Matching document template...")
            template_match = self.template_matcher.match_template(structure['raw_text'])
            
            # Stage 4: Extraction Strategy Selection
            extraction_strategy = self.template_matcher.get_extraction_strategy(template_match)
            print(f"Stage 4: Using extraction strategy: {extraction_strategy}")
            
            # Stage 5: Data Extraction
            if extraction_strategy == 'deterministic':
                extraction_results = self._deterministic_extraction(
                    file_bytes, template_match, structure
                )
            elif extraction_strategy == 'llm_primary':
                extraction_results = self._llm_primary_extraction(
                    file_bytes, template_match, structure
                )
            else:  # llm_only
                extraction_results = self._llm_only_extraction(
                    structure, template_match
                )
            
            # Stage 6: AI Insights Generation
            print("Stage 6: Generating AI insights...")
            ai_insights = self.insights_service.generate_document_insights(
                structure['raw_text'],
                template_match['template_name'],
                extraction_results.get('ExtractedData', extraction_results)
            )
            
            # Stage 7: Result Compilation
            return self._compile_final_results(
                file_info, structure, template_match, extraction_results, extraction_strategy, ai_insights
            )
            
        except Exception as e:
            print(f"Document processing failed: {e}")
            return self._create_error_result(f"Processing failed: {str(e)}")
    
    def _deterministic_extraction(self, file_bytes: bytes, template_match: Dict, structure: Dict) -> Dict[str, Any]:
        """Use the existing multi-form extractor for known document types"""
        try:
            return self.form_extractor.extract_document_fields(
                file_bytes, 
                template_match['template_name']
            )
        except Exception as e:
            print(f"Deterministic extraction failed, falling back to LLM: {e}")
            return self._llm_primary_extraction(file_bytes, template_match, structure)
    
    def _llm_primary_extraction(self, file_bytes: bytes, template_match: Dict, structure: Dict) -> Dict[str, Any]:
        """Use LLM as primary with template guidance"""
        relevant_text = self.structure_extractor.get_relevant_text_regions(structure, max_tokens=3000)
        
        # Create context-aware prompt
        if template_match['template_name'] != 'Unknown':
            prompt = f"""
You are processing a document that appears to be a {template_match['template_name']}.

Extract key information from this document in JSON format. Focus on:
- Names, dates, amounts, and identification numbers
- Key business information (addresses, phone numbers)
- Important financial data
- Document-specific fields relevant to {template_match['template_name']}

Document text:
{relevant_text}

Return only valid JSON with descriptive field names. Use null for missing values.
"""
        else:
            prompt = f"""
Extract key information from this document in JSON format. Focus on:
- Names, dates, amounts, and identification numbers
- Key business information (addresses, phone numbers)
- Important financial or business data
- Any structured information present

Document text:
{relevant_text}

Return only valid JSON with descriptive field names. Use null for missing values.
"""
        
        return self._call_claude_extraction(prompt, template_match['template_name'])
    
    def _llm_only_extraction(self, structure: Dict, template_match: Dict) -> Dict[str, Any]:
        """Use LLM for completely unknown document types"""
        relevant_text = self.structure_extractor.get_relevant_text_regions(structure, max_tokens=3500)
        
        prompt = f"""
Analyze this document and extract any structured information you can find.

Create a JSON response with:
1. "document_type": Your best guess at what type of document this is
2. "key_information": Object containing any structured data you can extract
3. "summary": Brief description of the document's purpose and content

Document text:
{relevant_text}

Return only valid JSON.
"""
        
        return self._call_claude_extraction(prompt, "Unknown Document")
    
    def _call_claude_extraction(self, prompt: str, doc_type: str) -> Dict[str, Any]:
        """Call Claude for extraction with error handling"""
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            llm_output = response_body['content'][0]['text']
            
            # Parse JSON from response
            json_start = llm_output.find('{')
            json_end = llm_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_output[json_start:json_end]
                extracted_data = json.loads(json_str)
                
                return {
                    'DocumentType': doc_type,
                    'ExtractedData': extracted_data,
                    'ExtractionMetadata': {
                        'method': 'claude_llm',
                        'confidence': 0.85,
                        'needs_review': False
                    }
                }
            else:
                raise ValueError("No valid JSON found in LLM response")
                
        except Exception as e:
            print(f"Claude extraction failed: {e}")
            return {
                'DocumentType': doc_type,
                'ExtractedData': {},
                'ExtractionMetadata': {
                    'method': 'failed',
                    'confidence': 0.0,
                    'needs_review': True,
                    'error': str(e)
                }
            }
    
    def _compile_final_results(self, file_info: Dict, structure: Dict, template_match: Dict, 
                             extraction_results: Dict, extraction_strategy: str, ai_insights: Dict = None) -> Dict[str, Any]:
        """Compile comprehensive final results"""
        return {
            'ProcessingMetadata': {
                'file_type': file_info['mime_type'],
                'file_category': file_info['category'],
                'processing_route': file_info['processing_route'],
                'template_match': template_match['template_name'],
                'template_confidence': template_match['confidence'],
                'extraction_strategy': extraction_strategy,
                'structure_confidence': structure['overall_confidence'],
                'total_pages': structure['layout_info']['pages'],
                'has_tables': structure['layout_info']['has_tables'],
                'has_forms': structure['layout_info']['has_forms']
            },
            'DocumentType': extraction_results.get('DocumentType', template_match['template_name']),
            'ExtractedData': extraction_results.get('ExtractedData', extraction_results),
            'ExtractionMetadata': extraction_results.get('ExtractionMetadata', {}),
            'AIInsights': ai_insights or {},
            'QualityMetrics': {
                'overall_confidence': self._calculate_overall_confidence(
                    file_info, structure, template_match, extraction_results
                ),
                'needs_human_review': self._needs_human_review(
                    file_info, structure, template_match, extraction_results
                ),
                'processing_time_estimate': self._estimate_processing_time(file_info, structure)
            }
        }
    
    def _calculate_overall_confidence(self, file_info: Dict, structure: Dict, 
                                    template_match: Dict, extraction_results: Dict) -> float:
        """Calculate overall confidence score"""
        weights = {
            'file_detection': 0.1,
            'structure_extraction': 0.2,
            'template_matching': 0.3,
            'data_extraction': 0.4
        }
        
        scores = {
            'file_detection': file_info['confidence'],
            'structure_extraction': structure['overall_confidence'],
            'template_matching': template_match['confidence'],
            'data_extraction': extraction_results.get('ExtractionMetadata', {}).get('confidence', 0.5)
        }
        
        return sum(weights[k] * scores[k] for k in weights.keys())
    
    def _needs_human_review(self, file_info: Dict, structure: Dict, 
                          template_match: Dict, extraction_results: Dict) -> bool:
        """Determine if human review is needed"""
        overall_confidence = self._calculate_overall_confidence(
            file_info, structure, template_match, extraction_results
        )
        
        return (
            overall_confidence < 0.7 or
            template_match['confidence'] < 0.3 or
            extraction_results.get('ExtractionMetadata', {}).get('needs_review', False)
        )
    
    def _estimate_processing_time(self, file_info: Dict, structure: Dict) -> str:
        """Estimate processing time based on document complexity"""
        if structure['layout_info']['pages'] > 10:
            return "3-5 minutes"
        elif structure['layout_info']['has_tables'] or structure['layout_info']['has_forms']:
            return "1-2 minutes"
        else:
            return "30-60 seconds"
    
    def _create_error_result(self, error_message: str, file_info: Dict = None) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'ProcessingMetadata': {
                'file_type': file_info['mime_type'] if file_info else 'unknown',
                'processing_status': 'failed',
                'error_message': error_message
            },
            'DocumentType': 'Error',
            'ExtractedData': {},
            'ExtractionMetadata': {
                'method': 'error',
                'confidence': 0.0,
                'needs_review': True
            },
            'QualityMetrics': {
                'overall_confidence': 0.0,
                'needs_human_review': True,
                'processing_time_estimate': 'N/A'
            }
        }
    
    def get_supported_file_types(self) -> List[str]:
        """Return list of supported file types"""
        return list(self.file_detector.supported_types.keys())
    
    def process_batch(self, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple documents in batch"""
        results = []
        for file_info in files:
            try:
                result = self.process_document(
                    file_info['bytes'], 
                    file_info.get('filename')
                )
                result['batch_id'] = file_info.get('id')
                results.append(result)
            except Exception as e:
                results.append(self._create_error_result(
                    f"Batch processing failed: {str(e)}"
                ))
        return results