import boto3
import json
from typing import Dict, Any, Optional

class BedrockClaudeService:
    """Service for Claude LLM processing via Amazon Bedrock"""
    
    def __init__(self):
        self.client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
    
    def extract_fields(self, document_text: str, document_type: str, target_fields: list) -> Dict[str, Any]:
        """Extract fields using Claude LLM"""
        
        prompt = self._build_extraction_prompt(document_text, document_type, target_fields)
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            llm_output = response_body['content'][0]['text']
            
            return self._parse_llm_response(llm_output)
            
        except Exception as e:
            print(f"Claude LLM processing failed: {e}")
            return {}
    
    def _build_extraction_prompt(self, document_text: str, document_type: str, target_fields: list) -> str:
        """Build extraction prompt for Claude"""
        
        fields_list = ', '.join(target_fields)
        
        return f"""
Extract the following fields from this {document_type} document:
{fields_list}

Document text:
{document_text[:4000]}

Return only valid JSON with exact field names. Use null for missing values.
Example: {{"field1": "value1", "field2": null, "field3": "value3"}}
"""
    
    def _parse_llm_response(self, llm_output: str) -> Dict[str, Any]:
        """Parse JSON response from Claude"""
        
        try:
            # Find JSON in response
            json_start = llm_output.find('{')
            json_end = llm_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_output[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Format with metadata
                results = {}
                for field, value in parsed_data.items():
                    if value is not None and value != "":
                        results[field] = {
                            'value': value,
                            'confidence': 0.85,
                            'source': 'claude_llm'
                        }
                
                return results
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM JSON response: {e}")
        
        return {}
    
    def extract_fields_json_mode(self, document_text: str, prompt: str, schema_fields: list) -> Dict[str, Any]:
        """Extract fields using Claude with strict JSON mode"""
        
        enhanced_prompt = f"""{prompt}
        
Document text:
{document_text[:4000]}

IMPORTANT: Return ONLY valid JSON. No explanations or additional text.
Schema: {{{', '.join([f'"{field}": null' for field in schema_fields])}}}
"""
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.0,  # More deterministic
            "messages": [{"role": "user", "content": enhanced_prompt}]
        }
        
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            llm_output = response_body['content'][0]['text']
            
            return self._parse_strict_json_response(llm_output)
            
        except Exception as e:
            print(f"Claude JSON mode processing failed: {e}")
            return {}
    
    def _parse_strict_json_response(self, llm_output: str) -> Dict[str, Any]:
        """Parse strict JSON response from Claude"""
        
        try:
            # Clean the response - remove any markdown or extra text
            cleaned_output = llm_output.strip()
            
            # Remove markdown code blocks if present
            if cleaned_output.startswith('```json'):
                cleaned_output = cleaned_output[7:]
            if cleaned_output.startswith('```'):
                cleaned_output = cleaned_output[3:]
            if cleaned_output.endswith('```'):
                cleaned_output = cleaned_output[:-3]
            
            cleaned_output = cleaned_output.strip()
            
            # Find JSON boundaries
            json_start = cleaned_output.find('{')
            json_end = cleaned_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_output[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Format with metadata and higher confidence for JSON mode
                results = {}
                for field, value in parsed_data.items():
                    if value is not None and str(value).strip() != "":
                        results[field] = {
                            'value': value,
                            'confidence': 0.88,  # Higher confidence for JSON mode
                            'source': 'claude_json'
                        }
                
                return results
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse strict JSON response: {e}")
            print(f"Raw output: {llm_output[:500]}")
        
        return {}