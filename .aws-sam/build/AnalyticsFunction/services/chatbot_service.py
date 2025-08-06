"""
Chatbot Q&A Service
Provides intelligent Q&A about tax documents and processing results
"""
import json
import boto3
from typing import Dict, Any, List
import logging

logger = logging.getLogger()

class ChatbotService:
    """Intelligent chatbot for tax document Q&A"""
    
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        
        # Knowledge base for common tax questions
        self.tax_knowledge = {
            "w2": {
                "purpose": "W-2 forms report wages and tax withholdings for employees",
                "deadline": "Employers must provide W-2s by January 31st",
                "boxes": "W-2 has 20 boxes with different wage and tax information"
            },
            "1099": {
                "purpose": "1099 forms report various types of income for independent contractors",
                "deadline": "1099s must be provided by January 31st",
                "types": "Common types include 1099-NEC, 1099-INT, 1099-DIV, 1099-MISC"
            }
        }
    
    def chat(self, question: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user question and provide intelligent response"""
        
        try:
            # Build context from extracted document data
            context_info = self._build_context(context) if context else ""
            
            # Create comprehensive prompt
            prompt = f"""You are a helpful tax document assistant. Answer the user's question about tax documents and processing.

{context_info}

User Question: "{question}"

Provide a helpful, accurate response about tax documents, processing results, or general tax information. Be conversational but professional.

If the question is about specific extracted data, reference the document information provided.
If it's a general tax question, provide educational information.
If you're unsure, acknowledge limitations and suggest consulting a tax professional.

Response:"""

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
            answer = response_body['content'][0]['text']
            
            # Determine response type and confidence
            response_type = self._classify_response_type(question)
            confidence = self._calculate_response_confidence(question, context)
            
            return {
                "answer": answer.strip(),
                "response_type": response_type,
                "confidence": confidence,
                "context_used": bool(context),
                "suggested_actions": self._get_suggested_actions(question, context),
                "related_topics": self._get_related_topics(question)
            }
            
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return self._fallback_response(question)
    
    def get_document_summary(self, extracted_data: Dict[str, Any], doc_type: str) -> str:
        """Generate conversational summary of document"""
        
        try:
            prompt = f"""Create a friendly, conversational summary of this {doc_type} document for the user:

Extracted Data: {json.dumps(extracted_data, indent=2)}

Write a 2-3 sentence summary that:
1. Confirms what type of document was processed
2. Highlights the key financial information found
3. Uses a warm, helpful tone

Example: "I've successfully processed your W-2 form from [Company]. The document shows you earned $50,000 in wages with $6,835 in federal taxes withheld. All the key tax information has been extracted and is ready for your tax filing!"

Summary:"""

            bedrock_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(bedrock_request)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text'].strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return f"I've processed your {doc_type} document and extracted the key tax information for you!"
    
    def get_quick_answers(self) -> List[Dict[str, str]]:
        """Get common quick answer options"""
        
        return [
            {
                "question": "What is a W-2 form?",
                "category": "basics"
            },
            {
                "question": "How accurate is the extraction?",
                "category": "processing"
            },
            {
                "question": "What should I do with this data?",
                "category": "next_steps"
            },
            {
                "question": "Can I trust these numbers for tax filing?",
                "category": "accuracy"
            },
            {
                "question": "What if some information is missing?",
                "category": "troubleshooting"
            },
            {
                "question": "How do I download this data?",
                "category": "usage"
            }
        ]
    
    def _build_context(self, context: Dict[str, Any]) -> str:
        """Build context string from document data"""
        
        if not context:
            return ""
        
        doc_type = context.get('document_type', 'Unknown')
        extracted_data = context.get('extracted_data', {})
        
        # Key fields for context
        key_info = []
        
        if 'wages_income' in extracted_data:
            key_info.append(f"Wages: ${extracted_data['wages_income']:,.2f}")
        
        if 'federal_withheld' in extracted_data:
            key_info.append(f"Federal tax withheld: ${extracted_data['federal_withheld']:,.2f}")
        
        if 'employer_name' in extracted_data:
            key_info.append(f"Employer: {extracted_data['employer_name']}")
        
        if 'employee_ssn' in extracted_data:
            key_info.append("Employee SSN: [PROTECTED]")
        
        context_str = f"""
Document Context:
- Document Type: {doc_type}
- Key Information: {', '.join(key_info) if key_info else 'Basic information extracted'}
- Total Fields Extracted: {len([v for v in extracted_data.values() if v is not None])}
"""
        
        return context_str
    
    def _classify_response_type(self, question: str) -> str:
        """Classify the type of question being asked"""
        
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['what is', 'define', 'explain']):
            return "educational"
        elif any(word in question_lower for word in ['how accurate', 'confidence', 'trust']):
            return "accuracy"
        elif any(word in question_lower for word in ['what should', 'next step', 'what do']):
            return "guidance"
        elif any(word in question_lower for word in ['missing', 'wrong', 'error']):
            return "troubleshooting"
        elif any(word in question_lower for word in ['download', 'export', 'save']):
            return "usage"
        else:
            return "general"
    
    def _calculate_response_confidence(self, question: str, context: Dict[str, Any]) -> float:
        """Calculate confidence in response quality"""
        
        base_confidence = 0.8
        
        # Higher confidence for common questions
        if any(word in question.lower() for word in ['w-2', '1099', 'tax', 'wage']):
            base_confidence += 0.1
        
        # Higher confidence when we have document context
        if context and context.get('extracted_data'):
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _get_suggested_actions(self, question: str, context: Dict[str, Any]) -> List[str]:
        """Get suggested follow-up actions"""
        
        actions = []
        
        if context and context.get('extracted_data'):
            actions.append("Review extracted data for accuracy")
            actions.append("Download data for tax filing")
        
        if 'accuracy' in question.lower() or 'trust' in question.lower():
            actions.append("Compare with original document")
            actions.append("Consult tax professional if needed")
        
        if 'missing' in question.lower():
            actions.append("Try re-uploading with better image quality")
            actions.append("Manually enter missing information")
        
        return actions[:3]  # Limit to 3 suggestions
    
    def _get_related_topics(self, question: str) -> List[str]:
        """Get related topics user might be interested in"""
        
        topics = []
        question_lower = question.lower()
        
        if 'w-2' in question_lower:
            topics.extend(["1099 forms", "Tax withholdings", "Employer reporting"])
        elif '1099' in question_lower:
            topics.extend(["W-2 forms", "Independent contractor taxes", "Self-employment"])
        elif 'tax' in question_lower:
            topics.extend(["Tax filing deadlines", "Deductions", "Tax software"])
        
        return topics[:3]
    
    def _fallback_response(self, question: str) -> Dict[str, Any]:
        """Fallback response when chatbot fails"""
        
        return {
            "answer": "I'm sorry, I'm having trouble processing your question right now. Please try rephrasing your question or contact support for assistance with tax document processing.",
            "response_type": "error",
            "confidence": 0.0,
            "context_used": False,
            "suggested_actions": [
                "Try rephrasing your question",
                "Check our FAQ section",
                "Contact support for help"
            ],
            "related_topics": ["Tax basics", "Document processing", "Support"]
        }