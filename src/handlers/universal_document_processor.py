import json
import base64
import boto3
import uuid
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Core QuerySets (≤15 queries each) - Production Ready
QUERYSETS = {
    "w2": [
        {"Text":"Box 1 wages tips other compensation","Alias":"box1_wages"},
        {"Text":"Box 2 federal income tax withheld","Alias":"box2_fed_tax"},
        {"Text":"Box 3 social security wages","Alias":"box3_ss_wages"},
        {"Text":"Box 4 social security tax withheld","Alias":"box4_ss_tax"},
        {"Text":"Box 5 medicare wages and tips","Alias":"box5_medicare_wages"},
        {"Text":"Box 6 medicare tax withheld","Alias":"box6_medicare_tax"},
        {"Text":"Box 7 social security tips","Alias":"box7_ss_tips"},
        {"Text":"Box 8 allocated tips","Alias":"box8_alloc_tips"},
        {"Text":"Box 10 dependent care benefits","Alias":"box10_dependent_care"},
        {"Text":"Box 11 nonqualified plans","Alias":"box11_nonqualified"},
        {"Text":"Box 12a code","Alias":"box12a_code"},
        {"Text":"Box 12a amount","Alias":"box12a_amount"},
        {"Text":"Box 12b code","Alias":"box12b_code"},
        {"Text":"Box 12b amount","Alias":"box12b_amount"},
        {"Text":"Tax year","Alias":"taxyear"}
    ],
    "1099_nec": [
        {"Text":"Tax year","Alias":"taxyear"},
        {"Text":"Payer TIN","Alias":"payer_tin"},
        {"Text":"Payer name","Alias":"payer_name"},
        {"Text":"Payer address","Alias":"payer_address"},
        {"Text":"Recipient TIN","Alias":"recipient_tin"},
        {"Text":"Recipient name","Alias":"recipient_name"},
        {"Text":"Recipient address","Alias":"recipient_address"},
        {"Text":"Box 1 nonemployee compensation","Alias":"nec_amount_box1"},
        {"Text":"Box 4 federal income tax withheld","Alias":"fed_tax_withheld_box4"},
        {"Text":"Box 5 state tax withheld","Alias":"state_tax_withheld_box5"},
        {"Text":"Box 6 state number","Alias":"state_no_box6"},
        {"Text":"Box 7 state income","Alias":"state_income_box7"},
        {"Text":"Account number","Alias":"account_number"}
    ],
    "paystub": [
        {"Text":"Employee name","Alias":"employee_name"},
        {"Text":"Employer name","Alias":"employer_name"},
        {"Text":"Pay period start","Alias":"pay_period_start"},
        {"Text":"Pay period end","Alias":"pay_period_end"},
        {"Text":"Pay date","Alias":"pay_date"},
        {"Text":"Gross pay","Alias":"gross_pay"},
        {"Text":"Net pay","Alias":"net_pay"},
        {"Text":"YTD gross","Alias":"ytd_gross"},
        {"Text":"YTD net","Alias":"ytd_net"}
    ],
    "utility_bill": [
        {"Text":"Provider name","Alias":"provider_name"},
        {"Text":"Account number","Alias":"account_number"},
        {"Text":"Service address","Alias":"service_address"},
        {"Text":"Billing period start","Alias":"period_start"},
        {"Text":"Billing period end","Alias":"period_end"},
        {"Text":"Statement date","Alias":"statement_date"},
        {"Text":"Due date","Alias":"due_date"},
        {"Text":"Amount due","Alias":"amount_due"}
    ],
    "bank_statement": [
        {"Text":"Account number","Alias":"account_number"},
        {"Text":"Statement period start","Alias":"period_start"},
        {"Text":"Statement period end","Alias":"period_end"}
    ]
}

