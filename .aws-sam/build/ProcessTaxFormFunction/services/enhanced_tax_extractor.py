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
        self.model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        
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
        
        # Layer 1: Textract Queries (high precision)
        try:
            layer1_data = self._layer1_textract_queries(textract_response, doc_type)
            layers_used.append("textract_queries")
            final_data.update(layer1_data)
            logger.info(f"Layer 1 extracted {len(layer1_data)} fields")
        except Exception as e:
            logger.warning(f"Layer 1 failed: {e}")
        
        # Layer 2: Bedrock Claude (intelligent fallback for missing fields)
        missing_fields = self._get_missing_fields(final_data, doc_type)
        if missing_fields:
            try:
                layer2_data = self._layer2_bedrock_claude(textract_response, doc_type, missing_fields)
                layers_used.append("bedrock_claude")
                final_data.update(layer2_data)
                logger.info(f"Layer 2 filled {len(layer2_data)} missing fields")
            except Exception as e:
                logger.warning(f"Layer 2 failed: {e}")
        
        # Layer 3: Regex patterns (safety net for critical fields)
        critical_missing = self._get_critical_missing_fields(final_data, doc_type)
        if critical_missing:
            try:
                layer3_data = self._layer3_regex_patterns(textract_response, doc_type, critical_missing)
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
            'total_fields_extracted': len([v for v in processed_data.values() if v is not None])
        })
        
        return processed_data
    
    def _layer1_textract_queries(self, textract_response: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Layer 1: Use Textract natural language queries for high-precision extraction"""
        
        if doc_type != "W-2":
            return {}
        
        # Define W-2 queries for high-confidence fields
        queries = [
            "What is the employee's social security number?",
            "What is the employer identification number or EIN?", 
            "What are the wages, tips, and other compensation in box 1?",
            "What is the federal income tax withheld in box 2?",
            "What are the social security wages in box 3?",
            "What is the social security tax withheld in box 4?",
            "What are the medicare wages and tips in box 5?",
            "What is the medicare tax withheld in box 6?",
            "What is the employee's name?",
            "What is the employer's name?"
        ]
        
        # Extract text for queries (simplified - in real implementation would use Textract queries API)
        text_content = self._extract_text_from_textract(textract_response)
        
        # Parse key fields using text analysis
        result = {}
        
        # Extract SSN
        ssn_match = re.search(r'\b\d{3}-\d{2}-\d{4}\b', text_content)
        if ssn_match:
            result['employee_ssn'] = ssn_match.group()
        
        # Extract EIN  
        ein_match = re.search(r'\b\d{2}-\d{7}\b', text_content)
        if ein_match:
            result['employer_ein'] = ein_match.group()
        
        # Extract currency amounts with better context
        result['wages_income'] = self._extract_currency_with_context(text_content, ['wages', 'box 1', 'compensation'])
        result['federal_withheld'] = self._extract_currency_with_context(text_content, ['federal', 'withheld', 'box 2'])
        result['social_security_wages'] = self._extract_currency_with_context(text_content, ['social security wages', 'box 3'])
        result['medicare_wages'] = self._extract_currency_with_context(text_content, ['medicare wages', 'box 5'])
        
        return {k: v for k, v in result.items() if v is not None}
    
    def _layer2_bedrock_claude(self, textract_response: Dict[str, Any], doc_type: str, missing_fields: List[str]) -> Dict[str, Any]:
        """Layer 2: Use Bedrock Claude for intelligent extraction of missing fields"""
        
        text_content = self._extract_text_from_textract(textract_response)
        
        # Build prompt for missing fields
        field_descriptions = []
        for field in missing_fields:
            if field in self.w2_fields:
                field_descriptions.append(f"- {field}: {self.w2_fields[field]}")
        
        prompt = f"""Extract the following missing fields from this {doc_type} tax form:

{chr(10).join(field_descriptions)}

Document text:
{text_content}

Return ONLY a JSON object with the extracted values. Use null for missing values.
For currency amounts: return numeric values without $ or commas.
For Box 12 codes: return as array of objects with "code" and "amount" fields.
For checkboxes: return true/false.

Example: {{"state": "CA", "state_wages": 50000.00, "box12_codes": [{{"code": "D", "amount": 1500.00}}]}}"""

        try:
            bedrock_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(bedrock_request)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            logger.error(f"Bedrock extraction failed: {e}")
        
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