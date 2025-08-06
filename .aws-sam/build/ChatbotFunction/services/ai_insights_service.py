"""
AI Insights Service
Generates AI-powered insights and summaries for tax documents using Claude
"""
import json
import boto3
import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger()

class AIInsightsService:
    """Generate AI insights for processed tax documents"""
    
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    def generate_insights(self, extracted_data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Generate comprehensive AI insights for a document"""
        
        try:
            # Generate summary and insights
            summary = self._generate_summary(extracted_data, doc_type)
            insights = self._generate_key_insights(extracted_data, doc_type)
            risk_level = self._assess_risk_level(extracted_data, doc_type)
            action_required = self._determine_actions(extracted_data, doc_type)
            
            return {
                "summary": summary,
                "insights": insights,
                "risk_level": risk_level,
                "action_required": action_required,
                "confidence": 0.85,
                "generated_by": "claude_ai"
            }
            
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            return self._fallback_insights(doc_type)
    
    def _generate_summary(self, data: Dict[str, Any], doc_type: str) -> str:
        """Generate one-sentence executive summary"""
        
        prompt = f"""Based on this {doc_type} tax document data, provide a single sentence executive summary:

Data: {json.dumps(data, indent=2)}

Provide only one clear, concise sentence summarizing the key financial information."""

        try:
            response = self._call_claude(prompt, max_tokens=100)
            return response.strip()
        except:
            return f"Tax document processed with key financial data extracted from {doc_type}."
    
    def _generate_key_insights(self, data: Dict[str, Any], doc_type: str) -> List[str]:
        """Generate 3 key insights as bullet points"""
        
        prompt = f"""Analyze this {doc_type} tax document and provide exactly 3 key insights as bullet points:

Data: {json.dumps(data, indent=2)}

Focus on:
- Financial significance and tax implications
- Notable amounts or patterns
- Compliance or filing considerations

Return exactly 3 bullet points, each starting with a dash (-)."""

        try:
            response = self._call_claude(prompt, max_tokens=300)
            
            # Extract bullet points
            lines = response.strip().split('\n')
            insights = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('-') or line.startswith('•'):
                    insight = line[1:].strip()
                    if insight:
                        insights.append(insight)
            
            # Ensure we have exactly 3 insights
            if len(insights) >= 3:
                return insights[:3]
            elif len(insights) > 0:
                # Pad with generic insights if needed
                while len(insights) < 3:
                    insights.append("Document contains standard tax information requiring review.")
                return insights
            else:
                return self._default_insights(doc_type)
                
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return self._default_insights(doc_type)
    
    def _assess_risk_level(self, data: Dict[str, Any], doc_type: str) -> str:
        """Assess risk level based on document data"""
        
        try:
            # Simple risk assessment based on amounts
            if doc_type == "W-2":
                wages = data.get('wages_income', 0) or 0
                federal_withheld = data.get('federal_withheld', 0) or 0
                
                if isinstance(wages, (int, float)) and wages > 100000:
                    return "medium"
                elif isinstance(federal_withheld, (int, float)) and federal_withheld == 0 and wages > 0:
                    return "high"
                else:
                    return "low"
            
            return "low"
            
        except:
            return "low"
    
    def _determine_actions(self, data: Dict[str, Any], doc_type: str) -> bool:
        """Determine if action is required"""
        
        try:
            if doc_type == "W-2":
                # Check for missing critical data
                critical_fields = ['wages_income', 'federal_withheld', 'employee_ssn']
                missing_fields = [field for field in critical_fields if not data.get(field)]
                
                return len(missing_fields) > 0
            
            return False
            
        except:
            return False
    
    def _call_claude(self, prompt: str, max_tokens: int = 500) -> str:
        """Make API call to Claude via Bedrock"""
        
        bedrock_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self.bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(bedrock_request)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _default_insights(self, doc_type: str) -> List[str]:
        """Fallback insights when AI generation fails"""
        
        if doc_type == "W-2":
            return [
                "W-2 form contains employee wage and tax withholding information",
                "Federal and state tax withholdings should be verified for accuracy",
                "Document should be retained for tax filing and record-keeping purposes"
            ]
        elif doc_type.startswith("1099"):
            return [
                "1099 form reports income that may require additional tax considerations",
                "Self-employment tax implications should be reviewed if applicable",
                "Quarterly estimated tax payments may be required for future periods"
            ]
        else:
            return [
                "Tax document has been processed and key information extracted",
                "Review extracted data for accuracy and completeness",
                "Consult tax professional if clarification is needed"
            ]
    
    def _fallback_insights(self, doc_type: str) -> Dict[str, Any]:
        """Complete fallback when AI service fails"""
        
        return {
            "summary": f"Tax document ({doc_type}) processed successfully with key data extracted.",
            "insights": self._default_insights(doc_type),
            "risk_level": "low",
            "action_required": False,
            "confidence": 0.5,
            "generated_by": "fallback"
        }