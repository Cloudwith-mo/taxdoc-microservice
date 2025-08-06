"""
Amazon Comprehend Insights Service
Provides AI-powered document analysis and insights
"""

import boto3
import json
from typing import Dict, Any, List, Optional

class ComprehendInsightsService:
    def __init__(self):
        self.comprehend = boto3.client('comprehend', region_name='us-east-1')
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.claude_model_id = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
    
    def generate_document_insights(self, document_text: str, document_type: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive AI insights for a document"""
        
        if not document_text or len(document_text.strip()) < 50:
            return self._create_empty_insights()
        
        # Truncate text for API limits
        text = document_text[:4500]  # Stay under 5000 char limit
        
        insights = {
            'document_summary': self._generate_summary(text, document_type),
            'sentiment_analysis': self._analyze_sentiment(text),
            'key_phrases': self._extract_key_phrases(text),
            'entities': self._extract_entities(text),
            'language_detection': self._detect_language(text),
            'document_classification': self._classify_document_content(text),
            'business_insights': self._generate_business_insights(text, document_type, extracted_data)
        }
        
        return insights
    
    def _generate_summary(self, text: str, document_type: str) -> Dict[str, Any]:
        """Generate document summary using Claude"""
        try:
            prompt = f"""
Analyze this {document_type} document and provide a concise summary.

Document text:
{text}

Provide a 2-3 sentence summary focusing on:
- Document purpose and key information
- Important dates, amounts, or parties involved
- Any notable details or requirements

Return only the summary text, no additional formatting.
"""
            
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 200,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            summary = response_body['content'][0]['text'].strip()
            
            return {
                'summary': summary,
                'confidence': 0.9,
                'source': 'claude_ai'
            }
            
        except Exception as e:
            return {
                'summary': f'Unable to generate summary for this {document_type}.',
                'confidence': 0.0,
                'source': 'fallback',
                'error': str(e)
            }
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze document sentiment using Comprehend"""
        try:
            response = self.comprehend.detect_sentiment(
                Text=text,
                LanguageCode='en'
            )
            
            return {
                'sentiment': response['Sentiment'],
                'confidence': response['SentimentScore'][response['Sentiment']],
                'scores': response['SentimentScore']
            }
            
        except Exception as e:
            return {
                'sentiment': 'NEUTRAL',
                'confidence': 0.0,
                'scores': {'POSITIVE': 0.0, 'NEGATIVE': 0.0, 'NEUTRAL': 1.0, 'MIXED': 0.0},
                'error': str(e)
            }
    
    def _extract_key_phrases(self, text: str) -> Dict[str, Any]:
        """Extract key phrases using Comprehend"""
        try:
            response = self.comprehend.detect_key_phrases(
                Text=text,
                LanguageCode='en'
            )
            
            # Sort by confidence and take top 10
            phrases = sorted(
                response['KeyPhrases'], 
                key=lambda x: x['Score'], 
                reverse=True
            )[:10]
            
            return {
                'phrases': [
                    {
                        'text': phrase['Text'],
                        'confidence': phrase['Score']
                    }
                    for phrase in phrases
                ],
                'total_found': len(response['KeyPhrases'])
            }
            
        except Exception as e:
            return {
                'phrases': [],
                'total_found': 0,
                'error': str(e)
            }
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities using Comprehend"""
        try:
            response = self.comprehend.detect_entities(
                Text=text,
                LanguageCode='en'
            )
            
            # Group entities by type
            entities_by_type = {}
            for entity in response['Entities']:
                entity_type = entity['Type']
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                
                entities_by_type[entity_type].append({
                    'text': entity['Text'],
                    'confidence': entity['Score']
                })
            
            # Sort each type by confidence
            for entity_type in entities_by_type:
                entities_by_type[entity_type] = sorted(
                    entities_by_type[entity_type],
                    key=lambda x: x['confidence'],
                    reverse=True
                )[:5]  # Top 5 per type
            
            return {
                'entities_by_type': entities_by_type,
                'total_entities': len(response['Entities'])
            }
            
        except Exception as e:
            return {
                'entities_by_type': {},
                'total_entities': 0,
                'error': str(e)
            }
    
    def _detect_language(self, text: str) -> Dict[str, Any]:
        """Detect document language using Comprehend"""
        try:
            response = self.comprehend.detect_dominant_language(Text=text)
            
            if response['Languages']:
                dominant = response['Languages'][0]
                return {
                    'language': dominant['LanguageCode'],
                    'confidence': dominant['Score'],
                    'all_languages': response['Languages'][:3]  # Top 3
                }
            
            return {
                'language': 'en',
                'confidence': 0.5,
                'all_languages': []
            }
            
        except Exception as e:
            return {
                'language': 'en',
                'confidence': 0.0,
                'all_languages': [],
                'error': str(e)
            }
    
    def _classify_document_content(self, text: str) -> Dict[str, Any]:
        """Classify document content themes"""
        try:
            # Use key phrases to infer document themes
            phrases_response = self.comprehend.detect_key_phrases(
                Text=text,
                LanguageCode='en'
            )
            
            # Simple theme classification based on key phrases
            themes = {
                'financial': 0,
                'legal': 0,
                'business': 0,
                'personal': 0,
                'technical': 0
            }
            
            financial_terms = ['tax', 'income', 'wage', 'payment', 'amount', 'dollar', 'compensation']
            legal_terms = ['agreement', 'contract', 'terms', 'conditions', 'liability', 'rights']
            business_terms = ['company', 'business', 'invoice', 'receipt', 'service', 'product']
            personal_terms = ['name', 'address', 'phone', 'email', 'personal', 'individual']
            technical_terms = ['system', 'software', 'technical', 'specification', 'requirement']
            
            for phrase in phrases_response['KeyPhrases']:
                phrase_text = phrase['Text'].lower()
                confidence = phrase['Score']
                
                if any(term in phrase_text for term in financial_terms):
                    themes['financial'] += confidence
                if any(term in phrase_text for term in legal_terms):
                    themes['legal'] += confidence
                if any(term in phrase_text for term in business_terms):
                    themes['business'] += confidence
                if any(term in phrase_text for term in personal_terms):
                    themes['personal'] += confidence
                if any(term in phrase_text for term in technical_terms):
                    themes['technical'] += confidence
            
            # Normalize scores
            max_score = max(themes.values()) if themes.values() else 1
            if max_score > 0:
                themes = {k: v/max_score for k, v in themes.items()}
            
            # Get dominant theme
            dominant_theme = max(themes.items(), key=lambda x: x[1])
            
            return {
                'dominant_theme': dominant_theme[0],
                'confidence': dominant_theme[1],
                'all_themes': themes
            }
            
        except Exception as e:
            return {
                'dominant_theme': 'business',
                'confidence': 0.0,
                'all_themes': {},
                'error': str(e)
            }
    
    def _generate_business_insights(self, text: str, document_type: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business-specific insights using Claude"""
        try:
            # Create context from extracted data
            data_summary = []
            for key, value in extracted_data.items():
                if value is not None and str(value).strip():
                    data_summary.append(f"{key}: {value}")
            
            data_context = "\n".join(data_summary[:10])  # Top 10 fields
            
            prompt = f"""
Analyze this {document_type} and provide business insights.

Extracted Data:
{data_context}

Document Text Sample:
{text[:1000]}

Provide insights in JSON format:
{{
  "key_insights": ["insight1", "insight2", "insight3"],
  "financial_highlights": ["highlight1", "highlight2"],
  "action_items": ["action1", "action2"],
  "risk_factors": ["risk1", "risk2"],
  "compliance_notes": ["note1", "note2"]
}}

Focus on practical business value and actionable information.
"""
            
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            llm_output = response_body['content'][0]['text']
            
            # Parse JSON from response
            json_start = llm_output.find('{')
            json_end = llm_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_output[json_start:json_end]
                insights = json.loads(json_str)
                insights['confidence'] = 0.8
                insights['source'] = 'claude_ai'
                return insights
            
            return self._create_fallback_business_insights(document_type)
            
        except Exception as e:
            return self._create_fallback_business_insights(document_type, str(e))
    
    def _create_fallback_business_insights(self, document_type: str, error: str = None) -> Dict[str, Any]:
        """Create fallback business insights when AI analysis fails"""
        return {
            'key_insights': [f'This {document_type} contains structured business information'],
            'financial_highlights': ['Review extracted financial data for accuracy'],
            'action_items': ['Verify all extracted information', 'Store document securely'],
            'risk_factors': ['Ensure data accuracy before business use'],
            'compliance_notes': ['Follow document retention policies'],
            'confidence': 0.3,
            'source': 'fallback',
            'error': error
        }
    
    def _create_empty_insights(self) -> Dict[str, Any]:
        """Create empty insights structure when no text is available"""
        return {
            'document_summary': {
                'summary': 'Insufficient text for analysis',
                'confidence': 0.0,
                'source': 'none'
            },
            'sentiment_analysis': {
                'sentiment': 'NEUTRAL',
                'confidence': 0.0,
                'scores': {'POSITIVE': 0.0, 'NEGATIVE': 0.0, 'NEUTRAL': 1.0, 'MIXED': 0.0}
            },
            'key_phrases': {'phrases': [], 'total_found': 0},
            'entities': {'entities_by_type': {}, 'total_entities': 0},
            'language_detection': {'language': 'en', 'confidence': 0.0, 'all_languages': []},
            'document_classification': {'dominant_theme': 'unknown', 'confidence': 0.0, 'all_themes': {}},
            'business_insights': {
                'key_insights': ['Document requires manual review'],
                'financial_highlights': [],
                'action_items': ['Manual document analysis needed'],
                'risk_factors': [],
                'compliance_notes': [],
                'confidence': 0.0,
                'source': 'none'
            }
        }