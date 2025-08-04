import boto3
import json
import os
from typing import Dict, Any, Optional, List

class BedrockService:
    def __init__(self):
        self.client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        self.enabled = os.environ.get('ENABLE_BEDROCK_SUMMARY', 'true').lower() == 'true'
        self.claude_model_id = 'anthropic.claude-sonnet-4-20250514-v1:0'
    
    def generate_summary(self, document_text: str, doc_type: str) -> Optional[str]:
        """Generate document summary using Bedrock LLM"""
        if not self.enabled:
            print("Bedrock summarization disabled")
            return None
        
        try:
            # Truncate text if too long
            max_chars = 3000
            if len(document_text) > max_chars:
                document_text = document_text[:max_chars] + "..."
                print(f"Truncated document text to {max_chars} characters for Bedrock")
            
            # Construct prompt
            prompt = f"Summarize the key information in this {doc_type} document:\n\n{document_text}\n\nProvide a brief, factual summary:"
            
            # Prepare payload based on model
            if self.model_id.startswith('amazon.titan'):
                payload = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 200,
                        "temperature": 0.2,
                        "topP": 0.9
                    }
                }
            elif self.model_id.startswith('anthropic.claude'):
                # Use new Claude 3 message format
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "temperature": 0.2,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            else:
                payload = {"inputText": prompt}
            
            # Call Bedrock
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(payload)
            )
            
            # Parse response
            model_response = json.loads(response['body'].read())
            
            if self.model_id.startswith('amazon.titan'):
                summary_text = model_response["results"][0]["outputText"]
            elif self.model_id.startswith('anthropic.claude'):
                # Handle new Claude 3 response format
                if 'content' in model_response and model_response['content']:
                    summary_text = model_response['content'][0]['text']
                else:
                    summary_text = model_response.get("completion", "")
            else:
                summary_text = str(model_response)
            
            summary = summary_text.strip()
            print(f"Generated Bedrock summary: {summary[:100]}...")
            return summary
            
        except Exception as e:
            print(f"Bedrock summarization failed: {e}")
            return None
    
    def extract_fuzzy_fields(self, document_text: str, doc_type: str) -> Dict[str, Any]:
        """Extract fields that are hard to regex using LLM"""
        if not self.enabled:
            return {}
        
        try:
            # Define extraction prompts by document type
            if doc_type == "Receipt":
                prompt = f"Extract the purpose/reason for this expense from the receipt:\n\n{document_text[:2000]}\n\nPurpose:"
            elif doc_type == "Invoice":
                prompt = f"Extract the business purpose and payment terms from this invoice:\n\n{document_text[:2000]}\n\nBusiness purpose and terms:"
            else:
                return {}
            
            # Similar Bedrock call as summary
            if self.model_id.startswith('amazon.titan'):
                payload = {
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": 100,
                        "temperature": 0.1
                    }
                }
            else:
                payload = {"inputText": prompt}
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(payload)
            )
            
            model_response = json.loads(response['body'].read())
            
            if self.model_id.startswith('amazon.titan'):
                extracted_text = model_response["results"][0]["outputText"]
            else:
                extracted_text = str(model_response)
            
            # Return as structured data
            if doc_type == "Receipt":
                return {"expense_purpose": extracted_text.strip()}
            elif doc_type == "Invoice":
                return {"business_purpose": extracted_text.strip()}
            
        except Exception as e:
            print(f"Bedrock field extraction failed: {e}")
            
        return {}
    
    def extract_structured_fields(self, document_text: str, document_type: str, field_list: List[str]) -> Dict[str, Any]:
        """Extract structured fields using Claude for any document type"""
        if not self.enabled:
            return {}
        
        try:
            # Construct field extraction prompt
            fields_str = ', '.join(field_list)
            prompt = f"""Extract the following fields from this {document_type} document: {fields_str}

Document text:
{document_text[:4000]}

Return only valid JSON with the exact field names listed above. Use null for missing values. Do not include explanatory text."""
            
            # Use Claude 3 format
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
            
            response = self.client.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            
            model_response = json.loads(response['body'].read())
            
            if 'content' in model_response and model_response['content']:
                extracted_text = model_response['content'][0]['text']
                
                # Parse JSON from response
                json_start = extracted_text.find('{')
                json_end = extracted_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = extracted_text[json_start:json_end]
                    return json.loads(json_str)
            
        except Exception as e:
            print(f"Bedrock structured field extraction failed: {e}")
            
        return {}