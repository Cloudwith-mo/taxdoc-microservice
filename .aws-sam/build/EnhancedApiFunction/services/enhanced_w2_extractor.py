import json
from .bedrock_service import BedrockService

class EnhancedW2Extractor:
    def __init__(self):
        self.bedrock = BedrockService()
    
    def extract_w2_fields(self, textract_text: str) -> dict:
        """Extract W-2 fields using Claude via Bedrock"""
        
        prompt = f"""
Extract W-2 tax form data from this text. Return JSON with these exact fields:
- EmployerName
- EmployerEIN  
- EmployeeName
- EmployeeSSN
- Wages (Box 1)
- FederalTaxWithheld (Box 2)
- SocialSecurityWages (Box 3)
- SocialSecurityTaxWithheld (Box 4)
- MedicareWages (Box 5)
- MedicareTaxWithheld (Box 6)
- StateWages
- StateTaxWithheld

Text:
{textract_text}

Return only valid JSON, no explanation:
"""
        
        response = self.bedrock.invoke_model(prompt)
        
        try:
            return json.loads(response)
        except:
            # Fallback to rule-based
            return self._fallback_extraction(textract_text)
    
    def _fallback_extraction(self, text: str) -> dict:
        """Fallback to current rule-based method"""
        from .extractor_service import ExtractorService
        extractor = ExtractorService()
        return extractor._extract_w2_fields({'Blocks': [{'BlockType': 'LINE', 'Text': line} for line in text.split('\n')]})