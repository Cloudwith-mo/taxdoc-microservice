"""
Tax Data Extractor using Claude for V1 MVP
Extracts structured data from W-2 and 1099 forms
"""
import json
import requests
import os
import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger()

class TaxExtractor:
    """Extract tax data using Claude LLM"""
    
    def __init__(self):
        self.claude_api_key = os.environ.get('CLAUDE_API_KEY')
        self.claude_url = "https://api.anthropic.com/v1/messages"
        
        # Field definitions for each form type
        self.form_fields = {
            "W-2": {
                "employee_ssn": "Employee's Social Security Number",
                "employer_ein": "Employer's EIN",
                "employee_name": "Employee's Name",
                "employer_name": "Employer's Name",
                "wages_income": "Wages, tips, other compensation (Box 1)",
                "federal_withheld": "Federal income tax withheld (Box 2)",
                "social_security_wages": "Social Security wages (Box 3)",
                "social_security_tax": "Social Security tax withheld (Box 4)",
                "medicare_wages": "Medicare wages and tips (Box 5)",
                "medicare_tax": "Medicare tax withheld (Box 6)"
            },
            "1099-NEC": {
                "payer_tin": "Payer's TIN",
                "recipient_tin": "Recipient's TIN",
                "payer_name": "Payer's Name",
                "recipient_name": "Recipient's Name",
                "nonemployee_compensation": "Nonemployee compensation (Box 1)",
                "federal_withheld": "Federal income tax withheld (Box 4)"
            },
            "1099-MISC": {
                "payer_tin": "Payer's TIN",
                "recipient_tin": "Recipient's TIN",
                "payer_name": "Payer's Name",
                "recipient_name": "Recipient's Name",
                "rents": "Rents (Box 1)",
                "royalties": "Royalties (Box 2)",
                "other_income": "Other income (Box 3)",
                "federal_withheld": "Federal income tax withheld (Box 4)"
            },
            "1099-DIV": {
                "payer_name": "Payer's Name",
                "recipient_name": "Recipient's Name",
                "ordinary_dividends": "Ordinary dividends (Box 1a)",
                "qualified_dividends": "Qualified dividends (Box 1b)",
                "federal_withheld": "Federal income tax withheld (Box 4)"
            },
            "1099-INT": {
                "payer_name": "Payer's Name",
                "recipient_name": "Recipient's Name",
                "interest_income": "Interest income (Box 1)",
                "federal_withheld": "Federal income tax withheld (Box 4)"
            }
        }
    
    def extract_tax_data(self, textract_response: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Extract structured data from tax document"""
        
        # Get text content from Textract
        text_content = self._extract_text_from_textract(textract_response)
        
        # Get field definitions for this document type
        fields = self.form_fields.get(doc_type, {})
        
        if not fields:
            return {"error": f"No field definitions for document type: {doc_type}"}
        
        # Extract data using Claude
        extracted_data = self._extract_with_claude(text_content, doc_type, fields)
        
        # Post-process and validate
        processed_data = self._post_process_data(extracted_data, doc_type)
        
        return processed_data
    
    def _extract_text_from_textract(self, textract_response: Dict[str, Any]) -> str:
        """Extract text content from Textract response"""
        text_blocks = []
        
        for block in textract_response.get('Blocks', []):
            if block.get('BlockType') == 'LINE':
                text = block.get('Text', '').strip()
                if text:
                    text_blocks.append(text)
        
        return '\n'.join(text_blocks)
    
    def _extract_with_claude(self, text_content: str, doc_type: str, fields: Dict[str, str]) -> Dict[str, Any]:
        """Use Claude to extract structured data"""
        
        if not self.claude_api_key:
            logger.warning("No Claude API key found, using fallback extraction")
            return self._fallback_extraction(text_content, doc_type)
        
        # Build field list for prompt
        field_descriptions = []
        for field_key, field_desc in fields.items():
            field_descriptions.append(f"- {field_key}: {field_desc}")
        
        prompt = f"""You are a tax document data extraction assistant. Extract the following fields from this {doc_type} tax form:

{chr(10).join(field_descriptions)}

Document text:
{text_content}

Return ONLY a valid JSON object with the extracted values. Use null for missing values. For currency amounts, return numeric values without dollar signs or commas. For SSN/EIN, keep the format with dashes.

Example format:
{{"field_name": "value", "numeric_field": 1234.56, "missing_field": null}}"""

        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(self.claude_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    logger.error("No JSON found in Claude response")
                    return self._fallback_extraction(text_content, doc_type)
            else:
                logger.error(f"Claude API error: {response.status_code}")
                return self._fallback_extraction(text_content, doc_type)
                
        except Exception as e:
            logger.error(f"Claude extraction failed: {str(e)}")
            return self._fallback_extraction(text_content, doc_type)
    
    def _fallback_extraction(self, text_content: str, doc_type: str) -> Dict[str, Any]:
        """Simple regex-based fallback extraction"""
        
        result = {"extraction_method": "fallback_regex"}
        
        # Basic patterns for common fields
        patterns = {
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "ein": r'\b\d{2}-\d{7}\b',
            "currency": r'\$?[\d,]+\.?\d{0,2}',
            "box_1": r'(?:box\s*1|1\.)\s*[\$\d,\.]+',
            "box_2": r'(?:box\s*2|2\.)\s*[\$\d,\.]+',
            "box_3": r'(?:box\s*3|3\.)\s*[\$\d,\.]+',
            "box_4": r'(?:box\s*4|4\.)\s*[\$\d,\.]+'
        }
        
        text_lower = text_content.lower()
        
        # Extract SSNs and EINs
        ssns = re.findall(patterns["ssn"], text_content)
        eins = re.findall(patterns["ein"], text_content)
        
        if doc_type == "W-2":
            result.update({
                "employee_ssn": ssns[0] if ssns else None,
                "employer_ein": eins[0] if eins else None,
                "wages_income": self._extract_currency_near_text(text_content, ["wages", "box 1"]),
                "federal_withheld": self._extract_currency_near_text(text_content, ["federal", "withheld", "box 2"]),
                "social_security_wages": self._extract_currency_near_text(text_content, ["social security", "box 3"]),
                "medicare_wages": self._extract_currency_near_text(text_content, ["medicare", "box 5"])
            })
        elif doc_type.startswith("1099"):
            result.update({
                "payer_tin": eins[0] if eins else None,
                "recipient_tin": ssns[0] if ssns else eins[1] if len(eins) > 1 else None
            })
            
            if doc_type == "1099-NEC":
                result["nonemployee_compensation"] = self._extract_currency_near_text(text_content, ["nonemployee", "compensation", "box 1"])
            elif doc_type == "1099-INT":
                result["interest_income"] = self._extract_currency_near_text(text_content, ["interest", "income", "box 1"])
        
        return result
    
    def _extract_currency_near_text(self, text: str, keywords: List[str]) -> float:
        """Extract currency value near specific keywords"""
        text_lower = text.lower()
        
        for keyword in keywords:
            # Find keyword position
            pos = text_lower.find(keyword.lower())
            if pos != -1:
                # Look for currency in nearby text (±100 characters)
                start = max(0, pos - 100)
                end = min(len(text), pos + 100)
                nearby_text = text[start:end]
                
                # Find currency patterns
                currency_matches = re.findall(r'\$?([\d,]+\.?\d{0,2})', nearby_text)
                if currency_matches:
                    try:
                        # Return first valid currency value
                        value_str = currency_matches[0].replace(',', '')
                        return float(value_str)
                    except ValueError:
                        continue
        
        return None
    
    def _post_process_data(self, data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Clean and validate extracted data"""
        
        processed = {}
        
        for key, value in data.items():
            if value is None or value == "":
                processed[key] = None
            elif key in ["wages_income", "federal_withheld", "social_security_wages", 
                        "social_security_tax", "medicare_wages", "medicare_tax",
                        "nonemployee_compensation", "interest_income", "ordinary_dividends",
                        "qualified_dividends", "rents", "royalties", "other_income"]:
                # Process currency fields
                processed[key] = self._clean_currency(value)
            elif key in ["employee_ssn", "recipient_tin"]:
                # Process SSN fields
                processed[key] = self._clean_ssn(value)
            elif key in ["employer_ein", "payer_tin"]:
                # Process EIN fields
                processed[key] = self._clean_ein(value)
            else:
                # Keep other fields as-is
                processed[key] = value
        
        return processed
    
    def _clean_currency(self, value) -> float:
        """Clean and convert currency values"""
        if value is None:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            
            # Remove currency symbols and commas
            clean_value = str(value).replace('$', '').replace(',', '').strip()
            return float(clean_value) if clean_value else None
        except (ValueError, TypeError):
            return None
    
    def _clean_ssn(self, value) -> str:
        """Clean and validate SSN format"""
        if not value:
            return None
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(value))
        
        if len(digits) == 9:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        
        return None
    
    def _clean_ein(self, value) -> str:
        """Clean and validate EIN format"""
        if not value:
            return None
        
        # Extract digits only
        digits = re.sub(r'\D', '', str(value))
        
        if len(digits) == 9:
            return f"{digits[:2]}-{digits[2:]}"
        
        return None