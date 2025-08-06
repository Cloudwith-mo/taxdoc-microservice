from typing import Dict, Any, Tuple

class TaxFormClassifier:
    """Simple keyword-based classifier for tax forms"""
    
    def __init__(self):
        self.form_keywords = {
            'W-2': ['w-2', 'wage and tax statement', 'employee social security', 'employer ein'],
            '1099-NEC': ['1099-nec', 'nonemployee compensation'],
            '1099-INT': ['1099-int', 'interest income'],
            '1099-DIV': ['1099-div', 'dividends'],
            '1099-MISC': ['1099-misc', 'miscellaneous income']
        }
    
    def classify_form(self, textract_response: Dict[str, Any]) -> Tuple[str, float]:
        """Classify form type based on text content"""
        
        # Extract all text from Textract response
        text_content = self._extract_text(textract_response).lower()
        
        # Score each form type
        scores = {}
        for form_type, keywords in self.form_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_content)
            if score > 0:
                scores[form_type] = score / len(keywords)
        
        if not scores:
            return 'Unknown', 0.0
        
        # Return highest scoring form type
        best_form = max(scores.keys(), key=lambda k: scores[k])
        confidence = scores[best_form]
        
        return best_form, confidence
    
    def _extract_text(self, textract_response: Dict[str, Any]) -> str:
        """Extract plain text from Textract response"""
        
        text_lines = []
        for block in textract_response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_lines.append(block.get('Text', ''))
        
        return ' '.join(text_lines)