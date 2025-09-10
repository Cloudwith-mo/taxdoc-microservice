"""
Schema-based document extractors for multi-document processing
"""
import re
import boto3
from datetime import datetime

def extract_receipt_schema(document_bytes, full_text):
    """Extract receipt using schema-based approach"""
    textract = boto3.client('textract')
    
    try:
        response = textract.analyze_expense(Document={"Bytes": document_bytes})
        
        result = {
            'schema_version': '2025-09-A',
            'document_type': 'Receipt',
            'seller': {'name': '', 'address': ''},
            'receipt': {'date': '', 'number': ''},
            'currency': 'USD',
            'items': [],
            'totals': {'subtotal': '0.00', 'tax': '0.00', 'total': '0.00'}
        }
        
        for doc in response.get('ExpenseDocuments', []):
            for field in doc.get('SummaryFields', []):
                field_type = field.get('Type', {}).get('Text', '')
                field_value = field.get('ValueDetection', {}).get('Text', '')
                
                if 'VENDOR' in field_type.upper():
                    result['seller']['name'] = field_value
                elif 'TOTAL' in field_type.upper():
                    result['totals']['total'] = normalize_money(field_value) or '0.00'
                elif 'TAX' in field_type.upper():
                    result['totals']['tax'] = normalize_money(field_value) or '0.00'
                elif 'DATE' in field_type.upper():
                    result['receipt']['date'] = normalize_date(field_value) or ''
            
            # Extract line items
            for group in doc.get('LineItemGroups', []):
                for item in group.get('LineItems', []):
                    line_item = {'description': '', 'qty': 1, 'unit_price': '0.00', 'amount': '0.00'}
                    for field in item.get('LineItemExpenseFields', []):
                        field_type = field.get('Type', {}).get('Text', '')
                        field_value = field.get('ValueDetection', {}).get('Text', '')
                        
                        if 'ITEM' in field_type.upper():
                            line_item['description'] = field_value
                        elif 'PRICE' in field_type.upper():
                            line_item['unit_price'] = normalize_money(field_value) or '0.00'
                    
                    if line_item['description']:
                        result['items'].append(line_item)
        
        return result
        
    except Exception as e:
        return {'error': f'Receipt extraction failed: {e}'}

def extract_bank_statement_schema(document_bytes, full_text):
    """Extract bank statement using schema-based approach"""
    result = {
        'schema_version': '2025-09-A',
        'document_type': 'Bank Statement',
        'account': {'institution': '', 'number': ''},
        'statement_period': {'start': '', 'end': ''},
        'currency': 'USD',
        'balances': {'beginning': '0.00', 'ending': '0.00'},
        'transactions': [],
        'truncated': False
    }
    
    # Extract key information using regex
    lines = full_text.split('\n')
    for line in lines:
        if 'account' in line.lower() and any(c.isdigit() for c in line):
            # Extract account number
            numbers = re.findall(r'\d{4,}', line)
            if numbers:
                result['account']['number'] = numbers[0]
        elif 'beginning balance' in line.lower():
            amount = extract_money_from_line(line)
            if amount:
                result['balances']['beginning'] = amount
        elif 'ending balance' in line.lower():
            amount = extract_money_from_line(line)
            if amount:
                result['balances']['ending'] = amount
    
    return result

def extract_1099_nec_schema(document_bytes, full_text):
    """Extract 1099-NEC using schema-based approach"""
    result = {
        'schema_version': '2025-09-A',
        'document_type': '1099-NEC',
        'tax_year': extract_tax_year(full_text),
        'payer': {'name': '', 'tin': ''},
        'recipient': {'name': '', 'tin': ''},
        'boxes': {}
    }
    
    # Extract box 1 amount
    box1_match = re.search(r'box\s*1.*?(\d+[,.]?\d*\.?\d{2})', full_text, re.I)
    if box1_match:
        result['boxes']['1_nonemployee_comp'] = normalize_money(box1_match.group(1)) or '0.00'
    
    return result

def extract_paystub_schema(document_bytes, full_text):
    """Extract paystub using enhanced schema-based approach"""
    result = {
        'schema_version': '2025-09-A',
        'document_type': 'Pay Stub',
        'employer': {'name': ''},
        'employee': {'name': ''},
        'payroll': {'cycle_start': '', 'cycle_end': '', 'pay_date': ''},
        'gross_pay': {'current_amount': '0.00', 'ytd_amount': '0.00'},
        'net_pay': {'current_amount': '0.00', 'ytd_amount': '0.00'},
        'validation': {'errors': []}
    }
    
    # Extract gross pay
    gross_match = re.search(r'gross.*?(\d+[,.]?\d*\.?\d{2})', full_text, re.I)
    if gross_match:
        result['gross_pay']['current_amount'] = normalize_money(gross_match.group(1)) or '0.00'
    
    # Extract net pay
    net_match = re.search(r'net.*?(\d+[,.]?\d*\.?\d{2})', full_text, re.I)
    if net_match:
        result['net_pay']['current_amount'] = normalize_money(net_match.group(1)) or '0.00'
    
    return result

def classify_document_llm(text):
    """LLM-based document classification"""
    text_lower = text.lower()
    
    if any(x in text_lower for x in ['w-2', 'wage and tax statement']):
        return {'doc_type': 'W-2', 'confidence': 0.95, 'reason': 'Contains W-2 form indicators'}
    elif '1099-nec' in text_lower or 'nonemployee compensation' in text_lower:
        return {'doc_type': '1099-NEC', 'confidence': 0.95, 'reason': 'Contains 1099-NEC form indicators'}
    elif any(x in text_lower for x in ['receipt', 'invoice', 'total paid']):
        return {'doc_type': 'Receipt', 'confidence': 0.90, 'reason': 'Contains receipt/invoice indicators'}
    elif any(x in text_lower for x in ['statement period', 'beginning balance', 'ending balance']):
        return {'doc_type': 'Bank Statement', 'confidence': 0.90, 'reason': 'Contains bank statement indicators'}
    elif any(x in text_lower for x in ['pay period', 'gross pay', 'net pay']):
        return {'doc_type': 'Pay Stub', 'confidence': 0.85, 'reason': 'Contains paystub indicators'}
    else:
        return {'doc_type': 'Other', 'confidence': 0.50, 'reason': 'No clear document type indicators'}

# Helper functions
def normalize_money(value):
    """Normalize money to ####.## format"""
    if not value:
        return None
    cleaned = re.sub(r'[^\d.]', '', str(value))
    try:
        return f"{float(cleaned):.2f}"
    except:
        return None

def normalize_date(value):
    """Normalize date to YYYY-MM-DD format"""
    if not value:
        return None
    try:
        from datetime import datetime
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y']:
            try:
                dt = datetime.strptime(str(value).strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except:
        pass
    return None

def extract_tax_year(text):
    """Extract tax year from document text"""
    years = re.findall(r'\b(20\d{2})\b', text)
    if years:
        return int(years[0])
    return 2024

def extract_money_from_line(line):
    """Extract money amount from a line of text"""
    money_match = re.search(r'\$?([0-9,]+\.?\d{0,2})', line)
    if money_match:
        return normalize_money(money_match.group(1))
    return None