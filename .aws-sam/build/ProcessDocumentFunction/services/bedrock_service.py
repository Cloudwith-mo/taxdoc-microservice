import boto3
import json
import os
from typing import Dict, Any, Optional

class BedrockService:
    def __init__(self):
        self.client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = os.environ.get('BEDROCK_MODEL_ID', 'amazon.titan-text-premier-v1:0')
        self.enabled = os.environ.get('ENABLE_BEDROCK_SUMMARY', 'false').lower() == 'true'
    
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
                payload = {
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 200,
                    "temperature": 0.2
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