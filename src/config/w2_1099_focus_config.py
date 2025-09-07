"""
W-2 and 1099 Focus Configuration
Initial narrow focus on most common tax forms with highest ROI
"""

# Phase 1: W-2 and 1099 forms only
PHASE_1_FORMS = {"W-2", "1099-NEC", "1099-MISC", "1099-DIV", "1099-INT"}

# Enhanced W-2 configuration with validation
W2_CONFIG = {
    "form_type": "W-2",
    "description": "Wage and Tax Statement",
    "priority": "HIGH",
    "accuracy_target": 99,
    "fields": [
        {"box": "a", "name": "employee_ssn", "type": "ssn", "required": True, "validation": "ssn_format"},
        {"box": "b", "name": "employer_ein", "type": "ein", "required": True, "validation": "ein_format"},
        {"box": "c", "name": "employer_name", "type": "text", "required": True},
        {"box": "d", "name": "control_number", "type": "text"},
        {"box": "e", "name": "employee_name", "type": "text", "required": True},
        {"box": "f", "name": "employee_address", "type": "text", "required": True},
        {"box": "1", "name": "wages_income", "type": "currency", "required": True},
        {"box": "2", "name": "federal_withheld", "type": "currency", "required": True},
        {"box": "3", "name": "social_security_wages", "type": "currency", "required": True},
        {"box": "4", "name": "social_security_tax", "type": "currency"},
        {"box": "5", "name": "medicare_wages", "type": "currency", "required": True},
        {"box": "6", "name": "medicare_tax", "type": "currency"},
        {"box": "7", "name": "social_security_tips", "type": "currency"},
        {"box": "8", "name": "allocated_tips", "type": "currency"},
        {"box": "10", "name": "dependent_care_benefits", "type": "currency"},
        {"box": "11", "name": "nonqualified_plans", "type": "currency"},
        {"box": "12", "name": "codes", "type": "text"},
        {"box": "13", "name": "statutory_employee", "type": "checkbox"},
        {"box": "13", "name": "retirement_plan", "type": "checkbox"},
        {"box": "13", "name": "third_party_sick_pay", "type": "checkbox"},
        {"box": "15", "name": "state", "type": "text"},
        {"box": "16", "name": "state_wages", "type": "currency"},
        {"box": "17", "name": "state_tax", "type": "currency"}
    ],
    "textract_queries": [
        {"Text": "What is the employee's social security number in box a?", "Alias": "employee_ssn"},
        {"Text": "What is the employer identification number in box b?", "Alias": "employer_ein"},
        {"Text": "What is the employer's name in box c?", "Alias": "employer_name"},
        {"Text": "What is the employee's name in box e?", "Alias": "employee_name"},
        {"Text": "What are the wages, tips, other compensation in box 1?", "Alias": "wages_income"},
        {"Text": "What is the federal income tax withheld in box 2?", "Alias": "federal_withheld"},
        {"Text": "What are the Social Security wages in box 3?", "Alias": "social_security_wages"},
        {"Text": "What is the Social Security tax withheld in box 4?", "Alias": "social_security_tax"},
        {"Text": "What are the Medicare wages and tips in box 5?", "Alias": "medicare_wages"},
        {"Text": "What is the Medicare tax withheld in box 6?", "Alias": "medicare_tax"}
    ],
    "claude_prompt": """Extract all W-2 fields from this wage and tax statement. Focus on:
- Employee SSN (box a) and name (box e)
- Employer EIN (box b) and name (box c)  
- Wages (box 1), federal tax withheld (box 2)
- Social Security wages (box 3) and tax (box 4)
- Medicare wages (box 5) and tax (box 6)
Return JSON with exact field names.""",
    "validation_rules": [
        {"rule": "ss_wage_relationship", "formula": "social_security_wages <= wages_income + 1000", "error": "SS wages exceed total wages"},
        {"rule": "medicare_wage_relationship", "formula": "medicare_wages >= wages_income - 1000", "error": "Medicare wages less than total wages"},
        {"rule": "ss_tax_rate_check", "formula": "social_security_tax <= social_security_wages * 0.062 + 10", "error": "SS tax rate exceeds 6.2%"},
        {"rule": "medicare_tax_rate_check", "formula": "medicare_tax <= medicare_wages * 0.0145 + 5", "error": "Medicare tax rate exceeds 1.45%"},
        {"rule": "federal_withholding_reasonable", "formula": "federal_withheld <= wages_income * 0.37", "error": "Federal withholding exceeds 37%"}
    ]
}