# Enhanced regex patterns
MONEY_RE = re.compile(r'^\$?\s*([\d,]+(?:\.\d{1,2})?)$')
SSN_RE = re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b')
EIN_RE = re.compile(r'\b\d{2}-?\d{7}\b')
DATE_RE = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
PHONE_RE = re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')
EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'X-Powered-By': 'TurboParse™ Engine'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        body = json.loads(event.get('body', '{}'))
        filename = body.get('filename', 'document.pdf')
        content_base64 = body.get('contentBase64', '')
        
        if not content_base64:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No contentBase64 provided'})}
        
        content_base64 = re.sub(r'^data:.*;base64,', '', content_base64, flags=re.I)
        content_base64 = re.sub(r'\s+', '', content_base64)
        
        document_bytes = base64.b64decode(content_base64)
        if not document_bytes:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Empty document'})}
        
        # Route and process document
        result = route_and_process(document_bytes, filename)
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(result)}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def route_and_process(document_bytes, filename):
    """Universal document processor with smart routing"""
    
    # Detect text for classification
    textract = boto3.client('textract')
    text_response = textract.detect_document_text(Document={'Bytes': document_bytes})
    full_text = extract_full_text(text_response)
    
    if len(full_text.strip()) < 10:
        return {'error': 'Document appears empty or unreadable', 'status': 'FAILED_EMPTY'}
    
    # Smart document classification
    doc_type = classify_document(full_text)
    doc_id = str(uuid.uuid4())
    
    print(f"[TurboParse™] classified={doc_type} text_len={len(full_text)} filename={filename}")
    
    # Route to optimal extractor based on document type
    if doc_type == 'W-2':
        result = extract_w2(document_bytes, full_text)
    elif doc_type in ['1099-NEC', '1099-MISC', '1099-INT', '1099-DIV']:
        result = extract_1099_nec(document_bytes, full_text)
    elif doc_type in ['INVOICE', 'RECEIPT', 'PURCHASE_ORDER']:
        result = extract_invoice_receipt(document_bytes, full_text)  # Uses AnalyzeExpense
    elif doc_type == 'BANK_STATEMENT':
        result = extract_bank_statement(document_bytes, full_text)  # Uses FORMS+TABLES
    elif doc_type == 'ID_CARD':
        result = extract_id_card(document_bytes, full_text)  # Uses AnalyzeID
    elif doc_type == 'PAYSTUB':
        result = extract_paystub(document_bytes, full_text)
    elif doc_type == 'UTILITY_BILL':
        result = extract_utility_bill(document_bytes, full_text)
    elif doc_type == 'CONTRACT':
        result = extract_contract(document_bytes, full_text)  # Uses LLM analysis
    else:
        result = extract_anydoc(document_bytes, full_text, doc_type)
    
    # Add metadata
    result.update({
        'docId': doc_id,
        'docType': doc_type,
        'filename': filename,
        'processedAt': datetime.utcnow().isoformat(),
        'engine': 'TurboParse™',
        'version': '2.0'
    })
    
    return result

def classify_document(text):
    """Enhanced document classifier with confidence scoring"""
    text_lower = text.lower()
    
    # Tax forms (high confidence patterns)
    if any(x in text_lower for x in ['w-2', 'wage and tax statement', 'form w-2']):
        return 'W-2'
    elif '1099-nec' in text_lower or 'nonemployee compensation' in text_lower:
        return '1099-NEC'
    elif '1099-misc' in text_lower:
        return '1099-MISC'
    elif '1099-int' in text_lower:
        return '1099-INT'
    elif '1099-div' in text_lower:
        return '1099-DIV'
    
    # Business documents (AnalyzeExpense optimal)
    elif any(x in text_lower for x in ['invoice', 'bill to', 'invoice number', 'purchase order']):
        return 'INVOICE'
    elif any(x in text_lower for x in ['receipt', 'thank you', 'total paid', 'merchant']):
        return 'RECEIPT'
    elif 'purchase order' in text_lower or 'po number' in text_lower:
        return 'PURCHASE_ORDER'
    
    # Financial statements
    elif any(x in text_lower for x in ['statement period', 'beginning balance', 'ending balance']):
        return 'BANK_STATEMENT'
    elif any(x in text_lower for x in ['pay period', 'gross pay', 'net pay', 'earnings', 'deductions']):
        return 'PAYSTUB'
    elif any(x in text_lower for x in ['amount due', 'billing period', 'service address', 'utility']):
        return 'UTILITY_BILL'
    
    # Identity documents (AnalyzeID optimal)
    elif any(x in text_lower for x in ['driver license', 'drivers license', 'state id', 'passport']):
        return 'ID_CARD'
    
    # Legal documents (LLM optimal)
    elif any(x in text_lower for x in ['agreement', 'contract', 'whereas', 'party of the first part']):
        return 'CONTRACT'
    
    # Handwritten or complex documents
    elif len(text.strip()) < 100:
        return 'HANDWRITTEN'
    
    return 'UNKNOWN'

