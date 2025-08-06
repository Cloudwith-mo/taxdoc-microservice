"""
Tax Validation Service - IRS Math Rules and Consistency Checks
"""
import re
from typing import Dict, Any, List, Tuple

class TaxValidationService:
    """Validates extracted tax data against IRS rules"""
    
    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_form_data(self, form_type: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted data against IRS rules"""
        
        self.validation_errors = []
        self.validation_warnings = []
        
        if form_type == "W-2":
            self._validate_w2(extracted_data)
        elif form_type == "1040":
            self._validate_1040(extracted_data)
        elif form_type == "1099-NEC":
            self._validate_1099_nec(extracted_data)
        elif form_type == "1099-DIV":
            self._validate_1099_div(extracted_data)
        
        return {
            "validation_status": "passed" if not self.validation_errors else "failed",
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "needs_review": len(self.validation_errors) > 0 or len(self.validation_warnings) > 2
        }
    
    def _validate_w2(self, data: Dict[str, Any]):
        """W-2 specific validation rules"""
        
        wages = self._get_numeric_value(data, "wages_income")
        ss_wages = self._get_numeric_value(data, "social_security_wages")
        medicare_wages = self._get_numeric_value(data, "medicare_wages")
        ss_tax = self._get_numeric_value(data, "social_security_tax")
        medicare_tax = self._get_numeric_value(data, "medicare_tax")
        
        # Box 1 ≟ Box 3 – 401(k) deferrals – other pretax
        if wages and ss_wages:
            if abs(wages - ss_wages) > 5000:  # Allow for 401k deferrals
                self.validation_warnings.append(
                    f"Large difference between wages ({wages}) and SS wages ({ss_wages}) - check for 401k deferrals"
                )
        
        # Medicare wages should be >= regular wages (no Medicare wage cap)
        if wages and medicare_wages:
            if medicare_wages < wages - 100:  # Small tolerance
                self.validation_errors.append(
                    f"Medicare wages ({medicare_wages}) less than regular wages ({wages})"
                )
        
        # Social Security tax rate check (6.2% for 2024)
        if ss_wages and ss_tax:
            expected_ss_tax = ss_wages * 0.062
            if abs(ss_tax - expected_ss_tax) > 50:  # $50 tolerance
                self.validation_warnings.append(
                    f"SS tax ({ss_tax}) doesn't match expected rate. Expected: {expected_ss_tax:.2f}"
                )
        
        # Medicare tax rate check (1.45% for 2024)
        if medicare_wages and medicare_tax:
            expected_medicare_tax = medicare_wages * 0.0145
            if abs(medicare_tax - expected_medicare_tax) > 25:  # $25 tolerance
                self.validation_warnings.append(
                    f"Medicare tax ({medicare_tax}) doesn't match expected rate. Expected: {expected_medicare_tax:.2f}"
                )
        
        # SSN format validation
        ssn = data.get("employee_ssn")
        if ssn and not re.match(r"\\d{3}-\\d{2}-\\d{4}", str(ssn)):
            self.validation_errors.append("Invalid SSN format")
        
        # EIN format validation
        ein = data.get("employer_ein")
        if ein and not re.match(r"\\d{2}-\\d{7}", str(ein)):
            self.validation_errors.append("Invalid EIN format")
    
    def _validate_1040(self, data: Dict[str, Any]):
        """1040 specific validation rules"""
        
        agi = self._get_numeric_value(data, "adjusted_gross_income")
        total_tax = self._get_numeric_value(data, "total_tax")
        total_payments = self._get_numeric_value(data, "total_payments")
        refund = self._get_numeric_value(data, "refund_amount")
        owed = self._get_numeric_value(data, "amount_owed")
        
        # AGI should be positive (or zero)
        if agi is not None and agi < 0:
            self.validation_warnings.append("Negative AGI - verify loss carryforwards")
        
        # Refund calculation: Line 35a - 35b should equal refund or amount owed
        if total_payments and total_tax:
            calculated_difference = total_payments - total_tax
            
            if calculated_difference > 0:  # Should be refund
                if refund and abs(refund - calculated_difference) > 1:
                    self.validation_errors.append(
                        f"Refund calculation error. Expected: {calculated_difference}, Found: {refund}"
                    )
            else:  # Should be amount owed
                expected_owed = abs(calculated_difference)
                if owed and abs(owed - expected_owed) > 1:
                    self.validation_errors.append(
                        f"Amount owed calculation error. Expected: {expected_owed}, Found: {owed}"
                    )
        
        # Total tax should be reasonable relative to AGI
        if agi and total_tax and agi > 0:
            tax_rate = total_tax / agi
            if tax_rate > 0.5:  # More than 50% tax rate is suspicious
                self.validation_warnings.append(
                    f"High effective tax rate: {tax_rate:.1%} - verify calculations"
                )
    
    def _validate_1099_nec(self, data: Dict[str, Any]):
        """1099-NEC specific validation"""
        
        compensation = self._get_numeric_value(data, "nonemployee_compensation")
        federal_withheld = self._get_numeric_value(data, "federal_withheld")
        
        # Compensation should be positive
        if compensation is not None and compensation <= 0:
            self.validation_errors.append("Nonemployee compensation must be positive")
        
        # Federal withholding shouldn't exceed compensation
        if compensation and federal_withheld:
            if federal_withheld > compensation:
                self.validation_errors.append(
                    f"Federal withholding ({federal_withheld}) exceeds compensation ({compensation})"
                )
            
            # Withholding rate check (shouldn't exceed 50%)
            withholding_rate = federal_withheld / compensation
            if withholding_rate > 0.5:
                self.validation_warnings.append(
                    f"High withholding rate: {withholding_rate:.1%}"
                )
    
    def _validate_1099_div(self, data: Dict[str, Any]):
        """1099-DIV specific validation"""
        
        ordinary_div = self._get_numeric_value(data, "ordinary_dividends")
        qualified_div = self._get_numeric_value(data, "qualified_dividends")
        
        # Qualified dividends shouldn't exceed ordinary dividends
        if ordinary_div and qualified_div:
            if qualified_div > ordinary_div + 1:  # $1 tolerance for rounding
                self.validation_errors.append(
                    f"Qualified dividends ({qualified_div}) exceed ordinary dividends ({ordinary_div})"
                )
    
    def _get_numeric_value(self, data: Dict[str, Any], field: str) -> float:
        """Safely extract numeric value from data"""
        value = data.get(field)
        if value is None:
            return None
        
        try:
            # Remove commas and dollar signs
            if isinstance(value, str):
                value = value.replace(",", "").replace("$", "").strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def cross_validate_forms(self, forms_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cross-validate data across multiple forms"""
        
        cross_validation_results = {
            "cross_validation_status": "passed",
            "cross_validation_errors": [],
            "cross_validation_warnings": []
        }
        
        # Find W-2s and 1040
        w2_forms = [f for f in forms_data if f.get("DocumentType") == "W-2"]
        form_1040 = next((f for f in forms_data if f.get("DocumentType") == "1040"), None)
        
        if w2_forms and form_1040:
            self._cross_validate_w2_1040(w2_forms, form_1040, cross_validation_results)
        
        # Find 1099s and 1040
        form_1099s = [f for f in forms_data if f.get("DocumentType", "").startswith("1099")]
        if form_1099s and form_1040:
            self._cross_validate_1099_1040(form_1099s, form_1040, cross_validation_results)
        
        return cross_validation_results
    
    def _cross_validate_w2_1040(self, w2_forms: List[Dict], form_1040: Dict, results: Dict):
        """Cross-validate W-2 data with 1040"""
        
        # Sum all W-2 wages
        total_w2_wages = 0
        for w2 in w2_forms:
            wages = self._get_numeric_value(w2.get("ExtractedData", {}), "wages_income")
            if wages:
                total_w2_wages += wages
        
        # Compare with 1040 wages line
        form_1040_wages = self._get_numeric_value(form_1040.get("ExtractedData", {}), "wages_income")
        
        if total_w2_wages > 0 and form_1040_wages:
            if abs(total_w2_wages - form_1040_wages) > 100:  # $100 tolerance
                results["cross_validation_errors"].append(
                    f"W-2 total wages ({total_w2_wages}) don't match 1040 wages ({form_1040_wages})"
                )
    
    def _cross_validate_1099_1040(self, form_1099s: List[Dict], form_1040: Dict, results: Dict):
        """Cross-validate 1099 data with 1040"""
        
        # This would check Schedule C, Schedule B, etc. against 1099s
        # Simplified for now
        total_1099_income = 0
        for form_1099 in form_1099s:
            data = form_1099.get("ExtractedData", {})
            doc_type = form_1099.get("DocumentType", "")
            
            if doc_type == "1099-NEC":
                income = self._get_numeric_value(data, "nonemployee_compensation")
            elif doc_type == "1099-INT":
                income = self._get_numeric_value(data, "interest_income")
            elif doc_type == "1099-DIV":
                income = self._get_numeric_value(data, "ordinary_dividends")
            else:
                income = 0
            
            if income:
                total_1099_income += income
        
        # This would need to check against appropriate 1040 lines
        # Implementation depends on having Schedule C, B, etc. data
        pass