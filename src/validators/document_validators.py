"""
Universal document validators with type-safe extraction and math checks
"""
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

class DocumentValidator:
    """Base validator with common validation methods"""
    
    @staticmethod
    def validate_money(value, field_name="amount"):
        """Validate money format: ####.## (no $ or commas)"""
        if not value:
            return None, f"Missing {field_name}"
        
        # Clean and validate
        cleaned = re.sub(r'[^\d.]', '', str(value))
        try:
            amount = Decimal(cleaned)
            if amount < 0:
                return None, f"Negative {field_name}: {amount}"
            return f"{amount:.2f}", None
        except (InvalidOperation, ValueError):
            return None, f"Invalid money format: {value}"
    
    @staticmethod
    def validate_date(value, field_name="date"):
        """Validate date format: YYYY-MM-DD"""
        if not value:
            return None, f"Missing {field_name}"
        
        try:
            dt = datetime.strptime(str(value), '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d'), None
        except ValueError:
            return None, f"Invalid date format: {value} (expected YYYY-MM-DD)"

class PaystubValidator(DocumentValidator):
    """Paystub-specific validation"""
    
    def validate(self, data):
        """Validate complete paystub with math checks"""
        errors = []
        warnings = []
        validated = {}
        
        # Validate money fields (required)
        required_money = ['gross_current', 'net_current']
        optional_money = ['gross_ytd', 'net_ytd', 'deduction_total_current', 'deduction_total_ytd', 'pay_rate']
        
        for field in required_money:
            value, error = self.validate_money(data.get(field), field)
            if error:
                errors.append(error)
            else:
                validated[field] = value
        
        for field in optional_money:
            if data.get(field):
                value, error = self.validate_money(data.get(field), field)
                if error:
                    warnings.append(error)
                else:
                    validated[field] = value
        
        # Validate dates with sequence check
        date_fields = ['cycle_start', 'cycle_end', 'pay_date']
        dates = {}
        
        for field in date_fields:
            value, error = self.validate_date(data.get(field), field)
            if error:
                errors.append(error)
            else:
                validated[field] = value
                dates[field] = datetime.strptime(value, '%Y-%m-%d')
        
        # Date sequence validation
        if len(dates) >= 2:
            if 'cycle_start' in dates and 'cycle_end' in dates:
                if dates['cycle_start'] >= dates['cycle_end']:
                    errors.append("cycle_start must be before cycle_end")
            
            if 'cycle_end' in dates and 'pay_date' in dates:
                if dates['cycle_end'] > dates['pay_date']:
                    warnings.append("pay_date is before cycle_end")
        
        # Math validation: gross - deductions = net
        try:
            gross = Decimal(validated.get('gross_current', '0'))
            deductions = Decimal(validated.get('deduction_total_current', '0'))
            net = Decimal(validated.get('net_current', '0'))
            
            expected_net = gross - deductions
            if abs(net - expected_net) > Decimal('0.01'):
                errors.append(f"Math error: {gross} - {deductions} = {expected_net}, got {net}")
        except (InvalidOperation, KeyError):
            errors.append("Cannot validate math: missing or invalid amounts")
        
        # Required fields
        required = ['employee_name', 'pay_date', 'gross_current', 'net_current']
        for field in required:
            if not data.get(field):
                errors.append(f"Missing required field: {field}")
            else:
                validated[field] = data[field]
        
        # Copy other fields
        for field in ['employee_name', 'employer_name', 'employer_address', 'current_hours']:
            if data.get(field):
                validated[field] = data[field]
        
        validated['validation'] = {'errors': errors, 'warnings': warnings}
        return validated

# Factory function
def get_validator(doc_type):
    """Get appropriate validator for document type"""
    validators = {
        'PAYSTUB': PaystubValidator()
    }
    return validators.get(doc_type, DocumentValidator())