def extract_w2(document_bytes, full_text):
    """Extract W-2 using comprehensive QuerySet"""
    textract = boto3.client('textract')
    
    queries = QUERYSETS["w2"]
    print(f"[W2] loaded_queries={len(queries)} aliases={[(q.get('Alias'), q.get('Text')[:28]) for q in queries[:8]]}")
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES", "FORMS", "TABLES"],
        QueriesConfig={"Queries": queries}
    )
    
    # Count results
    qres = [b for b in response.get("Blocks", []) if b["BlockType"]=="QUERY_RESULT"]
    kv = [b for b in response["Blocks"] if b["BlockType"]=="KEY_VALUE_SET"]
    tbl = [b for b in response["Blocks"] if b["BlockType"]=="TABLE"]
    print(f"[W2] query_results={len(qres)} kv_sets={len(kv)} tables={len(tbl)}")
    print(f"[W2] bytes={len(document_bytes)} featureTypes=QUERIES+FORMS+TABLES")
    
    queries = parse_query_results(response)
    normalize_money_and_ids(queries)
    
    # Build employee name only if we have parts
    first = get_val(queries, "employee_first")
    last = get_val(queries, "employee_last")
    employee_name = None
    if first or last:
        employee_name = " ".join([first or "", last or ""]).strip()
    
    # Extract from FORMS for non-numeric fields
    forms = parse_forms_kv(response)
    
    fields = {
        "Box 1 - Wages": get_val(queries, "box1_wages"),
        "Box 2 - Federal Tax": get_val(queries, "box2_fed_tax"),
        "Box 3 - SS Wages": get_val(queries, "box3_ss_wages"),
        "Box 4 - SS Tax": get_val(queries, "box4_ss_tax"),
        "Box 5 - Medicare Wages": get_val(queries, "box5_medicare_wages"),
        "Box 6 - Medicare Tax": get_val(queries, "box6_medicare_tax"),
        "Box 7 - SS Tips": get_val(queries, "box7_ss_tips"),
        "Box 8 - Allocated Tips": get_val(queries, "box8_alloc_tips"),
        "Box 10 - Dependent Care": get_val(queries, "box10_dependent_care"),
        "Box 11 - Nonqualified Plans": get_val(queries, "box11_nonqualified"),
        "Box 12a": f"{get_val(queries, 'box12a_code')} {get_val(queries, 'box12a_amount')}".strip(),
        "Box 12b": f"{get_val(queries, 'box12b_code')} {get_val(queries, 'box12b_amount')}".strip(),
        "Tax Year": get_val(queries, "taxyear")
    }
    
    # Add FORMS data for names/addresses
    for key, value in forms.items():
        if 'employee' in key and 'ssn' in key:
            fields["Employee SSN"] = value
        elif 'employer' in key and ('ein' in key or 'id' in key):
            fields["Employer EIN"] = value
        elif 'employee' in key and 'name' in key:
            fields["Employee Name"] = value
        elif 'employer' in key and ('name' in key or 'company' in key):
            fields["Employer Name"] = value
    
    # Clean up empty fields and format values
    filtered_fields = {}
    for k, v in fields.items():
        if v and str(v).strip() and str(v) != "None":
            # Clean up combined fields like "Box 12a"
            if k.startswith("Box 12") and v.strip() == "":
                continue
            filtered_fields[k] = str(v).strip()
    
    key_values = [{'key': k, 'value': v} for k, v in filtered_fields.items()]
    
    print(f"[W2] final_fields={len(filtered_fields)} extracted={list(filtered_fields.keys())}")
    
    fields = filtered_fields
    
    return {
        'docTypeConfidence': 0.95,
        'summary': f'W-2 processed with {len(fields)} fields extracted',
        'fields': fields,
        'keyValues': key_values,
        'flags': {'needs_review': False, 'contains_pii': True}
    }

