import json
import re
import boto3
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal

class W2ExtractorService:
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.claude_model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        
    def extract_w2_fields(self, textract_response: Dict[str, Any], document_bytes: bytes = None) -> Dict[str, Any]:
        """Enhanced W-2 extraction using AI + rule-based hybrid approach"""
        
        # Primary: AI-enhanced extraction
        ai_fields = self._extract_with_claude(textract_response, document_bytes)
        
        # Secondary: Rule-based fallback
        rule_fields = self._extract_with_rules(textract_response)
        
        # Merge and validate results
        final_fields = self._merge_and_validate(ai_fields, rule_fields)
        
        return final_fields
    
    def _extract_with_claude(self, textract_response: Dict[str, Any], document_bytes: bytes = None) -> Dict[str, Any]:
        """Extract W-2 fields using Claude AI"""
        try:
            # Get text from Textract
            text = self._get_full_text(textract_response)
            
            # Construct prompt for W-2 extraction
            prompt = f"""You are a tax document assistant. Extract all key fields from this W-2 form and output them in JSON format.

Document text:
{text}

Extract these W-2 fields (use null if not found):
- EmployeeName
- EmployeeSSN  
- EmployerName
- EmployerEIN
- TaxYear
- Box1_Wages (Wages, tips, other compensation)
- Box2_FederalTaxWithheld (Federal income tax withheld)
- Box3_SocialSecurityWages (Social security wages)
- Box4_SocialSecurityTaxWithheld (Social security tax withheld)
- Box5_MedicareWages (Medicare wages and tips)
- Box6_MedicareTaxWithheld (Medicare tax withheld)
- Box7_SocialSecurityTips (Social security tips)
- Box8_AllocatedTips (Allocated tips)
- Box10_DependentCareBenefits (Dependent care benefits)
- Box11_NonqualifiedPlans (Nonqualified plans)
- Box12_Codes (Box 12 codes and amounts as array)
- Box13_StatutoryEmployee (checkbox)
- Box13_RetirementPlan (checkbox)
- Box13_ThirdPartySickPay (checkbox)
- Box15_State (State)
- Box16_StateWages (State wages, tips, etc.)
- Box17_StateTaxWithheld (State income tax)

Return only valid JSON with numeric values as numbers, not strings."""

            # Call Claude
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            ai_output = response_body['content'][0]['text']
            
            # Parse JSON from AI response
            try:
                # Extract JSON from response (handle cases where AI adds explanation)
                json_start = ai_output.find('{')
                json_end = ai_output.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = ai_output[json_start:json_end]
                    ai_fields = json.loads(json_str)
                    print(f"Claude extracted {len(ai_fields)} W-2 fields")
                    return ai_fields
                else:
                    print("No valid JSON found in Claude response")
                    return {}
            except json.JSONDecodeError as e:
                print(f"Failed to parse Claude JSON response: {e}")
                return {}
                
        except Exception as e:
            print(f"Claude W-2 extraction failed: {e}")
            return {}
    
    def _extract_with_rules(self, textract_response: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based W-2 extraction (existing logic + enhanced patterns)"""
        fields = {}
        text = self._get_full_text(textract_response)
        
        # Enhanced regex patterns for better coverage
        patterns = {
            'Box1_Wages': [
                r'wages.*?tips.*?compensation.*?(\$?[\d,]+\.?\d*)',
                r'box\s*1.*?(\$?[\d,]+\.?\d*)',
                r'1\s+wages.*?(\$?[\d,]+\.?\d*)'
            ],
            'Box2_FederalTaxWithheld': [
                r'federal.*?income.*?tax.*?withheld.*?(\$?[\d,]+\.?\d*)',
                r'box\s*2.*?(\$?[\d,]+\.?\d*)',
                r'2\s+federal.*?(\$?[\d,]+\.?\d*)'
            ],
            'Box3_SocialSecurityWages': [
                r'social.*?security.*?wages.*?(\$?[\d,]+\.?\d*)',
                r'box\s*3.*?(\$?[\d,]+\.?\d*)',
                r'3\s+social.*?security.*?(\$?[\d,]+\.?\d*)'
            ],
            'Box4_SocialSecurityTaxWithheld': [
                r'social.*?security.*?tax.*?withheld.*?(\$?[\d,]+\.?\d*)',
                r'box\s*4.*?(\$?[\d,]+\.?\d*)'
            ],
            'Box5_MedicareWages': [
                r'medicare.*?wages.*?(\$?[\d,]+\.?\d*)',
                r'box\s*5.*?(\$?[\d,]+\.?\d*)'
            ],
            'Box6_MedicareTaxWithheld': [
                r'medicare.*?tax.*?withheld.*?(\$?[\d,]+\.?\d*)',
                r'box\s*6.*?(\$?[\d,]+\.?\d*)'
            ]
        }
        
        # Extract using multiple patterns per field
        for field_name, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    amount = self._extract_amount(match.group(1))
                    if amount is not None:
                        fields[field_name] = amount
                        break
        
        # Extract non-monetary fields
        fields.update(self._extract_w2_text_fields(text))
        
        print(f"Rule-based extraction found {len(fields)} W-2 fields")
        return fields
    
    def _extract_w2_text_fields(self, text: str) -> Dict[str, Any]:
        """Extract text fields from W-2"""
        fields = {}
        
        # Employee SSN pattern
        ssn_match = re.search(r'(\d{3}-\d{2}-\d{4})', text)
        if ssn_match:
            fields['EmployeeSSN'] = ssn_match.group(1)
        
        # Tax year pattern
        year_match = re.search(r'(20\d{2})', text)
        if year_match:
            fields['TaxYear'] = int(year_match.group(1))
        
        # EIN pattern
        ein_match = re.search(r'(\d{2}-\d{7})', text)
        if ein_match:
            fields['EmployerEIN'] = ein_match.group(1)
        
        return fields
    
    def _merge_and_validate(self, ai_fields: Dict[str, Any], rule_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Merge AI and rule-based results with validation"""
        final_fields = {}
        conflicts = []
        
        # Start with AI fields as primary
        final_fields.update(ai_fields)
        
        # Cross-validate overlapping fields
        common_fields = set(ai_fields.keys()) & set(rule_fields.keys())
        
        for field in common_fields:
            ai_val = ai_fields[field]
            rule_val = rule_fields[field]
            
            # For numeric fields, check if values are close
            if isinstance(ai_val, (int, float)) and isinstance(rule_val, (int, float)):
                if abs(ai_val - rule_val) / max(ai_val, rule_val, 1) > 0.05:  # 5% tolerance
                    conflicts.append({
                        'field': field,
                        'ai_value': ai_val,
                        'rule_value': rule_val,
                        'confidence': 'low'
                    })
                    final_fields[f'{field}_conflict'] = True
                else:
                    final_fields[f'{field}_confidence'] = 'high'
            
            # For text fields, exact match
            elif ai_val != rule_val and ai_val and rule_val:
                conflicts.append({
                    'field': field,
                    'ai_value': ai_val,
                    'rule_value': rule_val,
                    'confidence': 'medium'
                })
        
        # Add rule-based fields that AI missed
        for field, value in rule_fields.items():
            if field not in ai_fields and value is not None:
                final_fields[field] = value
                final_fields[f'{field}_source'] = 'rule_based'
        
        # Add validation metadata
        if conflicts:
            final_fields['_validation'] = {
                'conflicts_detected': len(conflicts),
                'conflicts': conflicts,
                'needs_review': True
            }
            print(f"W-2 extraction conflicts detected: {len(conflicts)}")
        else:
            final_fields['_validation'] = {
                'conflicts_detected': 0,
                'needs_review': False,
                'confidence': 'high'
            }
        
        # Calculate completeness score
        expected_fields = ['Box1_Wages', 'Box2_FederalTaxWithheld', 'EmployeeName', 'EmployerName', 'TaxYear']
        found_fields = sum(1 for field in expected_fields if field in final_fields and final_fields[field])
        completeness = found_fields / len(expected_fields)
        final_fields['_validation']['completeness_score'] = completeness
        
        print(f"W-2 extraction completed: {len(final_fields)} total fields, {completeness:.1%} completeness")
        return final_fields
    
    def _get_full_text(self, response: Dict[str, Any]) -> str:
        """Get all text from Textract response"""
        text_lines = []
        
        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
        
        return '\n'.join(text_lines)
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """Extract monetary amount from text"""
        if not text:
            return None
        
        # Clean and extract number
        cleaned = re.sub(r'[^\d.]', '', text)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None