"""
Multi-Form Document Extraction Service
Implements 3-layer extraction: Textract Queries -> Claude LLM -> Regex
"""

import json
import re
import boto3
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal
import os

class MultiFormExtractor:
    def __init__(self):
        self.textract_client = boto3.client('textract')
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.claude_model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        self.confidence_threshold = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.8'))
        
        # Load document configurations
        from config.document_config import DOCUMENT_CONFIGS, CLASSIFICATION_KEYWORDS
        self.document_configs = DOCUMENT_CONFIGS
        self.classification_keywords = CLASSIFICATION_KEYWORDS
    
    def extract_document_fields(self, textract_response: Dict[str, Any], document_type: str, 
                               document_bytes: bytes = None, s3_bucket: str = None, s3_key: str = None) -> Dict[str, Any]:
        """
        Main extraction method using 3-layer approach:
        1. Textract Queries (Layer 1)
        2. Claude LLM fallback (Layer 2) 
        3. Regex patterns (Layer 3)
        """
        print(f"Starting multi-form extraction for document type: {document_type}")
        
        if document_type not in self.document_configs:
            print(f"No configuration found for document type: {document_type}")
            return self._extract_generic_fields(textract_response)
        
        config = self.document_configs[document_type]
        final_fields = {}
        extraction_metadata = {
            'document_type': document_type,
            'layers_used': [],
            'field_sources': {},
            'confidence_scores': {},
            'needs_review': False
        }
        
        # Layer 1: Textract Queries
        print("Layer 1: Running Textract Queries...")
        textract_fields, textract_confidences = self._extract_with_textract_queries(
            config['queries'], s3_bucket, s3_key, textract_response
        )
        
        if textract_fields:
            extraction_metadata['layers_used'].append('textract_queries')
            for field, value in textract_fields.items():
                final_fields[field] = value
                extraction_metadata['field_sources'][field] = 'textract'
                extraction_metadata['confidence_scores'][field] = textract_confidences.get(field, 0.0)
        
        # Identify low-confidence fields for Layer 2
        low_confidence_fields = [
            field for field, confidence in textract_confidences.items() 
            if confidence < self.confidence_threshold
        ]
        
        missing_fields = [
            query['Alias'] for query in config['queries'] 
            if query['Alias'] not in final_fields
        ]
        
        fields_for_llm = list(set(low_confidence_fields + missing_fields))
        
        # Layer 2: Claude LLM for low-confidence/missing fields
        if fields_for_llm:
            print(f"Layer 2: Running Claude LLM for {len(fields_for_llm)} fields...")
            document_text = self._get_full_text(textract_response)
            llm_fields = self._extract_with_claude(document_text, config['claude_prompt'], document_type)
            
            if llm_fields:
                extraction_metadata['layers_used'].append('claude_llm')
                for field in fields_for_llm:
                    if field in llm_fields and llm_fields[field]:
                        # Cross-validate with Textract if both have values
                        if field in final_fields and final_fields[field]:
                            if self._values_match(final_fields[field], llm_fields[field]):
                                extraction_metadata['confidence_scores'][field] = min(
                                    extraction_metadata['confidence_scores'][field] + 0.2, 1.0
                                )
                            else:
                                extraction_metadata['needs_review'] = True
                                extraction_metadata[f'{field}_conflict'] = {
                                    'textract': final_fields[field],
                                    'claude': llm_fields[field]
                                }
                        
                        final_fields[field] = llm_fields[field]
                        extraction_metadata['field_sources'][field] = 'claude'
                        if field not in extraction_metadata['confidence_scores']:
                            extraction_metadata['confidence_scores'][field] = 0.85  # Default LLM confidence
        
        # Layer 3: Regex fallback for still missing fields
        still_missing = [
            query['Alias'] for query in config['queries'] 
            if query['Alias'] not in final_fields or not final_fields[query['Alias']]
        ]
        
        if still_missing and 'regex_patterns' in config:
            print(f"Layer 3: Running regex patterns for {len(still_missing)} fields...")
            document_text = self._get_full_text(textract_response)
            regex_fields = self._extract_with_regex(document_text, config['regex_patterns'], still_missing)
            
            if regex_fields:
                extraction_metadata['layers_used'].append('regex')
                for field, value in regex_fields.items():
                    final_fields[field] = value
                    extraction_metadata['field_sources'][field] = 'regex'
                    extraction_metadata['confidence_scores'][field] = 0.5  # Low confidence for regex
                    extraction_metadata['needs_review'] = True
        
        # Calculate overall confidence and completeness
        expected_fields = [query['Alias'] for query in config['queries']]
        found_fields = sum(1 for field in expected_fields if field in final_fields and final_fields[field])
        completeness = found_fields / len(expected_fields) if expected_fields else 0
        
        avg_confidence = sum(extraction_metadata['confidence_scores'].values()) / len(extraction_metadata['confidence_scores']) if extraction_metadata['confidence_scores'] else 0
        
        extraction_metadata.update({
            'completeness_score': completeness,
            'average_confidence': avg_confidence,
            'total_fields_extracted': len(final_fields),
            'expected_fields': len(expected_fields)
        })
        
        # Add metadata to final result
        final_fields['_extraction_metadata'] = extraction_metadata
        
        print(f"Extraction completed: {len(final_fields)} fields, {completeness:.1%} complete, {avg_confidence:.2f} avg confidence")
        return final_fields
    
    def _extract_with_textract_queries(self, queries: List[Dict], s3_bucket: str, s3_key: str, 
                                     fallback_response: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """Extract fields using Textract Queries API"""
        if not s3_bucket or not s3_key:
            print("No S3 location provided, skipping Textract Queries")
            return {}, {}
        
        try:
            # Prepare queries for Textract
            textract_queries = [{"Text": q["Text"], "Alias": q["Alias"]} for q in queries]
            
            response = self.textract_client.analyze_document(
                Document={'S3Object': {'Bucket': s3_bucket, 'Name': s3_key}},
                FeatureTypes=['QUERIES'],
                QueriesConfig={'Queries': textract_queries}
            )
            
            # Parse query results
            fields = {}
            confidences = {}
            
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'QUERY_RESULT':
                    alias = block.get('Query', {}).get('Alias', '')
                    text = block.get('Text', '')
                    confidence = block.get('Confidence', 0.0) / 100.0
                    
                    if alias and text:
                        # Convert numeric fields
                        if self._is_numeric_field(alias):
                            numeric_value = self._extract_numeric_value(text)
                            if numeric_value is not None:
                                fields[alias] = numeric_value
                            else:
                                fields[alias] = text
                        else:
                            fields[alias] = text
                        
                        confidences[alias] = confidence
            
            print(f"Textract Queries extracted {len(fields)} fields")
            return fields, confidences
            
        except Exception as e:
            print(f"Textract Queries failed: {e}")
            return {}, {}
    
    def _extract_with_claude(self, document_text: str, prompt_template: str, document_type: str) -> Dict[str, Any]:
        """Extract fields using Claude LLM"""
        try:
            # Truncate text if too long
            max_chars = 4000
            if len(document_text) > max_chars:
                document_text = document_text[:max_chars] + "..."
            
            # Construct full prompt
            full_prompt = f"{prompt_template}\n\nDocument text:\n{document_text}\n\nReturn only valid JSON:"
            
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            claude_output = response_body['content'][0]['text']
            
            # Parse JSON from Claude response
            json_start = claude_output.find('{')
            json_end = claude_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = claude_output[json_start:json_end]
                claude_fields = json.loads(json_str)
                
                # Clean and validate fields
                cleaned_fields = {}
                for key, value in claude_fields.items():
                    if value and str(value).strip() and str(value).lower() not in ['null', 'none', 'n/a']:
                        if self._is_numeric_field(key):
                            numeric_value = self._extract_numeric_value(str(value))
                            if numeric_value is not None:
                                cleaned_fields[key] = numeric_value
                        else:
                            cleaned_fields[key] = str(value).strip()
                
                print(f"Claude extracted {len(cleaned_fields)} fields")
                return cleaned_fields
            else:
                print("No valid JSON found in Claude response")
                return {}
                
        except Exception as e:
            print(f"Claude extraction failed: {e}")
            return {}
    
    def _extract_with_regex(self, document_text: str, regex_patterns: Dict[str, str], 
                           target_fields: List[str]) -> Dict[str, Any]:
        """Extract fields using regex patterns"""
        fields = {}
        
        for field in target_fields:
            if field in regex_patterns:
                pattern = regex_patterns[field]
                match = re.search(pattern, document_text, re.IGNORECASE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    if self._is_numeric_field(field):
                        numeric_value = self._extract_numeric_value(value)
                        if numeric_value is not None:
                            fields[field] = numeric_value
                    else:
                        fields[field] = value
        
        print(f"Regex extracted {len(fields)} fields")
        return fields
    
    def _extract_generic_fields(self, textract_response: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback extraction for unknown document types"""
        text = self._get_full_text(textract_response)
        
        return {
            'document_text': text[:1000] + "..." if len(text) > 1000 else text,
            'dates_found': self._extract_dates(text),
            'amounts_found': self._extract_amounts(text),
            'phone_numbers': self._extract_phone_numbers(text),
            '_extraction_metadata': {
                'document_type': 'unknown',
                'layers_used': ['generic'],
                'needs_review': True
            }
        }
    
    def _get_full_text(self, response: Dict[str, Any]) -> str:
        """Extract all text from Textract response"""
        text_lines = []
        
        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)
    
    def _is_numeric_field(self, field_name: str) -> bool:
        """Check if field should contain numeric value"""
        numeric_indicators = ['box', 'wage', 'tax', 'amount', 'total', 'balance', 'compensation']
        return any(indicator in field_name.lower() for indicator in numeric_indicators)
    
    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text"""
        if not text:
            return None
        
        # Remove currency symbols and clean
        cleaned = re.sub(r'[^\d.]', '', str(text))
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    
    def _values_match(self, val1: Any, val2: Any, tolerance: float = 0.05) -> bool:
        """Check if two values match (with tolerance for numeric values)"""
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            if max(val1, val2) == 0:
                return val1 == val2
            return abs(val1 - val2) / max(val1, val2) <= tolerance
        
        return str(val1).strip().lower() == str(val2).strip().lower()
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract date patterns"""
        patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\w+ \d{1,2}, \d{4}'
        ]
        
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text))
        
        return list(set(dates))
    
    def _extract_amounts(self, text: str) -> List[float]:
        """Extract monetary amounts"""
        amounts = re.findall(r'\$[\d,]+\.?\d*', text)
        return [self._extract_numeric_value(amount) for amount in amounts if self._extract_numeric_value(amount)]
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """Extract phone numbers"""
        pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        return re.findall(pattern, text)