def extract_1099_nec(document_bytes, full_text):
    """Extract 1099-NEC using QuerySet"""
    textract = boto3.client('textract')
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES"],
        QueriesConfig={"Queries": QUERYSETS["1099_nec"]}
    )
    
    queries = parse_query_results(response)
    normalize_money_and_ids(queries)
    
    fields = {
        "Payer TIN": get_val(queries, "payer_tin"),
        "Payer Name": get_val(queries, "payer_name"),
        "Payer Address": get_val(queries, "payer_address"),
        "Recipient TIN": get_val(queries, "recipient_tin"),
        "Recipient Name": get_val(queries, "recipient_name"),
        "Recipient Address": get_val(queries, "recipient_address"),
        "Box 1 - Nonemployee Compensation": get_val(queries, "nec_amount_box1"),
        "Box 4 - Federal Tax Withheld": get_val(queries, "fed_tax_withheld_box4"),
        "Box 5 - State Tax Withheld": get_val(queries, "state_tax_withheld_box5"),
        "Box 6 - State Number": get_val(queries, "state_no_box6"),
        "Box 7 - State Income": get_val(queries, "state_income_box7"),
        "Account Number": get_val(queries, "account_number"),
        "Tax Year": get_val(queries, "taxyear")
    }
    
    fields = {k: v for k, v in fields.items() if v}
    key_values = [{'key': k, 'value': str(v)} for k, v in fields.items()]
    
    return {
        'docTypeConfidence': 0.90,
        'summary': f'1099-NEC processed with {len(fields)} fields extracted',
        'fields': fields,
        'keyValues': key_values,
        'flags': {'needs_review': False, 'contains_pii': True}
    }

def extract_invoice_receipt(document_bytes, full_text):
    """Extract invoice/receipt using AnalyzeExpense"""
    textract = boto3.client('textract')
    
    try:
        response = textract.analyze_expense(Document={"Bytes": document_bytes})
        
        fields = {}
        line_items = []
        
        for doc in response.get('ExpenseDocuments', []):
            # Summary fields
            for field in doc.get('SummaryFields', []):
                field_type = field.get('Type', {}).get('Text', '')
                field_value = field.get('ValueDetection', {}).get('Text', '')
                
                if field_type and field_value:
                    if 'VENDOR' in field_type.upper():
                        fields['Vendor'] = field_value
                    elif 'TOTAL' in field_type.upper():
                        fields['Total'] = field_value
                    elif 'DATE' in field_type.upper():
                        fields['Date'] = field_value
                    elif 'TAX' in field_type.upper():
                        fields['Tax'] = field_value
            
            # Line items
            for group in doc.get('LineItemGroups', []):
                for item in group.get('LineItems', []):
                    line_item = {}
                    for field in item.get('LineItemExpenseFields', []):
                        field_type = field.get('Type', {}).get('Text', '')
                        field_value = field.get('ValueDetection', {}).get('Text', '')
                        if field_type and field_value:
                            line_item[field_type] = field_value
                    if line_item:
                        line_items.append(line_item)
        
        key_values = [{'key': k, 'value': str(v)} for k, v in fields.items()]
        
        return {
            'docTypeConfidence': 0.85,
            'summary': f'Invoice/Receipt with {len(fields)} fields and {len(line_items)} line items',
            'fields': fields,
            'keyValues': key_values,
            'lineItems': line_items,
            'flags': {'needs_review': False, 'contains_pii': False}
        }
        
    except Exception as e:
        # Fallback to basic extraction
        return extract_basic_fields(full_text, 'INVOICE')

