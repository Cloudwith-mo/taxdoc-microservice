"""
Universal Sentiment Analysis Service
Analyzes sentiment of extracted document data and user interactions
"""
import json
import boto3
from typing import Dict, Any
import logging

logger = logging.getLogger()

class SentimentService:
    """Universal sentiment analysis for document processing"""
    
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    def analyze_document_sentiment(self, extracted_data: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
        """Analyze sentiment of document processing experience"""
        
        try:
            # Determine sentiment based on extraction success and data quality
            field_count = len([v for v in extracted_data.values() if v is not None])
            confidence_scores = extracted_data.get('confidence_scores', {})
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0.85
            
            # Generate sentiment analysis
            sentiment_data = {
                "overall_sentiment": self._determine_overall_sentiment(field_count, avg_confidence, doc_type),
                "confidence_sentiment": self._analyze_confidence_sentiment(avg_confidence),
                "processing_sentiment": self._analyze_processing_sentiment(extracted_data),
                "user_experience_score": self._calculate_ux_score(field_count, avg_confidence),
                "emotional_indicators": self._get_emotional_indicators(doc_type, field_count),
                "sentiment_summary": self._generate_sentiment_summary(doc_type, field_count, avg_confidence)
            }
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return self._fallback_sentiment()
    
    def analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of arbitrary text using Claude"""
        
        prompt = f"""Analyze the sentiment of this text and provide a comprehensive sentiment analysis:

Text: "{text}"

Provide analysis in this JSON format:
{{
    "sentiment": "positive/negative/neutral",
    "confidence": 0.95,
    "emotions": ["happy", "satisfied", "concerned"],
    "tone": "professional/casual/frustrated",
    "key_phrases": ["great experience", "very helpful"],
    "sentiment_score": 0.8,
    "analysis": "Brief explanation of the sentiment"
}}"""

        try:
            bedrock_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(bedrock_request)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
                
        except Exception as e:
            logger.error(f"Text sentiment analysis failed: {e}")
        
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "emotions": ["neutral"],
            "tone": "neutral",
            "analysis": "Unable to analyze sentiment"
        }
    
    def _determine_overall_sentiment(self, field_count: int, confidence: float, doc_type: str) -> str:
        """Determine overall sentiment based on extraction results"""
        
        if field_count >= 15 and confidence > 0.9:
            return "very_positive"
        elif field_count >= 10 and confidence > 0.8:
            return "positive"
        elif field_count >= 5 and confidence > 0.7:
            return "neutral"
        elif field_count >= 3:
            return "slightly_negative"
        else:
            return "negative"
    
    def _analyze_confidence_sentiment(self, confidence: float) -> Dict[str, Any]:
        """Analyze sentiment based on confidence scores"""
        
        if confidence > 0.95:
            return {
                "sentiment": "excellent",
                "message": "Extremely high confidence in extraction accuracy",
                "emoji": "🎯"
            }
        elif confidence > 0.85:
            return {
                "sentiment": "good",
                "message": "High confidence in extraction results",
                "emoji": "✅"
            }
        elif confidence > 0.7:
            return {
                "sentiment": "moderate",
                "message": "Moderate confidence, some fields may need review",
                "emoji": "⚠️"
            }
        else:
            return {
                "sentiment": "low",
                "message": "Low confidence, manual review recommended",
                "emoji": "❌"
            }
    
    def _analyze_processing_sentiment(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment of processing pipeline"""
        
        layers_used = extracted_data.get('layers_used', [])
        
        if 'textract_queries' in layers_used and len(layers_used) == 1:
            return {
                "sentiment": "optimal",
                "message": "Perfect extraction using primary layer only",
                "efficiency": "high"
            }
        elif 'bedrock_claude' in layers_used:
            return {
                "sentiment": "good",
                "message": "AI assistance provided comprehensive extraction",
                "efficiency": "medium"
            }
        elif 'regex_patterns' in layers_used:
            return {
                "sentiment": "acceptable",
                "message": "Fallback patterns ensured data capture",
                "efficiency": "low"
            }
        else:
            return {
                "sentiment": "unknown",
                "message": "Processing method unclear",
                "efficiency": "unknown"
            }
    
    def _calculate_ux_score(self, field_count: int, confidence: float) -> float:
        """Calculate user experience score (0-1)"""
        
        field_score = min(field_count / 20, 1.0)  # Normalize to 20 fields max
        confidence_score = confidence
        
        return round((field_score * 0.6 + confidence_score * 0.4), 2)
    
    def _get_emotional_indicators(self, doc_type: str, field_count: int) -> list:
        """Get emotional indicators based on processing results"""
        
        emotions = []
        
        if field_count >= 15:
            emotions.extend(["satisfied", "confident", "pleased"])
        elif field_count >= 10:
            emotions.extend(["content", "optimistic"])
        elif field_count >= 5:
            emotions.extend(["neutral", "cautious"])
        else:
            emotions.extend(["concerned", "disappointed"])
        
        if doc_type == "W-2":
            emotions.append("tax_season_ready")
        elif doc_type.startswith("1099"):
            emotions.append("business_focused")
        
        return emotions
    
    def _generate_sentiment_summary(self, doc_type: str, field_count: int, confidence: float) -> str:
        """Generate human-readable sentiment summary"""
        
        if field_count >= 15 and confidence > 0.9:
            return f"Excellent processing of {doc_type}! All key information extracted with high confidence. Users should feel very satisfied with these comprehensive results."
        elif field_count >= 10:
            return f"Good processing of {doc_type}. Most important fields captured successfully. Users likely feel positive about the extraction quality."
        elif field_count >= 5:
            return f"Moderate processing of {doc_type}. Basic information extracted but some details may be missing. Users might have mixed feelings about completeness."
        else:
            return f"Limited processing of {doc_type}. Only basic information captured. Users may feel disappointed with the extraction results."
    
    def _fallback_sentiment(self) -> Dict[str, Any]:
        """Fallback sentiment when analysis fails"""
        
        return {
            "overall_sentiment": "neutral",
            "confidence_sentiment": {
                "sentiment": "unknown",
                "message": "Unable to analyze confidence",
                "emoji": "❓"
            },
            "processing_sentiment": {
                "sentiment": "unknown",
                "message": "Processing analysis unavailable",
                "efficiency": "unknown"
            },
            "user_experience_score": 0.5,
            "emotional_indicators": ["neutral"],
            "sentiment_summary": "Sentiment analysis temporarily unavailable."
        }