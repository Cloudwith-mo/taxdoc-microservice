"""
Template Matcher Service
Implements intelligent document template matching with similarity scoring
Routes documents to deterministic extractors or LLM fallback
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from config.document_config import CLASSIFICATION_KEYWORDS, DOCUMENT_CONFIGS

class TemplateMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            lowercase=True
        )
        self.template_vectors = {}
        self.similarity_threshold = 0.3
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize template vectors from known document types"""
        template_texts = []
        template_names = []
        
        for doc_type, keywords in CLASSIFICATION_KEYWORDS.items():
            # Create representative text for each template
            template_text = " ".join(keywords)
            template_texts.append(template_text)
            template_names.append(doc_type)
        
        if template_texts:
            # Fit vectorizer and create template vectors
            self.vectorizer.fit(template_texts)
            vectors = self.vectorizer.transform(template_texts)
            
            for i, name in enumerate(template_names):
                self.template_vectors[name] = vectors[i]
    
    def match_template(self, document_text: str) -> Dict[str, Any]:
        """
        Match document against known templates
        Returns: {template_name, confidence, should_use_deterministic, extraction_config}
        """
        if not document_text.strip():
            return self._create_no_match_result()
        
        # Clean and prepare text
        cleaned_text = self._clean_text(document_text)
        
        # Rule-based matching (fast path)
        rule_match = self._rule_based_matching(cleaned_text)
        if rule_match['confidence'] > 0.8:
            return rule_match
        
        # Vector similarity matching
        similarity_match = self._similarity_matching(cleaned_text)
        
        # Return best match
        if rule_match['confidence'] > similarity_match['confidence']:
            return rule_match
        else:
            return similarity_match
    
    def _rule_based_matching(self, text: str) -> Dict[str, Any]:
        """Fast rule-based template matching using keywords"""
        text_lower = text.lower()
        best_match = None
        best_score = 0.0
        
        for doc_type, keywords in CLASSIFICATION_KEYWORDS.items():
            score = 0.0
            matched_keywords = 0
            
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    # Weight longer keywords more heavily
                    weight = len(keyword.split()) * 0.3 + 0.7
                    score += weight
                    matched_keywords += 1
            
            # Normalize score by number of keywords
            if len(keywords) > 0:
                normalized_score = (score / len(keywords)) * (matched_keywords / len(keywords))
                
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_match = doc_type
        
        if best_match and best_score > 0.3:
            return {
                'template_name': best_match,
                'confidence': min(best_score, 0.95),
                'should_use_deterministic': best_score > 0.6,
                'extraction_config': DOCUMENT_CONFIGS.get(best_match, {}),
                'matching_method': 'rule_based'
            }
        
        return self._create_no_match_result()
    
    def _similarity_matching(self, text: str) -> Dict[str, Any]:
        """Vector similarity-based template matching"""
        if not self.template_vectors:
            return self._create_no_match_result()
        
        try:
            # Transform document text to vector
            doc_vector = self.vectorizer.transform([text])
            
            best_match = None
            best_similarity = 0.0
            
            # Compare with all template vectors
            for template_name, template_vector in self.template_vectors.items():
                similarity = cosine_similarity(doc_vector, template_vector)[0][0]
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = template_name
            
            if best_match and best_similarity > self.similarity_threshold:
                return {
                    'template_name': best_match,
                    'confidence': min(best_similarity * 1.2, 0.9),  # Boost similarity scores
                    'should_use_deterministic': best_similarity > 0.5,
                    'extraction_config': DOCUMENT_CONFIGS.get(best_match, {}),
                    'matching_method': 'similarity'
                }
        
        except Exception as e:
            print(f"Similarity matching failed: {e}")
        
        return self._create_no_match_result()
    
    def _clean_text(self, text: str) -> str:
        """Clean text for better matching"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        return text.strip()
    
    def _create_no_match_result(self) -> Dict[str, Any]:
        """Create result for when no template matches"""
        return {
            'template_name': 'Unknown',
            'confidence': 0.0,
            'should_use_deterministic': False,
            'extraction_config': {},
            'matching_method': 'none'
        }
    
    def get_extraction_strategy(self, match_result: Dict[str, Any]) -> str:
        """
        Determine extraction strategy based on template match
        Returns: 'deterministic', 'llm_primary', or 'llm_only'
        """
        if match_result['should_use_deterministic'] and match_result['extraction_config']:
            return 'deterministic'
        elif match_result['confidence'] > 0.2:
            return 'llm_primary'
        else:
            return 'llm_only'
    
    def add_custom_template(self, template_name: str, keywords: List[str], config: Dict[str, Any]):
        """Add a custom template for specific document types"""
        CLASSIFICATION_KEYWORDS[template_name] = keywords
        DOCUMENT_CONFIGS[template_name] = config
        
        # Re-initialize templates to include the new one
        self._initialize_templates()
    
    def get_confidence_explanation(self, match_result: Dict[str, Any]) -> str:
        """Get human-readable explanation of matching confidence"""
        confidence = match_result['confidence']
        method = match_result['matching_method']
        
        if confidence > 0.8:
            return f"High confidence match using {method} - document type clearly identified"
        elif confidence > 0.5:
            return f"Medium confidence match using {method} - likely correct document type"
        elif confidence > 0.2:
            return f"Low confidence match using {method} - document type uncertain"
        else:
            return "No template match found - will use general extraction"