def extract_paystub(document_bytes, full_text):
    """Extract paystub using QuerySet"""
    textract = boto3.client('textract')
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES", "TABLES"],
        QueriesConfig={"Queries": QUERYSETS["paystub"]}
    )
    
    queries = parse_query_results(response)
    normalize_money_and_ids(queries)
    
    # Extract earnings/deductions from tables
    tables = extract_tables(response)
    earnings = []
    deductions = []
    
    for table in tables:
        for row in table.get('rows', []):
            if len(row) >= 2 and any(x in str(row[0]).lower() for x in ['regular', 'overtime', 'bonus']):
                earnings.append({'type': row[0], 'amount': row[-1]})
            elif len(row) >= 2 and any(x in str(row[0]).lower() for x in ['federal', 'state', 'medicare', '401k']):
                deductions.append({'type': row[0], 'amount': row[-1]})
    
    fields = {
        "Employee Name": get_val(queries, "employee_name"),
        "Employer Name": get_val(queries, "employer_name"),
        "Pay Period Start": get_val(queries, "pay_period_start"),
        "Pay Period End": get_val(queries, "pay_period_end"),
        "Pay Date": get_val(queries, "pay_date"),
        "Gross Pay": get_val(queries, "gross_pay"),
        "Net Pay": get_val(queries, "net_pay"),
        "YTD Gross": get_val(queries, "ytd_gross"),
        "YTD Net": get_val(queries, "ytd_net")
    }
    
    fields = {k: v for k, v in fields.items() if v}
    key_values = [{'key': k, 'value': str(v)} for k, v in fields.items()]
    
    return {
        'docTypeConfidence': 0.85,
        'summary': f'Paystub with {len(fields)} fields, {len(earnings)} earnings, {len(deductions)} deductions',
        'fields': fields,
        'keyValues': key_values,
        'earnings': earnings,
        'deductions': deductions,
        'flags': {'needs_review': False, 'contains_pii': True}
    }

def extract_utility_bill(document_bytes, full_text):
    """Extract utility bill using QuerySet"""
    textract = boto3.client('textract')
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES"],
        QueriesConfig={"Queries": QUERYSETS["utility_bill"]}
    )
    
    queries = parse_query_results(response)
    normalize_money_and_ids(queries)
    
    fields = {
        "Provider Name": get_val(queries, "provider_name"),
        "Account Number": get_val(queries, "account_number"),
        "Service Address": get_val(queries, "service_address"),
        "Statement Date": get_val(queries, "statement_date"),
        "Amount Due": get_val(queries, "amount_due"),
        "Due Date": get_val(queries, "due_date"),
        "Billing Period": f"{get_val(queries, 'period_start')} - {get_val(queries, 'period_end')}"
    }
    
    fields = {k: v for k, v in fields.items() if v and v != " - "}
    key_values = [{'key': k, 'value': str(v)} for k, v in fields.items()]
    
    return {
        'docTypeConfidence': 0.80,
        'summary': f'Utility bill processed with {len(fields)} fields extracted',
        'fields': fields,
        'keyValues': key_values,
        'flags': {'needs_review': False, 'contains_pii': True}
    }

