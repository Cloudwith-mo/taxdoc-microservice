"""
Comprehensive Multi-form Document Extraction Configuration
Supports W-2, 1099 series, 1098 series, 1095 series, 1040, Bank Statements, Pay Stubs, Receipts
"""

DOCUMENT_CONFIGS = {
    "W-2": {
        "queries": [
            {"Text": "What is the employee's name?", "Alias": "EmployeeName"},
            {"Text": "What is the employee's social security number?", "Alias": "EmployeeSSN"},
            {"Text": "What is the employer's name?", "Alias": "EmployerName"},
            {"Text": "What is the employer's EIN?", "Alias": "EmployerEIN"},
            {"Text": "What are the wages, tips, other compensation (Box 1)?", "Alias": "Box1_Wages"},
            {"Text": "What is the federal income tax withheld (Box 2)?", "Alias": "Box2_FederalTaxWithheld"},
            {"Text": "What are the Social Security wages (Box 3)?", "Alias": "Box3_SocialSecurityWages"},
            {"Text": "What is the Social Security tax withheld (Box 4)?", "Alias": "Box4_SocialSecurityTax"},
            {"Text": "What are the Medicare wages (Box 5)?", "Alias": "Box5_MedicareWages"},
            {"Text": "What is the Medicare tax withheld (Box 6)?", "Alias": "Box6_MedicareTax"},
            {"Text": "What is the tax year?", "Alias": "TaxYear"}
        ],
        "claude_prompt": "Extract the following fields from this W-2 form: EmployeeName, EmployeeSSN, EmployerName, EmployerEIN, Box1_Wages, Box2_FederalTaxWithheld, Box3_SocialSecurityWages, Box4_SocialSecurityTax, Box5_MedicareWages, Box6_MedicareTax, TaxYear. Return only valid JSON with numeric values as numbers.",
        "regex_patterns": {
            "Box1_Wages": r"wages.*?tips.*?compensation.*?\$?([0-9,]+\.?\d*)",
            "Box2_FederalTaxWithheld": r"federal.*?income.*?tax.*?withheld.*?\$?([0-9,]+\.?\d*)",
            "EmployeeSSN": r"employee.*?social.*?security.*?number.*?([0-9]{3}-[0-9]{2}-[0-9]{4})",
            "EmployerEIN": r"employer.*?ein.*?([0-9]{2}-[0-9]{7})",
            "TaxYear": r"(20\d{2})"
        }
    },
    "1099-NEC": {
        "queries": [
            {"Text": "What is the payer's name?", "Alias": "PayerName"},
            {"Text": "What is the payer's TIN?", "Alias": "PayerTIN"},
            {"Text": "What is the recipient's name?", "Alias": "RecipientName"},
            {"Text": "What is the recipient's TIN?", "Alias": "RecipientTIN"},
            {"Text": "What is the nonemployee compensation amount (Box 1)?", "Alias": "Box1_NonemployeeComp"},
            {"Text": "What is the federal income tax withheld (Box 4)?", "Alias": "Box4_FederalTaxWithheld"},
            {"Text": "What is the tax year?", "Alias": "TaxYear"}
        ],
        "claude_prompt": "Extract from this 1099-NEC: PayerName, PayerTIN, RecipientName, RecipientTIN, Box1_NonemployeeComp, Box4_FederalTaxWithheld, TaxYear. Return JSON.",
        "regex_patterns": {
            "Box1_NonemployeeComp": r"nonemployee.*?compensation.*?\$?([0-9,]+\.?\d*)",
            "PayerTIN": r"payer.*?tin.*?([0-9]{2}-[0-9]{7})",
            "RecipientTIN": r"recipient.*?tin.*?([0-9]{3}-[0-9]{2}-[0-9]{4})"
        }
    },
    "1099-INT": {
        "queries": [
            {"Text": "What is the payer's name?", "Alias": "PayerName"},
            {"Text": "What is the payer's TIN?", "Alias": "PayerTIN"},
            {"Text": "What is the recipient's name?", "Alias": "RecipientName"},
            {"Text": "What is the recipient's TIN?", "Alias": "RecipientTIN"},
            {"Text": "What is the interest income (Box 1)?", "Alias": "Box1_InterestIncome"},
            {"Text": "What is the federal income tax withheld (Box 4)?", "Alias": "Box4_FederalTaxWithheld"}
        ],
        "claude_prompt": "Extract from this 1099-INT: PayerName, PayerTIN, RecipientName, RecipientTIN, Box1_InterestIncome, Box4_FederalTaxWithheld. Return JSON.",
        "regex_patterns": {
            "Box1_InterestIncome": r"interest.*?income.*?\$?([0-9,]+\.?\d*)",
            "PayerTIN": r"payer.*?tin.*?([0-9]{2}-[0-9]{7})"
        }
    },
    "1098-E": {
        "queries": [
            {"Text": "Who is the lender (name of entity to whom interest was paid)?", "Alias": "LenderName"},
            {"Text": "What is the student loan interest received by lender (Box 1)?", "Alias": "Box1_StudentLoanInterest"},
            {"Text": "What is the borrower's name?", "Alias": "BorrowerName"},
            {"Text": "What is the borrower's SSN?", "Alias": "BorrowerSSN"},
            {"Text": "What is the tax year?", "Alias": "TaxYear"}
        ],
        "claude_prompt": "Extract from this 1098-E: LenderName, BorrowerName, BorrowerSSN, Box1_StudentLoanInterest, TaxYear. Return JSON.",
        "regex_patterns": {
            "Box1_StudentLoanInterest": r"student.*?loan.*?interest.*?\$?([0-9,]+\.?\d*)",
            "BorrowerSSN": r"borrower.*?ssn.*?([0-9]{3}-[0-9]{2}-[0-9]{4})"
        }
    },
    "1098": {
        "queries": [
            {"Text": "What is the lender's name?", "Alias": "LenderName"},
            {"Text": "What is the borrower's name?", "Alias": "BorrowerName"},
            {"Text": "What is the mortgage interest paid?", "Alias": "Box1_MortgageInterest"},
            {"Text": "What are the mortgage insurance premiums?", "Alias": "Box4_MortgageInsurance"},
            {"Text": "What are the points paid?", "Alias": "Box6_PointsPaid"}
        ],
        "claude_prompt": "Extract from this 1098: LenderName, BorrowerName, Box1_MortgageInterest, Box4_MortgageInsurance, Box6_PointsPaid. Return JSON.",
        "regex_patterns": {
            "Box1_MortgageInterest": r"mortgage.*?interest.*?\$?([0-9,]+\.?\d*)",
            "Box4_MortgageInsurance": r"mortgage.*?insurance.*?\$?([0-9,]+\.?\d*)"
        }
    },
    "1095-A": {
        "queries": [
            {"Text": "What is the Marketplace assigned Policy Number?", "Alias": "PolicyNumber"},
            {"Text": "What is the name of the Covered individual (subscriber)?", "Alias": "SubscriberName"},
            {"Text": "What is the subscriber's SSN?", "Alias": "SubscriberSSN"},
            {"Text": "What are the coverage start and end dates?", "Alias": "CoveragePeriod"},
            {"Text": "What is the premium amount (second lowest cost silver plan)?", "Alias": "SLCSPPremium"}
        ],
        "claude_prompt": "Extract from this 1095-A: PolicyNumber, SubscriberName, SubscriberSSN, CoveragePeriod, SLCSPPremium. Return JSON.",
        "regex_patterns": {
            "PolicyNumber": r"policy.*?number.*?([A-Z0-9-]+)",
            "SubscriberSSN": r"subscriber.*?ssn.*?([0-9]{3}-[0-9]{2}-[0-9]{4})"
        }
    },
    "1040": {
        "queries": [
            {"Text": "What is the Primary taxpayer's name?", "Alias": "PrimaryName"},
            {"Text": "What is the taxpayer's Social Security Number?", "Alias": "PrimarySSN"},
            {"Text": "What is the filing status?", "Alias": "FilingStatus"},
            {"Text": "What is the Adjusted Gross Income on Form 1040?", "Alias": "AGI"},
            {"Text": "What is the Total Tax?", "Alias": "TotalTax"},
            {"Text": "What is the Refund or Amount Owed?", "Alias": "RefundOrOwed"}
        ],
        "claude_prompt": "Extract from this 1040: PrimaryName, PrimarySSN, FilingStatus, AGI, TotalTax, RefundOrOwed. Return JSON.",
        "regex_patterns": {
            "AGI": r"adjusted.*?gross.*?income.*?\$?([0-9,]+\.?\d*)",
            "TotalTax": r"total.*?tax.*?\$?([0-9,]+\.?\d*)",
            "PrimarySSN": r"([0-9]{3}-[0-9]{2}-[0-9]{4})"
        }
    },
    "Bank Statement": {
        "queries": [
            {"Text": "What is the account holder's name?", "Alias": "AccountHolder"},
            {"Text": "What is the account number?", "Alias": "AccountNumber"},
            {"Text": "What is the statement period or date range?", "Alias": "StatementPeriod"},
            {"Text": "What is the beginning balance?", "Alias": "BeginningBalance"},
            {"Text": "What is the ending balance?", "Alias": "EndingBalance"}
        ],
        "claude_prompt": "Extract from this bank statement: AccountHolder, AccountNumber, StatementPeriod, BeginningBalance, EndingBalance. Return JSON.",
        "regex_patterns": {
            "BeginningBalance": r"beginning.*?balance.*?\$?([0-9,]+\.?\d*)",
            "EndingBalance": r"ending.*?balance.*?\$?([0-9,]+\.?\d*)",
            "AccountNumber": r"account.*?number.*?([0-9-]+)"
        }
    },
    "Pay Stub": {
        "queries": [
            {"Text": "What is the employee's name?", "Alias": "EmployeeName"},
            {"Text": "What is the pay period?", "Alias": "PayPeriod"},
            {"Text": "What is the net pay for this period?", "Alias": "NetPayCurrent"},
            {"Text": "What is the gross pay for this period?", "Alias": "GrossPayCurrent"},
            {"Text": "What is the year to date gross pay?", "Alias": "GrossPayYTD"}
        ],
        "claude_prompt": "Extract from this paystub: EmployeeName, PayPeriod, GrossPayCurrent, NetPayCurrent, GrossPayYTD. Return JSON.",
        "regex_patterns": {
            "GrossPayCurrent": r"gross.*?pay.*?current.*?\$?([0-9,]+\.?\d*)",
            "NetPayCurrent": r"net.*?pay.*?\$?([0-9,]+\.?\d*)",
            "GrossPayYTD": r"gross.*?pay.*?ytd.*?\$?([0-9,]+\.?\d*)"
        }
    },
    "Receipt": {
        "queries": [
            {"Text": "What is the merchant name on the receipt?", "Alias": "MerchantName"},
            {"Text": "What is the purchase date?", "Alias": "PurchaseDate"},
            {"Text": "What is the total amount paid?", "Alias": "TotalAmount"},
            {"Text": "What is the total sales tax?", "Alias": "SalesTax"}
        ],
        "claude_prompt": "Extract from this receipt: MerchantName, PurchaseDate, TotalAmount, SalesTax. Return JSON.",
        "regex_patterns": {
            "TotalAmount": r"total.*?\$?([0-9,]+\.?\d*)",
            "SalesTax": r"tax.*?\$?([0-9,]+\.?\d*)"
        }
    },
    "Invoice": {
        "queries": [
            {"Text": "What is the invoice number?", "Alias": "InvoiceNumber"},
            {"Text": "What is the invoice date?", "Alias": "InvoiceDate"},
            {"Text": "What is the vendor name?", "Alias": "VendorName"},
            {"Text": "What is the total amount?", "Alias": "TotalAmount"},
            {"Text": "What is the due date?", "Alias": "DueDate"}
        ],
        "claude_prompt": "Extract from this invoice: InvoiceNumber, InvoiceDate, VendorName, TotalAmount, DueDate. Return JSON.",
        "regex_patterns": {
            "InvoiceNumber": r"invoice.*?#?.*?([A-Z0-9-]+)",
            "TotalAmount": r"total.*?\$?([0-9,]+\.?\d*)"
        }
    }
}

CLASSIFICATION_KEYWORDS = {
    "W-2": ["w-2", "w2", "wage and tax statement", "employee's social security"],
    "1099-NEC": ["1099-nec", "nonemployee compensation"],
    "1099-INT": ["1099-int", "interest income"],
    "1099-DIV": ["1099-div", "dividends"],
    "1099-MISC": ["1099-misc", "miscellaneous income"],
    "1098-E": ["1098-e", "student loan interest"],
    "1098": ["1098", "mortgage interest"],
    "1095-A": ["1095-a", "health insurance marketplace"],
    "1040": ["1040", "individual income tax return"],
    "Bank Statement": ["statement", "account summary", "beginning balance", "ending balance"],
    "Pay Stub": ["pay stub", "paystub", "payroll", "earnings statement"],
    "Receipt": ["receipt", "thank you", "subtotal", "total due"],
    "Invoice": ["invoice", "bill to", "invoice number", "due date"]
}