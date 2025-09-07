import json
import re
from typing import Dict, Any, List, Tuple, Optional
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .template_service import TemplateService

class AdvancedTemplateMatcher:
    """Advanced template matching using multiple algorithms"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.confidence_threshold = 0.75
        self.template_service = TemplateService()
        
    def find_best_template(self, document_text: str, document_type: str) -> Tuple[Optional[Dict], float]:
        """Find the best matching template using multiple algorithms"""
        
        available_templates = self.template_service.list_templates(document_type)
        
        if not available_templates:
            return None, 0.0
        
        scores = []
        
        for template in available_templates:
            keyword_score = self._keyword_matching(document_text, template)
            structure_score = self._structure_matching(document_text, template)
            semantic_score = self._semantic_matching(document_text, template)
            layout_score = self._layout_matching(document_text, template)
            
            combined_score = (
                keyword_score * 0.3 +
                structure_score * 0.25 +
                semantic_score * 0.25 +
                layout_score * 0.2
            )
            
            scores.append((template, combined_score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        best_template, best_score = scores[0]
        
        if best_score >= self.confidence_threshold:
            return best_template, best_score
        else:
            return None, best_score
    
    def _keyword_matching(self, document_text: str, template: Dict[str, Any]) -> float:
        """Enhanced keyword matching with weighted importance"""
        
        template_data = template.get('TemplateData', {})
        keywords = template_data.get('keywords', [])
        
        if not keywords:
            return 0.0
        
        text_lower = document_text.lower()
        weighted_score = 0.0
        total_weight = 0.0
        
        for keyword_data in keywords:
            if isinstance(keyword_data, dict):
                keyword = keyword_data.get('term', '')
                weight = keyword_data.get('weight', 1.0)
                required = keyword_data.get('required', False)
            else:
                keyword = str(keyword_data)
                weight = 1.0
                required = False
            
            if keyword.lower() in text_lower:
                weighted_score += weight
                if required:
                    weighted_score += weight * 0.5
            elif required:
                return 0.0
            
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _structure_matching(self, document_text: str, template: Dict[str, Any]) -> float:
        """Enhanced structure matching with field positioning"""
        
        template_data = template.get('TemplateData', {})
        structure_patterns = template_data.get('structure_patterns', [])
        
        if not structure_patterns:
            return 0.0
        
        matches = 0
        total_patterns = len(structure_patterns)
        
        for pattern_data in structure_patterns:
            if isinstance(pattern_data, dict):
                pattern = pattern_data.get('pattern', '')
                weight = pattern_data.get('weight', 1.0)
                position = pattern_data.get('expected_position', 'anywhere')
            else:
                pattern = str(pattern_data)
                weight = 1.0
                position = 'anywhere'
            
            if self._check_pattern_with_position(document_text, pattern, position):
                matches += weight
        
        return matches / total_patterns
    
    def _semantic_matching(self, document_text: str, template: Dict[str, Any]) -> float:
        """Enhanced semantic matching with context awareness"""
        
        template_data = template.get('TemplateData', {})
        sample_texts = template_data.get('sample_texts', [])
        
        if not sample_texts:
            return 0.0
        
        max_similarity = 0.0
        
        for sample_text in sample_texts:
            try:
                texts = [document_text, sample_text]
                tfidf_matrix = self.vectorizer.fit_transform(texts)
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                max_similarity = max(max_similarity, float(similarity))
            except Exception as e:
                print(f"Semantic matching error: {e}")
                continue
        
        return max_similarity
    
    def _layout_matching(self, document_text: str, template: Dict[str, Any]) -> float:
        """Match document layout patterns"""
        
        template_data = template.get('TemplateData', {})
        layout_patterns = template_data.get('layout_patterns', {})
        
        if not layout_patterns:
            return 0.5
        
        score = 0.0
        total_checks = 0
        
        if 'expected_line_count' in layout_patterns:
            doc_lines = len(document_text.split('\n'))
            expected_range = layout_patterns['expected_line_count']
            if isinstance(expected_range, dict):
                min_lines = expected_range.get('min', 0)
                max_lines = expected_range.get('max', float('inf'))
                if min_lines <= doc_lines <= max_lines:
                    score += 1.0
            total_checks += 1
        
        if 'field_distribution' in layout_patterns:
            field_dist = layout_patterns['field_distribution']
            for section, expected_fields in field_dist.items():
                section_text = self._extract_section(document_text, section)
                found_fields = sum(1 for field in expected_fields if field.lower() in section_text.lower())
                if expected_fields:
                    score += found_fields / len(expected_fields)
                total_checks += 1
        
        return score / total_checks if total_checks > 0 else 0.5
    
    def _check_pattern_with_position(self, text: str, pattern: str, position: str) -> bool:
        """Check pattern with position awareness"""
        
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return False
        
        if position == 'anywhere':
            return True
        elif position == 'top':
            match_pos = match.start()
            return match_pos < len(text) * 0.2
        elif position == 'bottom':
            match_pos = match.start()
            return match_pos > len(text) * 0.8
        elif position == 'middle':
            match_pos = match.start()
            return 0.2 * len(text) < match_pos < 0.8 * len(text)
        
        return True
    
    def _extract_section(self, text: str, section: str) -> str:
        """Extract specific section from document"""
        
        lines = text.split('\n')
        
        if section == 'header':
            return '\n'.join(lines[:min(5, len(lines))])
        elif section == 'footer':
            return '\n'.join(lines[-min(5, len(lines)):])
        elif section == 'middle':
            start = len(lines) // 4
            end = 3 * len(lines) // 4
            return '\n'.join(lines[start:end])
        else:
            return text
    
    def match_field_patterns(self, document_text: str, field_patterns: Dict[str, str]) -> Dict[str, Any]:
        """Match specific field patterns in document with confidence scoring"""
        
        matches = {}
        
        for field_name, pattern_data in field_patterns.items():
            if isinstance(pattern_data, dict):
                pattern = pattern_data.get('pattern', '')
                confidence_boost = pattern_data.get('confidence_boost', 0.0)
                validation_func = pattern_data.get('validation')
            else:
                pattern = str(pattern_data)
                confidence_boost = 0.0
                validation_func = None
            
            match = re.search(pattern, document_text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                
                if validation_func and not validation_func(value):
                    continue
                
                base_confidence = 0.8
                final_confidence = min(0.95, base_confidence + confidence_boost)
                
                matches[field_name] = {
                    'value': value.strip(),
                    'confidence': final_confidence,
                    'source': 'template_pattern',
                    'pattern_used': pattern
                }
        
        return matches
    
    def create_template_from_document(self, document_text: str, document_type: str, field_mappings: Dict[str, str]) -> Dict[str, Any]:
        """Create a new template based on a document"""
        
        words = re.findall(r'\b\w+\b', document_text.lower())
        word_freq = {}
        for word in words:
            if len(word) > 3:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        
        structure_patterns = []
        for field_name, pattern in field_mappings.items():
            structure_patterns.append({
                'pattern': pattern,
                'field': field_name,
                'weight': 1.0
            })
        
        lines = document_text.split('\n')
        layout_patterns = {
            'expected_line_count': {
                'min': max(1, len(lines) - 5),
                'max': len(lines) + 5
            },
            'field_distribution': {
                'header': [kw[0] for kw in top_keywords[:5]],
                'middle': [kw[0] for kw in top_keywords[5:15]],
                'footer': [kw[0] for kw in top_keywords[15:20]]
            }
        }
        
        template_data = {
            'keywords': [{'term': kw[0], 'weight': min(kw[1] / 10, 2.0)} for kw in top_keywords],
            'structure_patterns': structure_patterns,
            'sample_texts': [document_text[:1000]],
            'layout_patterns': layout_patterns,
            'field_mappings': field_mappings,
            'validation_rules': {
                'required_elements': [{'pattern': pattern, 'name': field} for field, pattern in field_mappings.items()],
                'min_confidence': 0.7
            }
        }
        
        return template_data