# 1099-NEC configuration (contractor payments)
NEC_1099_CONFIG = {
    "form_type": "1099-NEC", 
    "description": "Nonemployee Compensation",
    "priority": "HIGH",
    "accuracy_target": 98,
    "fields": [
        {"box": "1", "name": "payer_name", "type": "text", "required": True},
        {"box": "2", "name": "payer_address", "type": "text", "required": True},
        {"box": "3", "name": "payer_tin", "type": "ein", "required": True},
        {"box": "4", "name": "recipient_name", "type": "text", "required": True},
        {"box": "5", "name": "recipient_address", "type": "text", "required": True},
        {"box": "6", "name": "recipient_tin", "type": "ssn", "required": True},
        {"box": "1", "name": "nonemployee_compensation", "type": "currency", "required": True},
        {"box": "4", "name": "federal_withheld", "type": "currency"}
    ],
    "textract_queries": [
        {"Text": "What is the payer's name?", "Alias": "payer_name"},
        {"Text": "What is the payer's TIN or EIN?", "Alias": "payer_tin"},
        {"Text": "What is the recipient's name?", "Alias": "recipient_name"},
        {"Text": "What is the recipient's TIN or SSN?", "Alias": "recipient_tin"},
        {"Text": "What is the nonemployee compensation amount in box 1?", "Alias": "nonemployee_compensation"},
        {"Text": "What is the federal income tax withheld in box 4?", "Alias": "federal_withheld"}
    ],
    "claude_prompt": """Extract 1099-NEC fields for contractor payments:
- Payer name, address, and TIN/EIN
- Recipient name, address, and TIN/SSN
- Nonemployee compensation (box 1)
- Federal income tax withheld (box 4)
Return JSON with exact field names.""",
    "validation_rules": [
        {"rule": "compensation_positive", "formula": "nonemployee_compensation > 0", "error": "Compensation must be positive"},
        {"rule": "withholding_reasonable", "formula": "federal_withheld <= nonemployee_compensation * 0.5", "error": "Withholding exceeds 50% of compensation"},
        {"rule": "minimum_reporting", "formula": "nonemployee_compensation >= 600", "warning": "Amount below $600 reporting threshold"}
    ]
}

# 1099-INT configuration (interest income)
INT_1099_CONFIG = {
    "form_type": "1099-INT",
    "description": "Interest Income", 
    "priority": "MEDIUM",
    "accuracy_target": 95,
    "fields": [
        {"box": "1", "name": "payer_name", "type": "text", "required": True},
        {"box": "2", "name": "payer_tin", "type": "ein", "required": True},
        {"box": "3", "name": "recipient_name", "type": "text", "required": True},
        {"box": "4", "name": "recipient_tin", "type": "ssn", "required": True},
        {"box": "1", "name": "interest_income", "type": "currency", "required": True},
        {"box": "4", "name": "federal_withheld", "type": "currency"}
    ],
    "textract_queries": [
        {"Text": "What is the interest income in box 1?", "Alias": "interest_income"},
        {"Text": "What is the federal income tax withheld in box 4?", "Alias": "federal_withheld"},
        {"Text": "What is the payer's name?", "Alias": "payer_name"},
        {"Text": "What is the recipient's name?", "Alias": "recipient_name"}
    ],
    "claude_prompt": "Extract 1099-INT interest income fields: payer info, recipient info, interest_income (box 1), federal_withheld (box 4). Return JSON.",
    "validation_rules": [
        {"rule": "interest_positive", "formula": "interest_income > 0", "error": "Interest income must be positive"},
        {"rule": "minimum_reporting", "formula": "interest_income >= 10", "warning": "Amount below $10 reporting threshold"}
    ]
}

