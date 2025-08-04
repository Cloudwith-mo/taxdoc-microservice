"""
Multi-Form Document Extraction Service
Implements three-layer extraction: Textract Queries → Claude LLM → Regex fallback
Supports all tax forms, bank statements, pay stubs, receipts, and invoices
"""

import json
import re
import boto3
from typing import Dict, Any, Optional, List, Tuple
from config.document_config import DOCUMENT_CONFIGS

class MultiFormExtractor:
    def __init__(self):
        self.textract_client = boto3.client('textract', region_name='us-east-1')
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.claude_model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        self.titan_model_id = 'amazon.titan-text-premier-v1:0'
        self.preferred_model = 'claude'  # Switch to Claude as primary
        self.confidence_threshold = 0.85
        
    def extract_document_fields(self, document_bytes: bytes, document_type: str, s3_bucket: str = None, s3_key: str = None) -> Dict[str, Any]:
        """
        Main extraction method using three-layer approach
        """
        print(f"Starting multi-form extraction for document type: {document_type}")
        
        if document_type not in DOCUMENT_CONFIGS:
            return {"error": f"Unsupported document type: {document_type}"}
        
        config = DOCUMENT_CONFIGS[document_type]
        
        # Layer 1: Textract Queries
        textract_results = self._extract_with_textract_queries(document_bytes, config["queries"], s3_bucket, s3_key)
        
        # Layer 2: Claude LLM for low-confidence fields
        llm_results = self._extract_with_claude_llm(document_bytes, document_type, config["claude_prompt"], textract_results)
        
        # Layer 3: Regex fallback for missing fields
        regex_results = self._extract_with_regex(document_bytes, config.get("regex_patterns", {}), textract_results, llm_results)
        
        # Orchestrate and merge results
        final_results = self._orchestrate_results(textract_results, llm_results, regex_results, document_type)
        
        return final_results
    
    def _extract_with_textract_queries(self, document_bytes: bytes, queries: List[Dict], s3_bucket: str = None, s3_key: str = None) -> Dict[str, Any]:
        """
        Layer 1: Extract fields using Textract Queries
        """
        try:
            print(f"Running Textract queries: {len(queries)} queries")
            
            # Prepare queries for Textract
            query_config = {
                "Queries": [{"Text": q["Text"], "Alias": q["Alias"]} for q in queries]
            }
            
            # Call Textract with queries
            if s3_bucket and s3_key:
                response = self.textract_client.analyze_document(
                    Document={'S3Object': {'Bucket': s3_bucket, 'Name': s3_key}},
                    FeatureTypes=['QUERIES'],
                    QueriesConfig=query_config
                )
            else:
                response = self.textract_client.analyze_document(
                    Document={'Bytes': document_bytes},
                    FeatureTypes=['QUERIES'],
                    QueriesConfig=query_config
                )
            
            # Parse query results - simplified approach
            results = {}
            query_map = {q['Alias']: q['Text'] for q in queries}
            
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'QUERY_RESULT':
                    text = block.get('Text', '')
                    confidence = block.get('Confidence', 0) / 100.0
                    
                    # Match result to query by finding the query that produced this result
                    for alias, query_text in query_map.items():
                        if alias not in results and text:  # First available result gets assigned
                            results[alias] = {
                                'value': self._parse_field_value(text, alias),
                                'confidence': confidence,
                                'source': 'textract_query',
                                'raw_text': text
                            }
                            break
            
            print(f"Textract queries extracted {len(results)} fields")
            return results
            
        except Exception as e:
            print(f"Textract queries failed: {e}")
            return {}
    
    def _extract_with_claude_llm(self, document_bytes: bytes, document_type: str, prompt: str, textract_results: Dict) -> Dict[str, Any]:
        """
        Layer 2: Use Claude LLM for low-confidence or missing fields
        """
        try:
            # Identify fields that need LLM processing
            low_confidence_fields = []
            for field, data in textract_results.items():
                if data['confidence'] < self.confidence_threshold:
                    low_confidence_fields.append(field)
            
            if not low_confidence_fields:
                print("All Textract fields have high confidence, skipping LLM")
                return {}
            
            print(f"Using Claude LLM for {len(low_confidence_fields)} low-confidence fields")
            
            # Get document text for LLM
            document_text = self._extract_document_text(document_bytes)
            
            # Construct enhanced prompt
            enhanced_prompt = f"""
{prompt}

Document text:
{document_text[:4000]}

Focus on these fields that need verification: {', '.join(low_confidence_fields)}

Return only valid JSON with exact field names. Use null for missing values.
"""
            
            # Use Claude as primary model
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": enhanced_prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            model_used = 'claude'
            
            response_body = json.loads(response['body'].read())
            llm_output = response_body['content'][0]['text']
            
            # Parse JSON from LLM response
            json_start = llm_output.find('{')
            json_end = llm_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_output[json_start:json_end]
                llm_fields = json.loads(json_str)
                
                # Format results with metadata
                results = {}
                for field, value in llm_fields.items():
                    if value is not None and value != "":
                        results[field] = {
                            'value': self._parse_field_value(str(value), field),
                            'confidence': 0.85,  # Default LLM confidence
                            'source': 'claude_llm',
                            'raw_text': str(value)
                        }
                
                print(f"Claude LLM extracted {len(results)} fields")
                return results
            
        except Exception as e:
            print(f"Claude LLM extraction failed: {e}")
        
        return {}
    
    def _extract_with_regex(self, document_bytes: bytes, regex_patterns: Dict, textract_results: Dict, llm_results: Dict) -> Dict[str, Any]:
        """
        Layer 3: Regex fallback for still-missing fields
        """
        if not regex_patterns:
            return {}
        
        try:
            document_text = self._extract_document_text(document_bytes).lower()
            
            # Find fields still missing after Textract and LLM
            missing_fields = []
            for field in regex_patterns.keys():
                if (field not in textract_results or textract_results[field]['confidence'] < 0.5) and \
                   (field not in llm_results):
                    missing_fields.append(field)
            
            if not missing_fields:
                print("No fields need regex fallback")
                return {}
            
            print(f"Using regex fallback for {len(missing_fields)} missing fields")
            
            results = {}
            for field in missing_fields:
                pattern = regex_patterns[field]
                match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
                
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
                    results[field] = {
                        'value': self._parse_field_value(value, field),
                        'confidence': 0.5,  # Low confidence for regex
                        'source': 'regex_fallback',
                        'raw_text': value
                    }
            
            print(f"Regex fallback extracted {len(results)} fields")
            return results
            
        except Exception as e:
            print(f"Regex fallback failed: {e}")
            return {}
    
    def _orchestrate_results(self, textract_results: Dict, llm_results: Dict, regex_results: Dict, document_type: str) -> Dict[str, Any]:
        """
        Orchestrate and merge results from all three layers with confidence scoring
        """
        final_results = {
            'DocumentType': document_type,
            'ExtractionMetadata': {
                'textract_fields': len(textract_results),
                'llm_fields': len(llm_results),
                'regex_fields': len(regex_results),
                'total_fields': 0,
                'overall_confidence': 0.0,
                'needs_review': False
            }
        }
        
        all_fields = set(textract_results.keys()) | set(llm_results.keys()) | set(regex_results.keys())
        confidence_scores = []
        
        for field in all_fields:
            # Priority: Textract (high confidence) > LLM > Textract (low confidence) > Regex
            if field in textract_results and textract_results[field]['confidence'] >= self.confidence_threshold:
                # Use high-confidence Textract result
                final_results[field] = textract_results[field]['value']
                final_results[f'{field}_confidence'] = textract_results[field]['confidence']
                final_results[f'{field}_source'] = 'textract'
                confidence_scores.append(textract_results[field]['confidence'])
                
            elif field in llm_results:
                # Use LLM result
                final_results[field] = llm_results[field]['value']
                final_results[f'{field}_confidence'] = llm_results[field]['confidence']
                final_results[f'{field}_source'] = 'llm'
                confidence_scores.append(llm_results[field]['confidence'])
                
                # Cross-validate with Textract if available
                if field in textract_results:
                    textract_val = textract_results[field]['value']
                    llm_val = llm_results[field]['value']
                    
                    if self._values_agree(textract_val, llm_val):
                        final_results[f'{field}_confidence'] = min(0.95, llm_results[field]['confidence'] + 0.1)
                        final_results[f'{field}_cross_validated'] = True
                
            elif field in textract_results:
                # Use low-confidence Textract result
                final_results[field] = textract_results[field]['value']
                final_results[f'{field}_confidence'] = textract_results[field]['confidence']
                final_results[f'{field}_source'] = 'textract_low'
                confidence_scores.append(textract_results[field]['confidence'])
                
            elif field in regex_results:
                # Use regex fallback
                final_results[field] = regex_results[field]['value']
                final_results[f'{field}_confidence'] = regex_results[field]['confidence']
                final_results[f'{field}_source'] = 'regex'
                confidence_scores.append(regex_results[field]['confidence'])
        
        # Calculate overall metrics
        final_results['ExtractionMetadata']['total_fields'] = len(all_fields)
        if confidence_scores:
            final_results['ExtractionMetadata']['overall_confidence'] = sum(confidence_scores) / len(confidence_scores)
            final_results['ExtractionMetadata']['needs_review'] = final_results['ExtractionMetadata']['overall_confidence'] < 0.8
        
        print(f"Final extraction: {len(all_fields)} fields, {final_results['ExtractionMetadata']['overall_confidence']:.2f} confidence")
        return final_results
    
    def _extract_document_text(self, document_bytes: bytes) -> str:
        """Extract plain text from document for LLM processing"""
        try:
            response = self.textract_client.detect_document_text(
                Document={'Bytes': document_bytes}
            )
            
            text_lines = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
            
            return '\n'.join(text_lines)
            
        except Exception as e:
            print(f"Failed to extract document text: {e}")
            return ""
    
    def _parse_field_value(self, text: str, field_name: str) -> Any:
        """Parse field value based on field type"""
        if not text or text.lower() in ['null', 'none', 'n/a', '']:
            return None
        
        # Monetary fields
        if any(keyword in field_name.lower() for keyword in ['amount', 'wages', 'tax', 'income', 'balance', 'pay']):
            return self._parse_monetary_value(text)
        
        # SSN fields
        if 'ssn' in field_name.lower():
            ssn_match = re.search(r'(\d{3}-\d{2}-\d{4})', text)
            return ssn_match.group(1) if ssn_match else text.strip()
        
        # EIN fields
        if 'ein' in field_name.lower() or 'tin' in field_name.lower():
            ein_match = re.search(r'(\d{2}-\d{7})', text)
            return ein_match.group(1) if ein_match else text.strip()
        
        # Year fields
        if 'year' in field_name.lower():
            year_match = re.search(r'(20\d{2})', text)
            return int(year_match.group(1)) if year_match else text.strip()
        
        # Default: return cleaned text
        return text.strip()
    
    def _parse_monetary_value(self, text: str) -> Optional[float]:
        """Parse monetary value from text"""
        if not text:
            return None
        
        # Remove currency symbols and clean
        cleaned = re.sub(r'[^\d.,]', '', text)
        cleaned = re.sub(r',', '', cleaned)
        
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def _values_agree(self, val1: Any, val2: Any) -> bool:
        """Check if two values agree (for cross-validation)"""
        if val1 is None or val2 is None:
            return False
        
        # For numeric values
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            return abs(val1 - val2) / max(abs(val1), abs(val2), 1) < 0.05  # 5% tolerance
        
        # For text values
        return str(val1).strip().lower() == str(val2).strip().lower()
    
    def get_supported_document_types(self) -> List[str]:
        """Return list of supported document types"""
        return list(DOCUMENT_CONFIGS.keys())