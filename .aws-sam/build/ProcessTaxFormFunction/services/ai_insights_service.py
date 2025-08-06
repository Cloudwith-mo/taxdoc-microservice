import boto3
import json
from typing import Dict, Any, List

class AIInsightsService:
    """AI-powered document insights and summarization"""
    
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    def generate_insights(self, extracted_data: Dict[str, Any], document_type: str) -> Dict[str, Any]:
        """Generate 3-bullet management insights"""
        
        prompt = f"""Analyze this {document_type} data and provide exactly 3 bullet points of "So-What?" insights for management:

Document Type: {document_type}
Extracted Data: {json.dumps(extracted_data, indent=2)}

Focus on:
- Business impact
- Financial implications  
- Action items needed
- Risk factors
- Compliance considerations

Return JSON format:
{{
  "insights": [
    "First key insight with business impact",
    "Second insight about financial implications", 
    "Third insight about actions needed"
  ],
  "summary": "One-sentence executive summary",
  "risk_level": "low|medium|high",
  "action_required": true/false
}}"""

        return self._call_claude(prompt)
    
    def analyze_sentiment(self, document_text: str, document_type: str) -> Dict[str, Any]:
        """Universal sentiment analysis for any document type"""
        
        prompt = f"""Analyze the sentiment and emotional context of this {document_type}:

Text: {document_text[:2000]}

Return JSON:
{{
  "sentiment": "positive|negative|neutral",
  "confidence": 0.95,
  "emotional_indicators": ["professional", "urgent", "concerned"],
  "tone": "formal|informal|aggressive|friendly",
  "key_phrases": ["phrase1", "phrase2"],
  "business_impact": "Description of how sentiment affects business"
}}"""

        return self._call_claude(prompt)
    
    def extract_action_items(self, document_text: str, document_type: str) -> List[Dict[str, Any]]:
        """Extract actionable items from documents"""
        
        prompt = f"""Extract action items from this {document_type}:

Text: {document_text[:2000]}

Return JSON array:
[
  {{
    "action": "Specific action needed",
    "priority": "high|medium|low", 
    "deadline": "timeframe if mentioned",
    "responsible_party": "who should handle this",
    "category": "compliance|financial|operational"
  }}
]"""

        result = self._call_claude(prompt)
        return result.get('actions', [])
    
    def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Call Claude via Bedrock"""
        
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.3,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            claude_output = response_body['content'][0]['text']
            
            # Parse JSON response
            json_start = claude_output.find('{')
            json_end = claude_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = claude_output[json_start:json_end]
                return json.loads(json_str)
            
        except Exception as e:
            print(f"AI insights failed: {e}")
        
        return {}