# 1099-DIV configuration (dividends)
DIV_1099_CONFIG = {
    "form_type": "1099-DIV",
    "description": "Dividends and Distributions",
    "priority": "MEDIUM", 
    "accuracy_target": 95,
    "fields": [
        {"box": "1a", "name": "ordinary_dividends", "type": "currency"},
        {"box": "1b", "name": "qualified_dividends", "type": "currency"},
        {"box": "4", "name": "federal_withheld", "type": "currency"}
    ],
    "textract_queries": [
        {"Text": "What are the ordinary dividends in box 1a?", "Alias": "ordinary_dividends"},
        {"Text": "What are the qualified dividends in box 1b?", "Alias": "qualified_dividends"},
        {"Text": "What is the federal income tax withheld in box 4?", "Alias": "federal_withheld"}
    ],
    "claude_prompt": "Extract 1099-DIV dividend fields: ordinary_dividends (1a), qualified_dividends (1b), federal_withheld (4). Return JSON.",
    "validation_rules": [
        {"rule": "qualified_subset", "formula": "qualified_dividends <= ordinary_dividends + 1", "error": "Qualified dividends exceed ordinary dividends"}
    ]
}

# 1099-MISC configuration (miscellaneous income)
MISC_1099_CONFIG = {
    "form_type": "1099-MISC",
    "description": "Miscellaneous Income",
    "priority": "MEDIUM",
    "accuracy_target": 93,
    "fields": [
        {"box": "1", "name": "rents", "type": "currency"},
        {"box": "2", "name": "royalties", "type": "currency"},
        {"box": "3", "name": "other_income", "type": "currency"},
        {"box": "4", "name": "federal_withheld", "type": "currency"}
    ],
    "textract_queries": [
        {"Text": "What are the rents in box 1?", "Alias": "rents"},
        {"Text": "What are the royalties in box 2?", "Alias": "royalties"},
        {"Text": "What is other income in box 3?", "Alias": "other_income"},
        {"Text": "What is federal income tax withheld in box 4?", "Alias": "federal_withheld"}
    ],
    "claude_prompt": "Extract 1099-MISC fields: rents (1), royalties (2), other_income (3), federal_withheld (4). Return JSON.",
    "validation_rules": []
}

# Combined configuration
W2_1099_CONFIGS = {
    "W-2": W2_CONFIG,
    "1099-NEC": NEC_1099_CONFIG,
    "1099-INT": INT_1099_CONFIG,
    "1099-DIV": DIV_1099_CONFIG,
    "1099-MISC": MISC_1099_CONFIG
}

# Classification keywords for focused forms
FOCUSED_CLASSIFICATION = {
    "W-2": ["w-2", "w2", "wage and tax statement", "employee's social security", "employer identification"],
    "1099-NEC": ["1099-nec", "nonemployee compensation", "contractor payment"],
    "1099-INT": ["1099-int", "interest income", "interest statement"],
    "1099-DIV": ["1099-div", "dividends", "dividend statement"],
    "1099-MISC": ["1099-misc", "miscellaneous income", "rents", "royalties"]
}

# Expansion roadmap phases
EXPANSION_PHASES = {
    "phase_1": {
        "forms": ["W-2", "1099-NEC", "1099-INT", "1099-DIV", "1099-MISC"],
        "timeline": "Q1 2024",
        "goal": "Perfect wage and income form extraction",
        "success_metrics": ["99% W-2 accuracy", "98% 1099-NEC accuracy", "95% other 1099s"]
    },
    "phase_2": {
        "forms": ["receipts", "invoices", "Schedule C"],
        "timeline": "Q2 2024", 
        "goal": "Business expense tracking and Schedule C automation",
        "success_metrics": ["90% receipt OCR", "Automated Schedule C generation"]
    },
    "phase_3": {
        "forms": ["1040", "Schedule A", "Schedule B"],
        "timeline": "Q3 2024",
        "goal": "Full 1040 preparation pipeline",
        "success_metrics": ["End-to-end tax return preparation", "E-file integration"]
    }
}