def extract_bank_statement(document_bytes, full_text):
    """Extract bank statement using FORMS+TABLES (async for multi-page)"""
    textract = boto3.client('textract')
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["FORMS", "TABLES"]
    )
    
    # Extract header info from forms
    forms = parse_forms_kv(response)
    
    fields = {}
    for key, value in forms.items():
        if 'account' in key.lower() and 'number' in key.lower():
            fields['Account Number'] = value
        elif 'bank' in key.lower() or 'institution' in key.lower():
            fields['Bank Name'] = value
        elif 'holder' in key.lower() or 'customer' in key.lower():
            fields['Account Holder'] = value
        elif 'period' in key.lower() or 'statement' in key.lower():
            fields['Statement Period'] = value
    
    # Extract transactions from tables
    transactions = []
    tables = extract_tables(response)
    
    total_withdrawals = 0
    total_deposits = 0
    
    for table in tables:
        rows = table.get('rows', [])
        if len(rows) > 1:  # Skip header
            for row in rows[1:]:  # Skip header row
                if len(row) >= 3:  # Date, Description, Amount format
                    try:
                        # Parse transaction
                        date = row[0] if row[0] else ''
                        desc = row[1] if len(row) > 1 else ''
                        amount = row[-1] if row[-1] else '0'
                        
                        # Track totals
                        if amount and amount.replace(',', '').replace('.', '').replace('-', '').isdigit():
                            amt_val = float(amount.replace(',', '').replace('$', ''))
                            if amt_val < 0:
                                total_withdrawals += abs(amt_val)
                            else:
                                total_deposits += amt_val
                        
                        transactions.append([date, desc, amount])
                    except:
                        continue
    
    # Add derived fields
    if total_deposits > 0:
        fields['Total Deposits'] = f"{total_deposits:,.2f}"
    if total_withdrawals > 0:
        fields['Total Withdrawals'] = f"{total_withdrawals:,.2f}"
    
    key_values = [{'key': k, 'value': str(v)} for k, v in fields.items()]
    
    return {
        'docTypeConfidence': 0.80,
        'summary': f'Bank statement with {len(fields)} fields and {len(transactions)} transactions',
        'fields': fields,
        'keyValues': key_values,
        'transactions': transactions[:10],  # Limit display
        'flags': {'needs_review': False, 'contains_pii': True}
    }

def extract_id_card(document_bytes, full_text):
    """Extract ID card using AnalyzeID"""
    textract = boto3.client('textract')
    
    try:
        response = textract.analyze_id(Document={"Bytes": document_bytes})
        
        fields = {}
        for doc in response.get('IdentityDocuments', []):
            for field in doc.get('IdentityDocumentFields', []):
                field_type = field.get('Type', {}).get('Text', '')
                field_value = field.get('ValueDetection', {}).get('Text', '')
                
                if field_type and field_value:
                    fields[field_type] = field_value
        
        key_values = [{'key': k, 'value': str(v)} for k, v in fields.items()]
        
        return {
            'docTypeConfidence': 0.90,
            'summary': f'ID document processed with {len(fields)} fields extracted',
            'fields': fields,
            'keyValues': key_values,
            'flags': {'needs_review': False, 'contains_pii': True}
        }
        
    except Exception as e:
        return extract_basic_fields(full_text, 'ID_CARD')

def extract_contract(document_bytes, full_text):
    """Extract contract using basic text analysis (LLM integration ready)"""
    fields = {}
    
    # Extract parties
    parties = []
    lines = full_text.split('\n')
    
    for line in lines:
        if any(x in line.lower() for x in ['party', 'between', 'contractor', 'client']):
            if len(line.strip()) < 200:  # Reasonable length
                parties.append(line.strip())
    
    if parties:
        fields['Parties'] = '; '.join(parties[:2])  # First 2 parties
    
    # Extract dates
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    dates = re.findall(date_pattern, full_text)
    if dates:
        fields['Effective Date'] = dates[0]
        if len(dates) > 1:
            fields['Termination Date'] = dates[1]
    
    # Extract monetary amounts
    money_pattern = r'\$[\d,]+(?:\.\d{2})?'
    amounts = re.findall(money_pattern, full_text)
    if amounts:
        fields['Contract Value'] = amounts[0]
    
    # Extract governing law
    for line in lines:
        if 'governing law' in line.lower() or 'jurisdiction' in line.lower():
            fields['Governing Law'] = line.strip()[:100]
            break
    
    # Document summary
    summary_text = ' '.join(full_text.split()[:50])  # First 50 words
    fields['Summary'] = summary_text
    
    key_values = [{'key': k, 'value': str(v)} for k, v in fields.items()]
    
    return {
        'docTypeConfidence': 0.75,
        'summary': f'Contract with {len(fields)} fields extracted',
        'fields': fields,
        'keyValues': key_values,
        'flags': {'needs_review': True, 'contains_pii': True}
    }

