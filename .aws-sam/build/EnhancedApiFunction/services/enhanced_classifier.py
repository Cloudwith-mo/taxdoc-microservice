"""
Enhanced Document Classification Service
Supports rule-based classification for all tax and financial document types
"""

import re
from typing import Dict, Any, Optional, List, Tuple

class EnhancedClassifier:
    def __init__(self):
        # Load classification keywords from config
        from config.document_config import CLASSIFICATION_KEYWORDS
        self.classification_keywords = CLASSIFICATION_KEYWORDS
        
        # Priority order for classification (more specific first)
        self.classification_priority = [
            "W-2", "1099-NEC", "1099-INT", "1099-DIV", "1099-MISC", 
            "1098-E", "1098", "1095-A", "1040",
            "Pay Stub", "Bank Statement", "Invoice", "Receipt"
        ]
    
    def classify_document(self, textract_response: Dict[str, Any]) -> Tuple[str, float]:
        """
        Classify document type with confidence score
        Returns: (document_type, confidence_score)
        """
        # Extract all text for classification
        text = self._extract_all_text(textract_response).lower()
        
        print(f"Classifying document with {len(text)} characters of text")
        
        # Try rule-based classification in priority order
        for doc_type in self.classification_priority:
            confidence = self._calculate_confidence(text, doc_type)
            if confidence > 0.7:  # High confidence threshold
                print(f"Document classified as {doc_type} with {confidence:.2f} confidence")
                return doc_type, confidence
        
        # If no high-confidence match, return best match above threshold
        best_type = "Other Document"
        best_confidence = 0.0
        
        for doc_type in self.classification_priority:
            confidence = self._calculate_confidence(text, doc_type)
            if confidence > best_confidence and confidence > 0.3:  # Minimum threshold
                best_type = doc_type
                best_confidence = confidence
        
        print(f"Document classified as {best_type} with {best_confidence:.2f} confidence")
        return best_type, best_confidence
    
    def _calculate_confidence(self, text: str, doc_type: str) -> float:
        """Calculate confidence score for a document type"""
        if doc_type not in self.classification_keywords:
            return 0.0
        
        keywords = self.classification_keywords[doc_type]
        matches = 0
        total_keywords = len(keywords)
        
        # Count keyword matches
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', text):
                matches += 1
        
        base_confidence = matches / total_keywords if total_keywords > 0 else 0
        
        # Apply specific rules for better accuracy
        if doc_type == "W-2":
            return self._classify_w2_confidence(text, base_confidence)
        elif doc_type.startswith("1099"):
            return self._classify_1099_confidence(text, doc_type, base_confidence)
        elif doc_type.startswith("1098"):
            return self._classify_1098_confidence(text, doc_type, base_confidence)
        elif doc_type.startswith("1095"):
            return self._classify_1095_confidence(text, base_confidence)
        elif doc_type == "1040":
            return self._classify_1040_confidence(text, base_confidence)
        elif doc_type == "Bank Statement":
            return self._classify_bank_statement_confidence(text, base_confidence)
        elif doc_type == "Pay Stub":
            return self._classify_paystub_confidence(text, base_confidence)
        elif doc_type == "Receipt":
            return self._classify_receipt_confidence(text, base_confidence)
        elif doc_type == "Invoice":
            return self._classify_invoice_confidence(text, base_confidence)
        
        return base_confidence
    
    def _classify_w2_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced W-2 classification with specific patterns"""
        w2_indicators = [
            r'w-?2',
            r'wage and tax statement',
            r'employee.*social security',
            r'employer.*ein',
            r'box\s*[1-6]',
            r'wages.*tips.*compensation',
            r'federal.*income.*tax.*withheld'
        ]
        
        matches = sum(1 for pattern in w2_indicators if re.search(pattern, text))
        pattern_confidence = matches / len(w2_indicators)
        
        # Boost confidence if multiple W-2 specific patterns found
        final_confidence = (base_confidence + pattern_confidence) / 2
        if matches >= 3:
            final_confidence = min(final_confidence + 0.2, 1.0)
        
        return final_confidence
    
    def _classify_1099_confidence(self, text: str, doc_type: str, base_confidence: float) -> float:
        """Enhanced 1099 series classification"""
        # Common 1099 patterns
        common_1099 = [r'1099', r'payer', r'recipient', r'tin']
        
        # Specific patterns by type
        specific_patterns = {
            "1099-NEC": [r'nonemployee.*compensation', r'1099-nec'],
            "1099-INT": [r'interest.*income', r'1099-int'],
            "1099-DIV": [r'dividend', r'1099-div'],
            "1099-MISC": [r'miscellaneous.*income', r'1099-misc']
        }
        
        common_matches = sum(1 for pattern in common_1099 if re.search(pattern, text))
        specific_matches = 0
        
        if doc_type in specific_patterns:
            specific_matches = sum(1 for pattern in specific_patterns[doc_type] if re.search(pattern, text))
        
        # Calculate weighted confidence
        common_confidence = common_matches / len(common_1099)
        specific_confidence = specific_matches / len(specific_patterns.get(doc_type, [1]))
        
        return (base_confidence + common_confidence + specific_confidence * 2) / 4
    
    def _classify_1098_confidence(self, text: str, doc_type: str, base_confidence: float) -> float:
        """Enhanced 1098 series classification"""
        common_1098 = [r'1098', r'lender', r'borrower']
        
        specific_patterns = {
            "1098-E": [r'student.*loan.*interest', r'1098-e'],
            "1098": [r'mortgage.*interest', r'points.*paid']
        }
        
        common_matches = sum(1 for pattern in common_1098 if re.search(pattern, text))
        specific_matches = 0
        
        if doc_type in specific_patterns:
            specific_matches = sum(1 for pattern in specific_patterns[doc_type] if re.search(pattern, text))
        
        common_confidence = common_matches / len(common_1098)
        specific_confidence = specific_matches / len(specific_patterns.get(doc_type, [1]))
        
        return (base_confidence + common_confidence + specific_confidence * 2) / 4
    
    def _classify_1095_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced 1095-A classification"""
        patterns = [r'1095-a', r'health.*insurance', r'marketplace', r'policy.*number', r'coverage']
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        pattern_confidence = matches / len(patterns)
        
        return (base_confidence + pattern_confidence) / 2
    
    def _classify_1040_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced 1040 classification"""
        patterns = [
            r'1040',
            r'individual.*income.*tax.*return',
            r'filing.*status',
            r'adjusted.*gross.*income',
            r'agi',
            r'total.*tax'
        ]
        
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        pattern_confidence = matches / len(patterns)
        
        return (base_confidence + pattern_confidence) / 2
    
    def _classify_bank_statement_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced bank statement classification"""
        patterns = [
            r'statement',
            r'account.*summary',
            r'beginning.*balance',
            r'ending.*balance',
            r'account.*number',
            r'statement.*period'
        ]
        
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        pattern_confidence = matches / len(patterns)
        
        # Bank statements often have multiple balance references
        if re.search(r'balance', text) and re.search(r'account', text):
            pattern_confidence = min(pattern_confidence + 0.2, 1.0)
        
        return (base_confidence + pattern_confidence) / 2
    
    def _classify_paystub_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced pay stub classification"""
        patterns = [
            r'pay.*stub',
            r'paystub',
            r'earnings.*statement',
            r'gross.*pay',
            r'net.*pay',
            r'ytd',
            r'year.*to.*date'
        ]
        
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        pattern_confidence = matches / len(patterns)
        
        return (base_confidence + pattern_confidence) / 2
    
    def _classify_receipt_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced receipt classification"""
        patterns = [
            r'receipt',
            r'thank.*you',
            r'subtotal',
            r'total.*due',
            r'tax.*amount',
            r'change.*due'
        ]
        
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        pattern_confidence = matches / len(patterns)
        
        # Receipts often have price patterns
        if re.findall(r'\$\d+\.\d{2}', text):
            pattern_confidence = min(pattern_confidence + 0.1, 1.0)
        
        return (base_confidence + pattern_confidence) / 2
    
    def _classify_invoice_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced invoice classification"""
        patterns = [
            r'invoice',
            r'bill.*to',
            r'invoice.*number',
            r'due.*date',
            r'amount.*due',
            r'payment.*terms'
        ]
        
        matches = sum(1 for pattern in patterns if re.search(pattern, text))
        pattern_confidence = matches / len(patterns)
        
        return (base_confidence + pattern_confidence) / 2
    
    def _extract_all_text(self, response: Dict[str, Any]) -> str:
        """Extract all text from Textract response"""
        text_lines = []
        
        if 'Blocks' in response:
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text_lines.append(block['Text'])
        elif 'ExpenseDocuments' in response:
            # Handle expense analysis response
            for doc in response['ExpenseDocuments']:
                for line_item in doc.get('LineItemGroups', []):
                    for item in line_item.get('LineItems', []):
                        for field in item.get('LineItemExpenseFields', []):
                            if 'ValueDetection' in field:
                                text_lines.append(field['ValueDetection']['Text'])
        
        return '\n'.join(text_lines)
    
    def get_supported_document_types(self) -> List[str]:
        """Return list of all supported document types"""
        return list(self.classification_keywords.keys())
    
    def is_tax_document(self, doc_type: str) -> bool:
        """Check if document type is a tax document"""
        tax_types = ["W-2", "1099-NEC", "1099-INT", "1099-DIV", "1099-MISC", 
                    "1098-E", "1098", "1095-A", "1040"]
        return doc_type in tax_types