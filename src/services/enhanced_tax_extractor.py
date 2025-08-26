"""
Enhanced Tax Extractor with Three-Layer Pipeline
Layer 1: Textract Queries (high precision)
Layer 2: Bedrock Claude (intelligent fallback)  
Layer 3: Regex patterns (safety net)
"""
import json
import boto3
import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger()

class EnhancedTaxExtractor:
    """Three-layer extraction pipeline for comprehensive tax document processing"""
    
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.textract_client = boto3.client('textract')
        self.model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        
        # W-2 field definitions with all boxes
        self.w2_fields = {
            "employee_ssn": "Employee's Social Security Number (Box a)",
            "employer_ein": "Employer identification number EIN (Box b)", 
            "control_number": "Control number (Box d)",
            "employee_first_name": "Employee's first name (Box e)",
            "employee_last_name": "Employee's last name (Box f)",
            "employee_address": "Employee's address and ZIP code (Box f)",
            "employer_name": "Employer's name (Box c)",
            "employer_address": "Employer's address (Box c)",
            "wages_income": "Wages, tips, other compensation (Box 1)",
            "federal_withheld": "Federal income tax withheld (Box 2)",
            "social_security_wages": "Social Security wages (Box 3)",
            "social_security_tax": "Social Security tax withheld (Box 4)",
            "medicare_wages": "Medicare wages and tips (Box 5)",
            "medicare_tax": "Medicare tax withheld (Box 6)",
            "social_security_tips": "Social Security tips (Box 7)",
            "allocated_tips": "Allocated tips (Box 8)",
            "dependent_care_benefits": "Dependent care benefits (Box 10)",
            "nonqualified_plans": "Nonqualified plans (Box 11)",
            "box12_codes": "Box 12 codes and amounts",
            "statutory_employee": "Statutory employee checkbox (Box 13)",
            "retirement_plan": "Retirement plan checkbox (Box 13)",
            "third_party_sick_pay": "Third-party sick pay checkbox (Box 13)",
            "other_deductions": "Other deductions (Box 14)",
            "state": "State (Box 15)",
            "state_wages": "State wages, tips, etc. (Box 16)",
            "state_income_tax": "State income tax (Box 17)",
            "local_wages": "Local wages, tips, etc. (Box 18)",
            "local_income_tax": "Local income tax (Box 19)",
            "locality_name": "Locality name (Box 20)"
        }
    
    def extract_with_three_layers(self, textract_response: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Execute three-layer extraction pipeline"""
        
        logger.info(f"Starting three-layer extraction for {doc_type}")
        
        layers_used = []
        confidence_scores = {}
        final_data = {}
        
        # For W-2 documents, prioritize Claude extraction for comprehensive fields
        if doc_type == "W-2":
            # Layer 2: Bedrock Claude (PRIMARY for comprehensive extraction)
            try:
                layer2_data = self._layer2_bedrock_claude(textract_response, doc_type, [])
                if layer2_data:
                    layers_used.append("bedrock_claude")
                    final_data.update(layer2_data)
                    logger.info(f"Layer 2 (Claude) extracted {len(layer2_data)} fields: {list(layer2_data.keys())}")
                else:
                    logger.warning("Layer 2 (Claude) returned no data")
            except Exception as e:
                logger.error(f"Layer 2 (Claude) failed: {e}")
            
            # Layer 1: Textract Queries (supplement Claude results)
            try:
                layer1_data = self._layer1_textract_queries(textract_response, doc_type)
                if layer1_data:
                    layers_used.append("textract_queries")
                    # Only add fields not already extracted by Claude
                    for key, value in layer1_data.items():
                        if key not in final_data or final_data[key] is None:
                            final_data[key] = value
                    logger.info(f"Layer 1 supplemented with {len(layer1_data)} fields")
            except Exception as e:
                logger.warning(f"Layer 1 failed: {e}")
        else:
            # For non-W-2 documents, use original order
            # Layer 1: Textract Queries
            try:
                layer1_data = self._layer1_textract_queries(textract_response, doc_type)
                layers_used.append("textract_queries")
                final_data.update(layer1_data)
                logger.info(f"Layer 1 extracted {len(layer1_data)} fields")
            except Exception as e:
                logger.warning(f"Layer 1 failed: {e}")
            
            # Layer 2: Bedrock Claude
            try:
                layer2_data = self._layer2_bedrock_claude(textract_response, doc_type, [])
                if layer2_data:
                    layers_used.append("bedrock_claude")
                    final_data.update(layer2_data)
                    logger.info(f"Layer 2 extracted {len(layer2_data)} fields")
            except Exception as e:
                logger.warning(f"Layer 2 failed: {e}")
        
        # Layer 3: Regex patterns (safety net for critical fields)
        critical_missing = self._get_critical_missing_fields(final_data, doc_type)
        if critical_missing:
            try:
                layer3_data = self._layer3_regex_patterns(textract_response, doc_type, critical_missing)
                if layer3_data:
                    layers_used.append("regex_patterns")
                    final_data.update(layer3_data)
                    logger.info(f"Layer 3 filled {len(layer3_data)} critical fields")
            except Exception as e:
                logger.warning(f"Layer 3 failed: {e}")
        
        # Post-process and validate
        processed_data = self._post_process_data(final_data, doc_type)
        
        # Add metadata
        processed_data.update({
            'layers_used': layers_used,
            'confidence_scores': confidence_scores,
            'extraction_method': 'three_layer_pipeline',
            'total_fields_extracted': len([v for v in processed_data.values() if v is not None and v != ''])
        })
        
        return processed_data
    
    def _layer1_textract_queries(self, textract_response: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Layer 1: Use Textract natural language queries for high-precision extraction"""
        
        if doc_type != "W-2":
            return {}
        
        # Extract text for analysis
        text_content = self._extract_text_from_textract(textract_response)
        
        # Parse key fields using text analysis
        result = {}
        
        # Extract SSN
        ssn_match = re.search(r'\b\d{3}-?\d{2}-?\d{4}\b', text_content)
        if ssn_match:
            result['a'] = ssn_match.group()
        
        # Extract EIN  
        ein_match = re.search(r'\b\d{2}-?\d{7}\b', text_content)
        if ein_match:
            result['b'] = ein_match.group()
        
        # Extract currency amounts with better context
        wages = self._extract_currency_with_context(text_content, ['wages', 'box 1', 'compensation'])
        if wages:
            result['1'] = str(wages)
            
        federal = self._extract_currency_with_context(text_content, ['federal', 'withheld', 'box 2'])
        if federal:
            result['2'] = str(federal)
            
        ss_wages = self._extract_currency_with_context(text_content, ['social security wages', 'box 3'])
        if ss_wages:
            result['3'] = str(ss_wages)
            
        medicare = self._extract_currency_with_context(text_content, ['medicare wages', 'box 5'])
        if medicare:
            result['5'] = str(medicare)
        
        return {k: v for k, v in result.items() if v is not None}
    
    def _layer2_bedrock_claude(self, textract_response: Dict[str, Any], doc_type: str, missing_fields: List[str]) -> Dict[str, Any]:
        """Layer 2: Use Bedrock Claude for intelligent extraction of missing fields"""
        
        if doc_type != "W-2":
            return {}
            
        text_content = self._extract_text_from_textract(textract_response)
        
        if not text_content.strip():
            logger.warning("No text content found for Claude extraction")
            return {}
        
        # Enhanced prompt for comprehensive W-2 extraction
        prompt = f"""You are a tax document expert. Extract ALL W-2 form fields from this document text.

Return ONLY a JSON object with these exact field names (use empty string "" if field not found):

{{
  "a": "Employee's social security number (format: XXX-XX-XXXX)",
  "b": "Employer identification number EIN (format: XX-XXXXXXX)", 
  "c": "Employer's name, address, and ZIP code (full text)",
  "d": "Control number",
  "e": "Employee's first name and middle initial",
  "f": "Employee's last name and address with ZIP code",
  "1": "Wages, tips, other compensation (Box 1 amount)",
  "2": "Federal income tax withheld (Box 2 amount)",
  "3": "Social security wages (Box 3 amount)",
  "4": "Social security tax withheld (Box 4 amount)",
  "5": "Medicare wages and tips (Box 5 amount)",
  "6": "Medicare tax withheld (Box 6 amount)",
  "15": "State abbreviation (Box 15)",
  "16": "State wages, tips, etc. (Box 16 amount)",
  "17": "State income tax (Box 17 amount)",
  "18": "Local wages, tips, etc. (Box 18 amount)",
  "19": "Local income tax (Box 19 amount)",
  "20": "Locality name (Box 20)",
  "box12": [{{"code": "letter code", "amount": "dollar amount"}}],
  "employer_state_id": "Employer's state ID number",
  "first_name": "Employee first name only",
  "last_name": "Employee last name only"
}}

Document OCR Text:
{text_content}

IMPORTANT: 
- Extract ALL fields even if some are empty
- Keep currency amounts as strings with commas (e.g., "50,000.00")
- Use exact format shown above
- Return ONLY the JSON object, no other text
"""

        try:
            bedrock_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            logger.info(f"Calling Bedrock Claude with model: {self.model_id}")
            
            # Add retry logic for throttling
            import time
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    response = self.bedrock_client.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps(bedrock_request)
                    )
                    break
                except Exception as e:
                    if 'ThrottlingException' in str(e) and attempt < max_retries - 1:
                        logger.warning(f"Throttled, waiting {2 ** attempt} seconds...")
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise e
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            logger.info(f"Claude response length: {len(content)}")
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    extracted = json.loads(json_match.group())
                    # Filter out empty strings and null values
                    filtered = {k: v for k, v in extracted.items() 
                              if v is not None and v != "" and k not in ['layers_used', 'confidence_scores', 'extraction_method', 'total_fields_extracted']}
                    logger.info(f"Claude successfully extracted {len(filtered)} non-empty fields: {list(filtered.keys())}")
                    return filtered
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    logger.error(f"Raw Claude response: {content[:500]}...")
                    return {}
            else:
                logger.error(f"No JSON found in Claude response: {content[:200]}...")
                return {}
            
        except Exception as e:
            logger.error(f"Bedrock extraction failed: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
        
        return {}
    
    def _layer3_regex_patterns(self, textract_response: Dict[str, Any], doc_type: str, critical_fields: List[str]) -> Dict[str, Any]:
        """Layer 3: Regex patterns as safety net for critical fields"""
        
        text_content = self._extract_text_from_textract(textract_response)
        result = {}
        
        for field in critical_fields:
            if field == 'wages_income':
                result[field] = self._extract_currency_with_context(text_content, ['wages', 'box 1'])
            elif field == 'federal_withheld':
                result[field] = self._extract_currency_with_context(text_content, ['federal', 'box 2'])
            elif field == 'employee_ssn':
                ssn_match = re.search(r'\b\d{3}-\d{2}-\d{4}\b', text_content)
                if ssn_match:
                    result[field] = ssn_match.group()
        
        return {k: v for k, v in result.items() if v is not None}
    
    def _extract_text_from_textract(self, textract_response: Dict[str, Any]) -> str:
        """Extract text content from Textract response"""
        text_blocks = []
        
        for block in textract_response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                text = block.get('Text', '').strip()
                if text:
                    text_blocks.append(text)
        
        return '\n'.join(text_blocks)
    
    def _extract_currency_with_context(self, text: str, keywords: List[str]) -> float:
        """Extract currency value with better context matching"""
        text_lower = text.lower()
        
        for keyword in keywords:
            # Find keyword position
            pos = text_lower.find(keyword.lower())
            if pos != -1:
                # Look for currency in nearby text (±50 characters for better precision)
                start = max(0, pos - 50)
                end = min(len(text), pos + 100)
                nearby_text = text[start:end]
                
                # Find currency patterns, prioritize larger amounts
                currency_matches = re.findall(r'\$?([0-9,]+\.?[0-9]{0,2})', nearby_text)
                if currency_matches:
                    # Filter out small numbers that might be box numbers or years
                    valid_amounts = []
                    for match in currency_matches:
                        try:
                            value = float(match.replace(',', ''))
                            if value >= 10:  # Ignore small numbers like box numbers
                                valid_amounts.append(value)
                        except ValueError:
                            continue
                    
                    if valid_amounts:
                        # Return the largest reasonable amount
                        return max(valid_amounts)
        
        return None
    
    def _get_missing_fields(self, current_data: Dict[str, Any], doc_type: str) -> List[str]:
        """Get list of missing fields for the document type"""
        if doc_type == "W-2":
            expected_fields = list(self.w2_fields.keys())
            return [field for field in expected_fields if field not in current_data or current_data[field] is None]
        return []
    
    def _get_critical_missing_fields(self, current_data: Dict[str, Any], doc_type: str) -> List[str]:
        """Get critical fields that must be extracted"""
        if doc_type == "W-2":
            critical_fields = ['1', '2', 'a', 'b']  # Box 1, Box 2, SSN, EIN
        else:
            critical_fields = ['wages_income', 'federal_withheld', 'employee_ssn', 'employer_ein']
        return [field for field in critical_fields if field not in current_data or current_data[field] is None]
    
    def _post_process_data(self, data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Clean and validate extracted data"""
        processed = {}
        
        for key, value in data.items():
            if key in ['layers_used', 'confidence_scores', 'extraction_method', 'total_fields_extracted']:
                processed[key] = value
                continue
                
            if value is None or value == "":
                processed[key] = None
            elif key in ['wages_income', 'federal_withheld', 'social_security_wages', 
                        'social_security_tax', 'medicare_wages', 'medicare_tax',
                        'state_wages', 'state_income_tax', 'local_wages', 'local_income_tax']:
                processed[key] = self._clean_currency(value)
            elif key in ['employee_ssn']:
                processed[key] = self._clean_ssn(value)
            elif key in ['employer_ein']:
                processed[key] = self._clean_ein(value)
            else:
                processed[key] = value
        
        return processed
    
    def _clean_currency(self, value) -> float:
        """Clean and convert currency values"""
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            
            clean_value = str(value).replace('$', '').replace(',', '').strip()
            return float(clean_value) if clean_value else None
        except (ValueError, TypeError):
            return None
    
    def _clean_ssn(self, value) -> str:
        """Clean and validate SSN format"""
        if not value:
            return None
        
        digits = re.sub(r'\D', '', str(value))
        
        if len(digits) == 9:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        
        return None
    
    def _clean_ein(self, value) -> str:
        """Clean and validate EIN format"""
        if not value:
            return None
        
        digits = re.sub(r'\D', '', str(value))
        
        if len(digits) == 9:
            return f"{digits[:2]}-{digits[2:]}"
        
        return None