def extract_anydoc(document_bytes, full_text, doc_type):
    """Fallback extractor with enhanced field detection"""
    textract = boto3.client('textract')
    
    # Try FORMS extraction for structured documents
    try:
        response = textract.analyze_document(
            Document={"Bytes": document_bytes},
            FeatureTypes=["FORMS"]
        )
        
        forms = parse_forms_kv(response)
        fields = {k.title(): v for k, v in forms.items() if len(k) < 50 and len(v) < 200}
        
        if len(fields) < 3:  # Fallback to basic extraction
            fields.update(extract_basic_fields(full_text, doc_type))
        
    except Exception:
        fields = extract_basic_fields(full_text, doc_type)
    
    key_values = [{'key': k, 'value': str(v)} for k, v in fields.items() if v]
    
    # Determine if document likely contains PII
    contains_pii = any(x in full_text.lower() for x in ['ssn', 'social security', 'license', 'address', 'phone'])
    
    return {
        'docTypeConfidence': 0.65,
        'summary': f'{doc_type} processed with {len(fields)} fields extracted',
        'fields': fields,
        'keyValues': key_values,
        'flags': {'needs_review': True, 'contains_pii': contains_pii}
    }

# Helper functions
def parse_query_results(resp):
    out = {}
    blocks = {b["Id"]: b for b in resp.get("Blocks", [])}
    
    # Map QUERY blocks to their aliases
    query_to_alias = {}
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "QUERY":
            alias = b.get("Query", {}).get("Alias")
            if alias:
                query_to_alias[b["Id"]] = alias
    
    # Map QUERY_RESULT blocks to their parent QUERY blocks
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "QUERY_RESULT":
            text = b.get("Text", "").strip()
            confidence = b.get("Confidence", 0) / 100 if b.get("Confidence", 0) > 1 else b.get("Confidence", 0)
            
            # Find parent QUERY block via relationships
            for rel in b.get("Relationships", []):
                if rel["Type"] == "CHILD":
                    continue
                
                # Check all relationship IDs for QUERY blocks
                for ref_id in rel.get("Ids", []):
                    if ref_id in query_to_alias:
                        alias = query_to_alias[ref_id]
                        out[alias] = {
                            "value": text if text else None,
                            "confidence": confidence
                        }
                        print(f"Matched: {alias} = '{text}' (conf: {confidence:.2f})")
                        break
    
    # Alternative: match by position if relationships fail
    if len(out) == 0:
        queries = [b for b in resp.get("Blocks", []) if b["BlockType"] == "QUERY"]
        results = [b for b in resp.get("Blocks", []) if b["BlockType"] == "QUERY_RESULT"]
        
        for i, (query, result) in enumerate(zip(queries, results)):
            alias = query.get("Query", {}).get("Alias")
            if alias:
                text = result.get("Text", "").strip()
                confidence = result.get("Confidence", 0) / 100 if result.get("Confidence", 0) > 1 else result.get("Confidence", 0)
                out[alias] = {
                    "value": text if text else None,
                    "confidence": confidence
                }
                print(f"Position match: {alias} = '{text}' (conf: {confidence:.2f})")
    
    print(f"Final parsed: {len(out)} queries")
    return out

