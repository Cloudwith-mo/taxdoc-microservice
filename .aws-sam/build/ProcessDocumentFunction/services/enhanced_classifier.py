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
            final_confidence = min(final_confidence + 0.2, 1.0)\n        \n        return final_confidence
    
    def _classify_1099_confidence(self, text: str, doc_type: str, base_confidence: float) -> float:
        """Enhanced 1099 series classification"""
        # Common 1099 patterns\n        common_1099 = [r'1099', r'payer', r'recipient', r'tin']\n        \n        # Specific patterns by type\n        specific_patterns = {\n            \"1099-NEC\": [r'nonemployee.*compensation', r'1099-nec'],\n            \"1099-INT\": [r'interest.*income', r'1099-int'],\n            \"1099-DIV\": [r'dividend', r'1099-div'],\n            \"1099-MISC\": [r'miscellaneous.*income', r'1099-misc']\n        }\n        \n        common_matches = sum(1 for pattern in common_1099 if re.search(pattern, text))\n        specific_matches = 0\n        \n        if doc_type in specific_patterns:\n            specific_matches = sum(1 for pattern in specific_patterns[doc_type] if re.search(pattern, text))\n        \n        # Calculate weighted confidence\n        common_confidence = common_matches / len(common_1099)\n        specific_confidence = specific_matches / len(specific_patterns.get(doc_type, [1]))\n        \n        return (base_confidence + common_confidence + specific_confidence * 2) / 4
    
    def _classify_1098_confidence(self, text: str, doc_type: str, base_confidence: float) -> float:
        """Enhanced 1098 series classification"""
        common_1098 = [r'1098', r'lender', r'borrower']\n        \n        specific_patterns = {\n            \"1098-E\": [r'student.*loan.*interest', r'1098-e'],\n            \"1098\": [r'mortgage.*interest', r'points.*paid']\n        }\n        \n        common_matches = sum(1 for pattern in common_1098 if re.search(pattern, text))\n        specific_matches = 0\n        \n        if doc_type in specific_patterns:\n            specific_matches = sum(1 for pattern in specific_patterns[doc_type] if re.search(pattern, text))\n        \n        common_confidence = common_matches / len(common_1098)\n        specific_confidence = specific_matches / len(specific_patterns.get(doc_type, [1]))\n        \n        return (base_confidence + common_confidence + specific_confidence * 2) / 4
    
    def _classify_1095_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced 1095-A classification"""
        patterns = [r'1095-a', r'health.*insurance', r'marketplace', r'policy.*number', r'coverage']\n        matches = sum(1 for pattern in patterns if re.search(pattern, text))\n        pattern_confidence = matches / len(patterns)\n        \n        return (base_confidence + pattern_confidence) / 2
    
    def _classify_1040_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced 1040 classification"""
n        patterns = [\n            r'1040',\n            r'individual.*income.*tax.*return',\n            r'filing.*status',\n            r'adjusted.*gross.*income',\n            r'agi',\n            r'total.*tax'\n        ]\n        \n        matches = sum(1 for pattern in patterns if re.search(pattern, text))\n        pattern_confidence = matches / len(patterns)\n        \n        return (base_confidence + pattern_confidence) / 2
    
    def _classify_bank_statement_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced bank statement classification"""
        patterns = [\n            r'statement',\n            r'account.*summary',\n            r'beginning.*balance',\n            r'ending.*balance',\n            r'account.*number',\n            r'statement.*period'\n        ]\n        \n        matches = sum(1 for pattern in patterns if re.search(pattern, text))\n        pattern_confidence = matches / len(patterns)\n        \n        # Bank statements often have multiple balance references\n        if re.search(r'balance', text) and re.search(r'account', text):\n            pattern_confidence = min(pattern_confidence + 0.2, 1.0)\n        \n        return (base_confidence + pattern_confidence) / 2
    
    def _classify_paystub_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced pay stub classification"""
        patterns = [\n            r'pay.*stub',\n            r'paystub',\n            r'earnings.*statement',\n            r'gross.*pay',\n            r'net.*pay',\n            r'ytd',\n            r'year.*to.*date'\n        ]\n        \n        matches = sum(1 for pattern in patterns if re.search(pattern, text))\n        pattern_confidence = matches / len(patterns)\n        \n        return (base_confidence + pattern_confidence) / 2
    
    def _classify_receipt_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced receipt classification"""
        patterns = [\n            r'receipt',\n            r'thank.*you',\n            r'subtotal',\n            r'total.*due',\n            r'tax.*amount',\n            r'change.*due'\n        ]\n        \n        matches = sum(1 for pattern in patterns if re.search(pattern, text))\n        pattern_confidence = matches / len(patterns)\n        \n        # Receipts often have price patterns\n        if re.findall(r'\\$\\d+\\.\\d{2}', text):\n            pattern_confidence = min(pattern_confidence + 0.1, 1.0)\n        \n        return (base_confidence + pattern_confidence) / 2
    
    def _classify_invoice_confidence(self, text: str, base_confidence: float) -> float:
        """Enhanced invoice classification"""
        patterns = [\n            r'invoice',\n            r'bill.*to',\n            r'invoice.*number',\n            r'due.*date',\n            r'amount.*due',\n            r'payment.*terms'\n        ]\n        \n        matches = sum(1 for pattern in patterns if re.search(pattern, text))\n        pattern_confidence = matches / len(patterns)\n        \n        return (base_confidence + pattern_confidence) / 2
    
    def _extract_all_text(self, response: Dict[str, Any]) -> str:
        """Extract all text from Textract response"""
        text_lines = []\n        \n        if 'Blocks' in response:\n            for block in response['Blocks']:\n                if block['BlockType'] == 'LINE':\n                    text_lines.append(block['Text'])\n        elif 'ExpenseDocuments' in response:\n            # Handle expense analysis response\n            for doc in response['ExpenseDocuments']:\n                for line_item in doc.get('LineItemGroups', []):\n                    for item in line_item.get('LineItems', []):\n                        for field in item.get('LineItemExpenseFields', []):\n                            if 'ValueDetection' in field:\n                                text_lines.append(field['ValueDetection']['Text'])\n        \n        return '\\n'.join(text_lines)
    
    def get_supported_document_types(self) -> List[str]:
        """Return list of all supported document types"""
        return list(self.classification_keywords.keys())
    
    def is_tax_document(self, doc_type: str) -> bool:
        """Check if document type is a tax document"""
        tax_types = [\"W-2\", \"1099-NEC\", \"1099-INT\", \"1099-DIV\", \"1099-MISC\", \n                    \"1098-E\", \"1098\", \"1095-A\", \"1040\"]\n        return doc_type in tax_types