import boto3
import json
from typing import Dict, Any, List
from datetime import datetime

class ChatbotService:
    """Natural language Q&A for documents"""
    
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
        self.conversation_history = []
    
    def ask_question(self, question: str, document_data: Dict[str, Any], document_text: str) -> Dict[str, Any]:
        """Answer questions about specific documents"""
        
        # Build context from document
        context = f"""Document Type: {document_data.get('DocumentType', 'Unknown')}
Extracted Fields: {json.dumps(document_data.get('ExtractedData', {}), indent=2)}
Full Text: {document_text[:3000]}

Previous conversation:
{self._format_conversation_history()}"""

        prompt = f"""You are a tax document assistant. Answer this question based on the document provided:

Question: {question}

Context:
{context}

Provide a helpful, accurate answer. If the information isn't in the document, say so clearly.

Return JSON:
{{
  "answer": "Your detailed answer",
  "confidence": 0.95,
  "source_fields": ["field1", "field2"],
  "follow_up_questions": ["suggested question 1", "suggested question 2"],
  "requires_human_review": false
}}"""

        result = self._call_claude(prompt)
        
        # Store in conversation history
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": result.get('answer', ''),
            "confidence": result.get('confidence', 0.0)
        })
        
        return result
    
    def get_cross_document_insights(self, question: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Answer questions across multiple documents"""
        
        # Summarize all documents
        doc_summaries = []
        for i, doc in enumerate(documents):
            summary = f"Document {i+1} ({doc.get('DocumentType', 'Unknown')}):\n"
            summary += json.dumps(doc.get('ExtractedData', {}), indent=2)
            doc_summaries.append(summary)
        
        context = "\n\n".join(doc_summaries)
        
        prompt = f"""Analyze these multiple tax documents and answer the question:

Question: {question}

Documents:
{context[:4000]}

Provide insights that span across documents, identify patterns, and give comprehensive analysis.

Return JSON:
{{
  "answer": "Cross-document analysis",
  "patterns_found": ["pattern1", "pattern2"],
  "document_references": [1, 2],
  "total_amounts": {{"wages": 50000, "taxes": 8000}},
  "recommendations": ["rec1", "rec2"]
}}"""

        return self._call_claude(prompt)
    
    def export_conversation(self) -> Dict[str, Any]:
        """Export conversation history"""
        
        return {
            "conversation_id": f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "total_questions": len(self.conversation_history),
            "conversation": self.conversation_history,
            "exported_at": datetime.now().isoformat()
        }
    
    def _format_conversation_history(self) -> str:
        """Format conversation for context"""
        
        if not self.conversation_history:
            return "No previous conversation"
        
        formatted = []
        for entry in self.conversation_history[-3:]:  # Last 3 exchanges
            formatted.append(f"Q: {entry['question']}")
            formatted.append(f"A: {entry['answer'][:200]}...")
        
        return "\n".join(formatted)
    
    def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Call Claude via Bedrock"""
        
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.2,
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
            print(f"Chatbot service failed: {e}")
        
        return {"answer": "I'm sorry, I couldn't process that question.", "confidence": 0.0}