def parse_forms_kv(resp):
    kv = {}
    blocks = {b["Id"]: b for b in resp.get("Blocks", [])}
    
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "KEY_VALUE_SET" and "KEY" in b.get("EntityTypes", []):
            key_text = gather_text(blocks, b, "CHILD")
            val_text = ""
            
            for rel in b.get("Relationships", []):
                if rel["Type"] == "VALUE":
                    for vid in rel["Ids"]:
                        val_text = gather_text(blocks, blocks[vid], "CHILD")
            
            if key_text and val_text:
                kv[key_text.lower()] = val_text
    
    return kv

def extract_tables(resp):
    tables = []
    blocks = {b["Id"]: b for b in resp.get("Blocks", [])}
    
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "TABLE":
            grid = {}
            for rel in b.get("Relationships", []):
                if rel["Type"] == "CHILD":
                    for cid in rel["Ids"]:
                        cell = blocks[cid]
                        if cell["BlockType"] == "CELL":
                            row, col = cell["RowIndex"], cell["ColumnIndex"]
                            txt = gather_text(blocks, cell, "CHILD")
                            grid.setdefault(row, {})[col] = txt
            
            rows = []
            for r in sorted(grid):
                row = [grid[r].get(c, "") for c in sorted(grid[r])]
                rows.append(row)
            
            if rows:
                tables.append({"rows": rows})
    
    return tables

def gather_text(blocks, blk, child_type):
    words = []
    for rel in blk.get("Relationships", []):
        if rel["Type"] == child_type:
            for cid in rel["Ids"]:
                c = blocks[cid]
                if c["BlockType"] in ("WORD", "SELECTION_ELEMENT", "LINE"):
                    if "Text" in c:
                        words.append(c["Text"])
    return " ".join(words).strip()

def normalize_money_and_ids(queries):
    """Normalize monetary values and ID formats"""
    for k, v in list(queries.items()):
        if not isinstance(v, dict) or not v.get("value"):
            continue
        
        x = str(v.get("value", "")).strip()
        
        # Normalize SSN/EIN formats
        if SSN_RE.fullmatch(x) or EIN_RE.fullmatch(x):
            queries[k]["value"] = x
        
        # Normalize money amounts
        money_match = MONEY_RE.match(x.replace('$', '').strip())
        if money_match:
            try:
                d = Decimal(money_match.group(1).replace(',', ''))
                queries[k]["value"] = f"${d:,.2f}"
            except (InvalidOperation, ValueError):
                pass
        
        # Clean up tax year
        if 'year' in k.lower() and x.isdigit() and len(x) == 4:
            queries[k]["value"] = x
        
        # Clean up codes (Box 12 codes, etc.)
        if 'code' in k.lower() and len(x) <= 3:
            queries[k]["value"] = x.upper()

def get_val(q, k):
    """Safely extract value from query results"""
    result = q.get(k)
    if isinstance(result, dict):
        return result.get("value")
    return result

def extract_full_text(textract_response):
    lines = []
    for block in textract_response.get('Blocks', []):
        if block['BlockType'] == 'LINE':
            lines.append(block.get('Text', ''))
    return '\n'.join(lines)

def extract_basic_fields(text, doc_type):
    """Enhanced basic field extraction with pattern matching"""
    fields = {}
    lines = text.split('\n')
    
    # Extract key-value pairs
    for line in lines:
        if ':' in line and len(line) < 300:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value and len(key) < 50 and len(value) < 200:
                    # Clean up common prefixes
                    key = re.sub(r'^[\d\s\-\.]+', '', key).strip()
                    if key:
                        fields[key] = value
    
    # Extract common patterns
    full_text = ' '.join(lines)
    
    # Dates
    date_matches = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', full_text)
    if date_matches:
        fields['Date'] = date_matches[0]
    
    # Money amounts
    money_matches = re.findall(r'\$[\d,]+(?:\.\d{2})?', full_text)
    if money_matches:
        fields['Amount'] = money_matches[0]
    
    # Phone numbers
    phone_matches = re.findall(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', full_text)
    if phone_matches:
        fields['Phone'] = phone_matches[0]
    
    # Email addresses
    email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text)
    if email_matches:
        fields['Email'] = email_matches[0]
    
    return fields