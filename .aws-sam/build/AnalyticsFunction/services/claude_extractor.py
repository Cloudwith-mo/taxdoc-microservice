import json
import requests
from typing import Dict, Any

class ClaudeExtractor:
    """Claude-based field extraction for tax forms"""
    
    def __init__(self):
        self.api_key = None  # Set via environment variable
        self.prompts = {
            'W-2': """Extract the following fields from this W-2 form text and return ONLY valid JSON:
{
  "employer_name": "employer name",
  "employer_ein": "employer EIN (XX-XXXXXXX format)",
  "employee_name": "employee name", 
  "employee_ssn": "employee SSN (XXX-XX-XXXX format)",
  "wages_box1": "wages, tips, other compensation (Box 1) as number",
  "federal_tax_withheld_box2": "federal income tax withheld (Box 2) as number",
  "social_security_wages_box3": "social security wages (Box 3) as number",
  "social_security_tax_box4": "social security tax withheld (Box 4) as number",
  "medicare_wages_box5": "medicare wages and tips (Box 5) as number",
  "medicare_tax_box6": "medicare tax withheld (Box 6) as number"
}""",
            '1099-NEC': """Extract the following fields from this 1099-NEC form text and return ONLY valid JSON:
{
  "payer_name": "payer name",
  "payer_tin": "payer TIN",
  "recipient_name": "recipient name",
  "recipient_tin": "recipient TIN", 
  "nonemployee_compensation_box1": "nonemployee compensation (Box 1) as number",
  "federal_tax_withheld_box4": "federal income tax withheld (Box 4) as number"
}""",
            '1099-INT': """Extract the following fields from this 1099-INT form text and return ONLY valid JSON:
{
  "payer_name": "payer name",
  "payer_tin": "payer TIN",
  "recipient_name": "recipient name", 
  "recipient_tin": "recipient TIN",
  "interest_income_box1": "interest income (Box 1) as number",
  "federal_tax_withheld_box4": "federal income tax withheld (Box 4) as number"
}"""
        }
    
    def extract_fields(self, textract_response: Dict[str, Any], form_type: str) -> Dict[str, Any]:
        """Extract fields using Claude API"""
        
        # Extract text from Textract response
        text_content = self._extract_text(textract_response)
        
        # Get appropriate prompt
        prompt = self.prompts.get(form_type, self.prompts['W-2'])
        
        # For MVP, use boto3 Bedrock instead of direct API
        return self._extract_with_bedrock(text_content, prompt)
    
    def _extract_with_bedrock(self, text_content: str, prompt: str) -> Dict[str, Any]:
        """Extract using AWS Bedrock Claude"""
        
        try:
            import boto3
            
            bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            full_prompt = f"{prompt}\n\nForm text:\n{text_content[:3000]}"
            
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": full_prompt}]
            }
            
            response = bedrock.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            claude_output = response_body['content'][0]['text']
            
            # Parse JSON from Claude response
            return self._parse_json_response(claude_output)
            
        except Exception as e:
            print(f"Claude extraction failed: {e}")
            return {}
    
    def _extract_text(self, textract_response: Dict[str, Any]) -> str:
        """Extract plain text from Textract response"""
        
        text_lines = []
        for block in textract_response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_lines.append(block.get('Text', ''))
        
        return '\n'.join(text_lines)
    
    def _parse_json_response(self, claude_output: str) -> Dict[str, Any]:
        """Parse JSON from Claude response"""
        
        try:
            # Find JSON in response
            json_start = claude_output.find('{')
            json_end = claude_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = claude_output[json_start:json_end]
                return json.loads(json_str)
            
        except json.JSONDecodeError:
            pass
        
        return {}