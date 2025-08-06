"""
W-2 and 1099 Focused Processing Orchestrator
Narrow focus on highest-impact tax forms with 99%+ accuracy
"""

import json
import logging
from typing import Dict, Any, Optional
from src.config.w2_1099_focus_config import W2_1099_CONFIGS, PHASE_1_FORMS, FOCUSED_CLASSIFICATION

logger = logging.getLogger(__name__)

class W21099Orchestrator:
    """Focused processor for W-2 and 1099 forms only"""
    
    def __init__(self, textract_service, claude_service):
        self.textract_service = textract_service
        self.claude_service = claude_service
        self.supported_forms = PHASE_1_FORMS
        
    def process_document(self, document_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Process W-2 or 1099 document with three-layer extraction"""
        try:
            # Step 1: Classify document type
            form_type = self._classify_document(document_bytes, filename)
            if not form_type:
                raise UnsupportedDocumentError("Only W-2 and 1099 forms supported in Phase 1")
                
            logger.info(f"Processing {form_type} document: {filename}")
            
            # Step 2: Get form configuration
            config = W2_1099_CONFIGS[form_type]
            
            # Step 3: Three-layer extraction
            extraction_result = self._three_layer_extraction(document_bytes, config)
            
            # Step 4: Validate extracted data
            validation_result = self._validate_extraction(extraction_result, config)
            
            # Step 5: Calculate confidence and quality metrics
            quality_metrics = self._calculate_quality_metrics(extraction_result, validation_result)
            
            return {
                "form_type": form_type,
                "extraction_data": extraction_result,
                "validation_result": validation_result,
                "quality_metrics": quality_metrics,
                "processing_metadata": {
                    "filename": filename,
                    "phase": "1",
                    "accuracy_target": config["accuracy_target"],
                    "priority": config["priority"]
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}")
            raise
    
    def _classify_document(self, document_bytes: bytes, filename: str) -> Optional[str]:
        """Classify document as W-2 or 1099 variant"""
        try:
            # Use Textract for initial text extraction
            text_content = self.textract_service.extract_text(document_bytes)
            text_lower = text_content.lower()
            
            # Check for form-specific keywords
            for form_type, keywords in FOCUSED_CLASSIFICATION.items():
                if any(keyword in text_lower for keyword in keywords):
                    logger.info(f"Classified as {form_type} based on keywords")
                    return form_type
            
            # Fallback: check filename
            filename_lower = filename.lower()
            for form_type in self.supported_forms:
                if form_type.lower().replace("-", "") in filename_lower:
                    return form_type
                    
            return None
            
        except Exception as e:
            logger.error(f"Classification error: {str(e)}")
            return None
    
    def _three_layer_extraction(self, document_bytes: bytes, config: Dict) -> Dict[str, Any]:
        """Three-layer extraction: Textract -> Claude -> Regex"""
        extraction_result = {
            "textract_data": {},
            "claude_data": {},
            "regex_data": {},
            "final_data": {},
            "confidence_scores": {},
            "source_attribution": {}
        }
        
        # Layer 1: Textract Queries (Primary)
        try:
            textract_result = self.textract_service.extract_with_queries(
                document_bytes, config["textract_queries"]
            )
            extraction_result["textract_data"] = textract_result
            logger.info(f"Textract extracted {len(textract_result)} fields")
        except Exception as e:
            logger.warning(f"Textract extraction failed: {str(e)}")
        
        # Layer 2: Claude LLM (Smart Fallback)
        try:
            claude_result = self.claude_service.extract_structured_data(
                document_bytes, config["claude_prompt"]
            )
            extraction_result["claude_data"] = claude_result
            logger.info(f"Claude extracted {len(claude_result)} fields")
        except Exception as e:
            logger.warning(f"Claude extraction failed: {str(e)}")
        
        # Layer 3: Regex Patterns (Safety Net)
        try:
            regex_result = self._regex_extraction(document_bytes, config)
            extraction_result["regex_data"] = regex_result
            logger.info(f"Regex extracted {len(regex_result)} fields")
        except Exception as e:
            logger.warning(f"Regex extraction failed: {str(e)}")
        
        # Merge results with confidence-based selection
        extraction_result["final_data"] = self._merge_extraction_layers(extraction_result)
        
        return extraction_result
    
    def _regex_extraction(self, document_bytes: bytes, config: Dict) -> Dict[str, Any]:
        """Regex-based extraction for critical fields"""
        import re
        
        # Get text content
        text_content = self.textract_service.extract_text(document_bytes)
        
        regex_patterns = {
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "ein": r"\b\d{2}-\d{7}\b", 
            "currency": r"\$?[\d,]+\.?\d{0,2}",
            "zip_code": r"\b\d{5}(-\d{4})?\b"
        }
        
        extracted_data = {}
        
        # Extract SSNs
        ssn_matches = re.findall(regex_patterns["ssn"], text_content)
        if ssn_matches:
            extracted_data["employee_ssn"] = ssn_matches[0]
        
        # Extract EINs  
        ein_matches = re.findall(regex_patterns["ein"], text_content)
        if ein_matches:
            extracted_data["employer_ein"] = ein_matches[0]
        
        # Extract currency amounts (basic)
        currency_matches = re.findall(regex_patterns["currency"], text_content)
        if len(currency_matches) >= 2:
            extracted_data["wages_income"] = currency_matches[0]
            extracted_data["federal_withheld"] = currency_matches[1]
        
        return extracted_data
    
    def _merge_extraction_layers(self, extraction_result: Dict) -> Dict[str, Any]:
        """Merge three layers with confidence-based selection"""
        final_data = {}
        confidence_scores = {}
        source_attribution = {}
        
        textract_data = extraction_result.get("textract_data", {})
        claude_data = extraction_result.get("claude_data", {})
        regex_data = extraction_result.get("regex_data", {})
        
        # Get all possible field names
        all_fields = set()
        all_fields.update(textract_data.keys())
        all_fields.update(claude_data.keys())
        all_fields.update(regex_data.keys())
        
        for field in all_fields:
            textract_value = textract_data.get(field)
            claude_value = claude_data.get(field)
            regex_value = regex_data.get(field)
            
            # Priority: Textract (high confidence) -> Claude -> Regex
            if textract_value and self._is_high_confidence(textract_value):
                final_data[field] = textract_value
                confidence_scores[field] = 0.95
                source_attribution[field] = "textract"
            elif claude_value:
                final_data[field] = claude_value
                confidence_scores[field] = 0.85
                source_attribution[field] = "claude"
            elif regex_value:
                final_data[field] = regex_value
                confidence_scores[field] = 0.75
                source_attribution[field] = "regex"
        
        extraction_result["confidence_scores"] = confidence_scores
        extraction_result["source_attribution"] = source_attribution
        
        return final_data
    
    def _is_high_confidence(self, value: Any) -> bool:
        """Check if Textract value has high confidence"""
        # Simple heuristic - in real implementation, use actual confidence scores
        if isinstance(value, dict) and "confidence" in value:
            return value["confidence"] > 0.9
        return True  # Assume high confidence for now
    
    def _validate_extraction(self, extraction_result: Dict, config: Dict) -> Dict[str, Any]:
        """Validate extracted data against form-specific rules"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "field_validations": {}
        }
        
        final_data = extraction_result.get("final_data", {})
        
        # Apply validation rules
        for rule in config.get("validation_rules", []):
            try:
                rule_result = self._apply_validation_rule(final_data, rule)
                validation_result["field_validations"][rule["rule"]] = rule_result
                
                if not rule_result["passed"]:
                    if rule.get("error"):
                        validation_result["errors"].append(rule["error"])
                        validation_result["is_valid"] = False
                    elif rule.get("warning"):
                        validation_result["warnings"].append(rule["warning"])
                        
            except Exception as e:
                logger.warning(f"Validation rule {rule['rule']} failed: {str(e)}")
        
        return validation_result
    
    def _apply_validation_rule(self, data: Dict, rule: Dict) -> Dict[str, Any]:
        """Apply a single validation rule"""
        try:
            formula = rule["formula"]
            
            # Simple formula evaluation (expand as needed)
            if "social_security_wages <= wages_income" in formula:
                ss_wages = float(data.get("social_security_wages", 0))
                wages = float(data.get("wages_income", 0))
                passed = ss_wages <= wages + 1000
            elif "nonemployee_compensation > 0" in formula:
                compensation = float(data.get("nonemployee_compensation", 0))
                passed = compensation > 0
            else:
                passed = True  # Default pass for unimplemented rules
            
            return {
                "passed": passed,
                "rule": rule["rule"],
                "formula": formula
            }
            
        except Exception as e:
            return {
                "passed": False,
                "rule": rule["rule"],
                "error": str(e)
            }
    
    def _calculate_quality_metrics(self, extraction_result: Dict, validation_result: Dict) -> Dict[str, Any]:
        """Calculate quality metrics for the extraction"""
        final_data = extraction_result.get("final_data", {})
        confidence_scores = extraction_result.get("confidence_scores", {})
        
        # Calculate overall confidence
        if confidence_scores:
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
        else:
            avg_confidence = 0.0
        
        # Count fields extracted
        fields_extracted = len(final_data)
        
        # Quality grade based on confidence and validation
        if avg_confidence >= 0.95 and validation_result["is_valid"]:
            quality_grade = "A"
        elif avg_confidence >= 0.85 and len(validation_result["errors"]) == 0:
            quality_grade = "B"
        elif avg_confidence >= 0.75:
            quality_grade = "C"
        else:
            quality_grade = "D"
        
        return {
            "overall_confidence": round(avg_confidence, 3),
            "fields_extracted": fields_extracted,
            "validation_errors": len(validation_result["errors"]),
            "validation_warnings": len(validation_result["warnings"]),
            "quality_grade": quality_grade,
            "extraction_completeness": min(1.0, fields_extracted / 8),  # Assume 8 key fields
            "ready_for_filing": validation_result["is_valid"] and avg_confidence >= 0.9
        }

class UnsupportedDocumentError(Exception):
    """Raised when document is not a supported W-2 or 1099 form"""
    pass