"""
Tax-Only Document Extraction Configuration
Supports only federal tax forms with IRS validation rules
"""

# Supported tax forms only - everything else gets rejected
SUPPORTED_TAX_FORMS = {
    "1040", "W-2", "1099-NEC", "1099-MISC", "1099-DIV", "1099-INT", 
    "K-1_1065", "K-1_1120S", "941"
}

TAX_DOCUMENT_CONFIGS = {
    "1040": {
        "year": 2024,
        "fields": [
            {"box": "11b", "name": "wages_income", "type": "currency", "required": True},
            {"box": "2a", "name": "tax_exempt_interest", "type": "currency"},
            {"box": "3a", "name": "qualified_dividends", "type": "currency"},
            {"box": "11", "name": "adjusted_gross_income", "type": "currency", "required": True},
            {"box": "24", "name": "total_tax", "type": "currency", "required": True},
            {"box": "33", "name": "total_payments", "type": "currency"},
            {"box": "37", "name": "refund_amount", "type": "currency"},
            {"box": "38", "name": "amount_owed", "type": "currency"}
        ],
        "queries": [
            {"Text": "What is the wages, salaries, tips amount (Line 1a)?", "Alias": "wages_income"},
            {"Text": "What is the adjusted gross income (Line 11)?", "Alias": "adjusted_gross_income"},
            {"Text": "What is the total tax (Line 24)?", "Alias": "total_tax"},
            {"Text": "What is the total payments (Line 33)?", "Alias": "total_payments"},
            {"Text": "What is the refund amount (Line 37)?", "Alias": "refund_amount"},
            {"Text": "What is the amount owed (Line 38)?", "Alias": "amount_owed"}
        ],
        "claude_prompt": "Extract 1040 fields: wages_income, adjusted_gross_income, total_tax, total_payments, refund_amount, amount_owed. Return JSON with numeric values.",
        "math_rules": [
            {"rule": "refund_calc", "formula": "total_payments - total_tax", "tolerance": 1.0},
            {"rule": "payment_check", "formula": "total_payments >= 0"},
            {"rule": "agi_positive", "formula": "adjusted_gross_income >= 0"}
        ]
    },
    "W-2": {
        "year": 2024,
        "fields": [
            {"box": "1", "name": "wages_income", "type": "currency", "required": True},
            {"box": "2", "name": "federal_withheld", "type": "currency", "required": True},
            {"box": "3", "name": "social_security_wages", "type": "currency", "required": True},
            {"box": "4", "name": "social_security_tax", "type": "currency"},
            {"box": "5", "name": "medicare_wages", "type": "currency", "required": True},
            {"box": "6", "name": "medicare_tax", "type": "currency"},
            {"box": "a", "name": "employee_ssn", "type": "ssn", "required": True},
            {"box": "b", "name": "employer_ein", "type": "ein", "required": True}
        ],
        "queries": [
            {"Text": "What is the employee's social security number?", "Alias": "employee_ssn"},
            {"Text": "What is the employer's EIN?", "Alias": "employer_ein"},
            {"Text": "What are the wages, tips, other compensation (Box 1)?", "Alias": "wages_income"},
            {"Text": "What is the federal income tax withheld (Box 2)?", "Alias": "federal_withheld"},
            {"Text": "What are the Social Security wages (Box 3)?", "Alias": "social_security_wages"},
            {"Text": "What is the Social Security tax withheld (Box 4)?", "Alias": "social_security_tax"},
            {"Text": "What are the Medicare wages (Box 5)?", "Alias": "medicare_wages"},
            {"Text": "What is the Medicare tax withheld (Box 6)?", "Alias": "medicare_tax"}
        ],
        "claude_prompt": "Extract W-2 fields: employee_ssn, employer_ein, wages_income, federal_withheld, social_security_wages, social_security_tax, medicare_wages, medicare_tax. Return JSON.",
        "math_rules": [
            {"rule": "ss_wage_check", "formula": "social_security_wages <= wages_income + 1000"},
            {"rule": "medicare_wage_check", "formula": "medicare_wages >= wages_income - 1000"},
            {"rule": "ss_tax_rate", "formula": "social_security_tax <= social_security_wages * 0.062 + 10"}
        ]
    },
    "1099-NEC": {
        "year": 2024,
        "fields": [
            {"box": "1", "name": "nonemployee_compensation", "type": "currency", "required": True},
            {"box": "4", "name": "federal_withheld", "type": "currency"},
            {"box": "a", "name": "payer_tin", "type": "ein", "required": True},
            {"box": "b", "name": "recipient_tin", "type": "ssn", "required": True}
        ],
        "queries": [
            {"Text": "What is the payer's TIN?", "Alias": "payer_tin"},
            {"Text": "What is the recipient's TIN?", "Alias": "recipient_tin"},
            {"Text": "What is the nonemployee compensation (Box 1)?", "Alias": "nonemployee_compensation"},
            {"Text": "What is the federal income tax withheld (Box 4)?", "Alias": "federal_withheld"}
        ],
        "claude_prompt": "Extract 1099-NEC fields: payer_tin, recipient_tin, nonemployee_compensation, federal_withheld. Return JSON.",
        "math_rules": [
            {"rule": "compensation_positive", "formula": "nonemployee_compensation > 0"},
            {"rule": "withholding_reasonable", "formula": "federal_withheld <= nonemployee_compensation * 0.5"}
        ]
    },
    "1099-MISC": {
        "year": 2024,
        "fields": [
            {"box": "1", "name": "rents", "type": "currency"},
            {"box": "2", "name": "royalties", "type": "currency"},
            {"box": "3", "name": "other_income", "type": "currency"},
            {"box": "4", "name": "federal_withheld", "type": "currency"}
        ],
        "queries": [
            {"Text": "What are the rents (Box 1)?", "Alias": "rents"},
            {"Text": "What are the royalties (Box 2)?", "Alias": "royalties"},
            {"Text": "What is other income (Box 3)?", "Alias": "other_income"},
            {"Text": "What is federal income tax withheld (Box 4)?", "Alias": "federal_withheld"}
        ],
        "claude_prompt": "Extract 1099-MISC fields: rents, royalties, other_income, federal_withheld. Return JSON.",
        "math_rules": []
    },
    "1099-DIV": {
        "year": 2024,
        "fields": [
            {"box": "1a", "name": "ordinary_dividends", "type": "currency"},
            {"box": "1b", "name": "qualified_dividends", "type": "currency"},
            {"box": "4", "name": "federal_withheld", "type": "currency"}
        ],
        "queries": [
            {"Text": "What are the ordinary dividends (Box 1a)?", "Alias": "ordinary_dividends"},
            {"Text": "What are the qualified dividends (Box 1b)?", "Alias": "qualified_dividends"},
            {"Text": "What is federal income tax withheld (Box 4)?", "Alias": "federal_withheld"}
        ],
        "claude_prompt": "Extract 1099-DIV fields: ordinary_dividends, qualified_dividends, federal_withheld. Return JSON.",
        "math_rules": [
            {"rule": "qualified_check", "formula": "qualified_dividends <= ordinary_dividends + 1"}
        ]
    },
    "1099-INT": {
        "year": 2024,
        "fields": [
            {"box": "1", "name": "interest_income", "type": "currency", "required": True},
            {"box": "4", "name": "federal_withheld", "type": "currency"}
        ],
        "queries": [
            {"Text": "What is the interest income (Box 1)?", "Alias": "interest_income"},
            {"Text": "What is federal income tax withheld (Box 4)?", "Alias": "federal_withheld"}
        ],
        "claude_prompt": "Extract 1099-INT fields: interest_income, federal_withheld. Return JSON.",
        "math_rules": [
            {"rule": "interest_positive", "formula": "interest_income > 0"}
        ]
    },
    "K-1_1065": {
        "year": 2024,
        "fields": [
            {"box": "1", "name": "ordinary_income", "type": "currency"},
            {"box": "2", "name": "net_rental_income", "type": "currency"},
            {"box": "3", "name": "guaranteed_payments", "type": "currency"}
        ],
        "queries": [
            {"Text": "What is ordinary business income (Box 1)?", "Alias": "ordinary_income"},
            {"Text": "What is net rental real estate income (Box 2)?", "Alias": "net_rental_income"},
            {"Text": "What are guaranteed payments (Box 3)?", "Alias": "guaranteed_payments"}
        ],
        "claude_prompt": "Extract K-1 1065 fields: ordinary_income, net_rental_income, guaranteed_payments. Return JSON.",
        "math_rules": []
    },
    "K-1_1120S": {
        "year": 2024,
        "fields": [
            {"box": "1", "name": "ordinary_income", "type": "currency"},
            {"box": "2", "name": "net_rental_income", "type": "currency"}
        ],
        "queries": [
            {"Text": "What is ordinary business income (Box 1)?", "Alias": "ordinary_income"},
            {"Text": "What is net rental real estate income (Box 2)?", "Alias": "net_rental_income"}
        ],
        "claude_prompt": "Extract K-1 1120S fields: ordinary_income, net_rental_income. Return JSON.",
        "math_rules": []
    },
    "941": {
        "year": 2024,
        "fields": [
            {"box": "2", "name": "total_wages", "type": "currency", "required": True},
            {"box": "3", "name": "federal_withheld", "type": "currency"},
            {"box": "5a", "name": "taxable_ss_wages", "type": "currency"},
            {"box": "5c", "name": "taxable_medicare_wages", "type": "currency"}
        ],
        "queries": [
            {"Text": "What are the total wages (Line 2)?", "Alias": "total_wages"},
            {"Text": "What is federal income tax withheld (Line 3)?", "Alias": "federal_withheld"},
            {"Text": "What are taxable Social Security wages (Line 5a)?", "Alias": "taxable_ss_wages"},
            {"Text": "What are taxable Medicare wages (Line 5c)?", "Alias": "taxable_medicare_wages"}
        ],
        "claude_prompt": "Extract 941 fields: total_wages, federal_withheld, taxable_ss_wages, taxable_medicare_wages. Return JSON.",
        "math_rules": [
            {"rule": "ss_wages_check", "formula": "taxable_ss_wages <= total_wages + 100"},
            {"rule": "medicare_wages_check", "formula": "taxable_medicare_wages >= total_wages - 100"}
        ]
    }
}

# PII masking configuration
PII_MASKING_RULES = {
    "ssn": {"pattern": r"(\d{3})-(\d{2})-(\d{4})", "mask": "***-**-{2}"},
    "ein": {"pattern": r"(\d{2})-(\d{7})", "mask": "**-*****{1}"}
}

# Tax form classification keywords
TAX_CLASSIFICATION_KEYWORDS = {
    "1040": ["1040", "individual income tax return", "form 1040"],
    "W-2": ["w-2", "w2", "wage and tax statement", "employee's social security"],
    "1099-NEC": ["1099-nec", "nonemployee compensation"],
    "1099-MISC": ["1099-misc", "miscellaneous income"],
    "1099-DIV": ["1099-div", "dividends"],
    "1099-INT": ["1099-int", "interest income"],
    "K-1_1065": ["k-1", "schedule k-1", "1065", "partnership"],
    "K-1_1120S": ["k-1", "schedule k-1", "1120s", "s corporation"],
    "941": ["941", "quarterly federal tax return", "employer's quarterly"]
}