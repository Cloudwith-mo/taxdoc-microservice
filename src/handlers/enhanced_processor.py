import json
import base64
import boto3
import uuid
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from extractor_core import (
    collect_candidates, resolve_field, validate_document, 
    check_acceptance, normalize_value
)
from llm_verifier import enhance_fields_with_llm, calculate_completeness_score

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
        {"Text":"Recipient TIN","Alias":"recipient_tin"},
        {"Text":"Recipient name","Alias":"recipient_name"},
        {"Text":"Box 1 nonemployee compensation","Alias":"nec_amount_box1"},
        {"Text":"Box 4 federal income tax withheld","Alias":"fed_tax_withheld_box4"},
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
    ]
}

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    start_time = time.time()
    llm_calls = 0
    
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
        
        # Route and process with 3-layer architecture
        result, llm_calls = route_and_process_enhanced(document_bytes, filename)
        
        # Emit telemetry
        processing_time = int((time.time() - start_time) * 1000)
        emit_processing_metrics(
            result.get('docType', 'UNKNOWN'),
            len(result.get('fields', {})),
            processing_time,
            llm_calls,
            result.get('completeness_score', 0)
        )
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(result)}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def route_and_process_enhanced(document_bytes, filename):
    """Enhanced document processor with 3-layer architecture"""
    llm_calls = 0
    
    # Detect text for classification
    textract = boto3.client('textract')
    text_response = textract.detect_document_text(Document={'Bytes': document_bytes})
    full_text = extract_full_text(text_response)
    
    if len(full_text.strip()) < 10:
        return {'error': 'Document appears empty or unreadable', 'status': 'FAILED_EMPTY'}, llm_calls
    
    # Smart document classification
    doc_type = classify_document(full_text)
    doc_id = str(uuid.uuid4())
    
    print(f"[ROUTER] classified={doc_type} text_len={len(full_text)} filename={filename}")
    
    # Route to optimal extractor
    if doc_type == 'W-2':
        result, llm_calls = extract_w2_enhanced(document_bytes, full_text)
    elif doc_type in ['1099-NEC', '1099-MISC']:
        result, llm_calls = extract_1099_enhanced(document_bytes, full_text)
    elif doc_type in ['INVOICE', 'RECEIPT']:
        result, llm_calls = extract_invoice_enhanced(document_bytes, full_text)
    elif doc_type == 'PAYSTUB':
        result, llm_calls = extract_paystub_enhanced(document_bytes, full_text)
    elif doc_type == 'UTILITY_BILL':
        result, llm_calls = extract_utility_enhanced(document_bytes, full_text)
    elif doc_type == 'BANK_STATEMENT':
        result, llm_calls = extract_bank_enhanced(document_bytes, full_text)
    elif doc_type == 'ID_CARD':
        result, llm_calls = extract_id_enhanced(document_bytes, full_text)
    else:
        result, llm_calls = extract_anydoc_enhanced(document_bytes, full_text, doc_type)
    
    # Add metadata
    result.update({
        'docId': doc_id,
        'docType': doc_type,
        'filename': filename,
        'processedAt': datetime.utcnow().isoformat()
    })
    
    return result, llm_calls

def extract_w2_enhanced(document_bytes, full_text):
    """Extract W-2 using 3-layer architecture"""
    textract = boto3.client('textract')
    llm_calls = 0
    
    queries = QUERYSETS["w2"]
    print(f"[W2] Processing with {len(queries)} queries")
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES", "FORMS", "TABLES"],
        QueriesConfig={"Queries": queries}
    )
    
    # Layer 1: Signal Capture
    candidates = collect_candidates(response, full_text, "W-2")
    print(f"[W2] Collected candidates for {len(candidates)} fields")
    
    # Layer 2: Field Resolver
    resolved_fields = {}
    for field_key, field_candidates in candidates.items():
        resolved = resolve_field(field_candidates, field_key)
        if resolved:
            resolved_fields[field_key] = resolved
    
    print(f"[W2] Resolved {len(resolved_fields)} fields")
    
    # Check acceptance criteria
    if not check_acceptance(resolved_fields, "W-2"):
        print(f"[W2] Acceptance not met, enhancing with LLM")
        resolved_fields = enhance_fields_with_llm(resolved_fields, full_text, "W-2")
        llm_calls = 1
        print(f"[W2] Enhanced to {len(resolved_fields)} fields")
    
    # Layer 3: Validation
    needs_review, validation_errors = validate_document(resolved_fields, "W-2")
    completeness_score = calculate_completeness_score(resolved_fields, "W-2")
    
    # Format for display
    display_fields = format_w2_fields(resolved_fields)
    key_values = [{'key': k, 'value': v} for k, v in display_fields.items()]
    
    print(f"[W2] Final: {len(display_fields)} fields, completeness={completeness_score:.2f}, needs_review={needs_review}")
    
    return {
        'docTypeConfidence': min(0.95, 0.7 + completeness_score * 0.25),
        'summary': f'W-2 processed: {len(display_fields)} fields extracted (completeness: {completeness_score:.1%})',
        'fields': display_fields,
        'keyValues': key_values,
        'flags': {'needs_review': needs_review, 'contains_pii': True},
        'validation_errors': validation_errors,
        'completeness_score': completeness_score
    }, llm_calls

def extract_1099_enhanced(document_bytes, full_text):
    """Extract 1099-NEC using 3-layer architecture"""
    textract = boto3.client('textract')
    llm_calls = 0
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES", "FORMS"],
        QueriesConfig={"Queries": QUERYSETS["1099_nec"]}
    )
    
    # 3-layer processing
    candidates = collect_candidates(response, full_text, "1099-NEC")
    
    resolved_fields = {}
    for field_key, field_candidates in candidates.items():
        resolved = resolve_field(field_candidates, field_key)
        if resolved:
            resolved_fields[field_key] = resolved
    
    # LLM enhancement if needed
    if not check_acceptance(resolved_fields, "1099-NEC"):
        resolved_fields = enhance_fields_with_llm(resolved_fields, full_text, "1099-NEC")
        llm_calls = 1
    
    # Validation
    needs_review, validation_errors = validate_document(resolved_fields, "1099-NEC")
    completeness_score = calculate_completeness_score(resolved_fields, "1099-NEC")
    
    # Format for display
    display_fields = format_1099_fields(resolved_fields)
    key_values = [{'key': k, 'value': v} for k, v in display_fields.items()]
    
    return {
        'docTypeConfidence': min(0.90, 0.7 + completeness_score * 0.20),
        'summary': f'1099-NEC processed: {len(display_fields)} fields extracted (completeness: {completeness_score:.1%})',
        'fields': display_fields,
        'keyValues': key_values,
        'flags': {'needs_review': needs_review, 'contains_pii': True},
        'validation_errors': validation_errors,
        'completeness_score': completeness_score
    }, llm_calls

def extract_invoice_enhanced(document_bytes, full_text):
    """Extract invoice/receipt using AnalyzeExpense + validation"""
    textract = boto3.client('textract')
    llm_calls = 0
    
    try:
        response = textract.analyze_expense(Document={"Bytes": document_bytes})
        
        fields = {}
        line_items = []
        
        for doc in response.get('ExpenseDocuments', []):
            # Extract summary fields
            for field in doc.get('SummaryFields', []):
                field_type = field.get('Type', {}).get('Text', '')
                field_value = field.get('ValueDetection', {}).get('Text', '')
                confidence = field.get('ValueDetection', {}).get('Confidence', 0) / 100
                
                if field_type and field_value:
                    normalized_key = normalize_expense_field_name(field_type)
                    if normalized_key:
                        fields[normalized_key] = {
                            "value": field_value,
                            "confidence": confidence,
                            "source": "E"
                        }
            
            # Extract line items
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
        
        # Validation
        needs_review, validation_errors = validate_document(fields, "INVOICE")
        completeness_score = calculate_completeness_score(fields, "INVOICE")
        
        # Format for display
        display_fields = {k: v["value"] if isinstance(v, dict) else v for k, v in fields.items()}
        key_values = [{'key': k, 'value': str(v)} for k, v in display_fields.items()]
        
        return {
            'docTypeConfidence': min(0.90, 0.75 + completeness_score * 0.15),
            'summary': f'Invoice/Receipt: {len(display_fields)} fields, {len(line_items)} line items (completeness: {completeness_score:.1%})',
            'fields': display_fields,
            'keyValues': key_values,
            'lineItems': line_items,
            'flags': {'needs_review': needs_review, 'contains_pii': False},
            'validation_errors': validation_errors,
            'completeness_score': completeness_score
        }, llm_calls
        
    except Exception as e:
        print(f"AnalyzeExpense failed: {e}")
        return extract_anydoc_enhanced(document_bytes, full_text, 'INVOICE')

def extract_paystub_enhanced(document_bytes, full_text):
    """Extract paystub using 3-layer architecture"""
    textract = boto3.client('textract')
    llm_calls = 0
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES", "TABLES"],
        QueriesConfig={"Queries": QUERYSETS["paystub"]}
    )
    
    # 3-layer processing
    candidates = collect_candidates(response, full_text, "PAYSTUB")
    
    resolved_fields = {}
    for field_key, field_candidates in candidates.items():
        resolved = resolve_field(field_candidates, field_key)
        if resolved:
            resolved_fields[field_key] = resolved
    
    # LLM enhancement if needed
    if not check_acceptance(resolved_fields, "PAYSTUB"):
        resolved_fields = enhance_fields_with_llm(resolved_fields, full_text, "PAYSTUB")
        llm_calls = 1
    
    # Validation
    needs_review, validation_errors = validate_document(resolved_fields, "PAYSTUB")
    completeness_score = calculate_completeness_score(resolved_fields, "PAYSTUB")
    
    # Format for display
    display_fields = {k: v["value"] if isinstance(v, dict) else v for k, v in resolved_fields.items()}
    key_values = [{'key': k, 'value': str(v)} for k, v in display_fields.items()]
    
    return {
        'docTypeConfidence': min(0.85, 0.7 + completeness_score * 0.15),
        'summary': f'Paystub processed: {len(display_fields)} fields extracted (completeness: {completeness_score:.1%})',
        'fields': display_fields,
        'keyValues': key_values,
        'flags': {'needs_review': needs_review, 'contains_pii': True},
        'validation_errors': validation_errors,
        'completeness_score': completeness_score
    }, llm_calls

def extract_utility_enhanced(document_bytes, full_text):
    """Extract utility bill using 3-layer architecture"""
    textract = boto3.client('textract')
    llm_calls = 0
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["QUERIES", "FORMS"],
        QueriesConfig={"Queries": QUERYSETS["utility_bill"]}
    )
    
    # 3-layer processing
    candidates = collect_candidates(response, full_text, "UTILITY_BILL")
    
    resolved_fields = {}
    for field_key, field_candidates in candidates.items():
        resolved = resolve_field(field_candidates, field_key)
        if resolved:
            resolved_fields[field_key] = resolved
    
    # LLM enhancement if needed
    if not check_acceptance(resolved_fields, "UTILITY_BILL"):
        resolved_fields = enhance_fields_with_llm(resolved_fields, full_text, "UTILITY_BILL")
        llm_calls = 1
    
    # Validation
    needs_review, validation_errors = validate_document(resolved_fields, "UTILITY_BILL")
    completeness_score = calculate_completeness_score(resolved_fields, "UTILITY_BILL")
    
    # Format for display
    display_fields = {k: v["value"] if isinstance(v, dict) else v for k, v in resolved_fields.items()}
    key_values = [{'key': k, 'value': str(v)} for k, v in display_fields.items()]
    
    return {
        'docTypeConfidence': min(0.80, 0.7 + completeness_score * 0.10),
        'summary': f'Utility bill processed: {len(display_fields)} fields extracted (completeness: {completeness_score:.1%})',
        'fields': display_fields,
        'keyValues': key_values,
        'flags': {'needs_review': needs_review, 'contains_pii': True},
        'validation_errors': validation_errors,
        'completeness_score': completeness_score
    }, llm_calls

def extract_bank_enhanced(document_bytes, full_text):
    """Extract bank statement using FORMS+TABLES"""
    textract = boto3.client('textract')
    
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["FORMS", "TABLES"]
    )
    
    # Use basic extraction for bank statements (no LLM needed)
    candidates = collect_candidates(response, full_text, "BANK_STATEMENT")
    
    resolved_fields = {}
    for field_key, field_candidates in candidates.items():
        resolved = resolve_field(field_candidates, field_key)
        if resolved:
            resolved_fields[field_key] = resolved
    
    # Extract transactions from tables
    transactions = extract_bank_transactions(response)
    
    # Format for display
    display_fields = {k: v["value"] if isinstance(v, dict) else v for k, v in resolved_fields.items()}
    key_values = [{'key': k, 'value': str(v)} for k, v in display_fields.items()]
    
    return {
        'docTypeConfidence': 0.80,
        'summary': f'Bank statement: {len(display_fields)} fields, {len(transactions)} transactions',
        'fields': display_fields,
        'keyValues': key_values,
        'transactions': transactions[:10],
        'flags': {'needs_review': False, 'contains_pii': True}
    }, 0

def extract_id_enhanced(document_bytes, full_text):
    """Extract ID using AnalyzeID"""
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
            'summary': f'ID document: {len(fields)} fields extracted',
            'fields': fields,
            'keyValues': key_values,
            'flags': {'needs_review': False, 'contains_pii': True}
        }, 0
        
    except Exception as e:
        print(f"AnalyzeID failed: {e}")
        return extract_anydoc_enhanced(document_bytes, full_text, 'ID_CARD')

def extract_anydoc_enhanced(document_bytes, full_text, doc_type):
    """Enhanced fallback extractor"""
    textract = boto3.client('textract')
    llm_calls = 0
    
    try:
        response = textract.analyze_document(
            Document={"Bytes": document_bytes},
            FeatureTypes=["FORMS"]
        )
        
        candidates = collect_candidates(response, full_text, doc_type)
        
        resolved_fields = {}
        for field_key, field_candidates in candidates.items():
            resolved = resolve_field(field_candidates, field_key)
            if resolved:
                resolved_fields[field_key] = resolved
        
        # Always use LLM for unknown documents
        if len(resolved_fields) < 3:
            resolved_fields = enhance_fields_with_llm(resolved_fields, full_text, doc_type)
            llm_calls = 1
        
    except Exception:
        resolved_fields = extract_basic_fields(full_text, doc_type)
    
    # Format for display
    display_fields = {k: v["value"] if isinstance(v, dict) else v for k, v in resolved_fields.items()}
    key_values = [{'key': k, 'value': str(v)} for k, v in display_fields.items() if v]
    
    contains_pii = any(x in full_text.lower() for x in ['ssn', 'social security', 'license', 'address', 'phone'])
    
    return {
        'docTypeConfidence': 0.65,
        'summary': f'{doc_type} processed: {len(display_fields)} fields extracted',
        'fields': display_fields,
        'keyValues': key_values,
        'flags': {'needs_review': True, 'contains_pii': contains_pii}
    }, llm_calls

# Helper functions
def classify_document(text):
    """Enhanced document classifier"""
    text_lower = text.lower()
    
    if any(x in text_lower for x in ['w-2', 'wage and tax statement']):
        return 'W-2'
    elif '1099-nec' in text_lower or 'nonemployee compensation' in text_lower:
        return '1099-NEC'
    elif any(x in text_lower for x in ['invoice', 'bill to', 'invoice number']):
        return 'INVOICE'
    elif any(x in text_lower for x in ['receipt', 'thank you', 'merchant']):
        return 'RECEIPT'
    elif any(x in text_lower for x in ['pay period', 'gross pay', 'net pay']):
        return 'PAYSTUB'
    elif any(x in text_lower for x in ['amount due', 'billing period', 'utility']):
        return 'UTILITY_BILL'
    elif any(x in text_lower for x in ['statement period', 'beginning balance']):
        return 'BANK_STATEMENT'
    elif any(x in text_lower for x in ['driver license', 'passport']):
        return 'ID_CARD'
    
    return 'UNKNOWN'

def format_w2_fields(resolved_fields):
    """Format W-2 fields for UI display"""
    display_fields = {}
    
    field_mapping = {
        "box1_wages": "Box 1 - Wages",
        "box2_fed_tax": "Box 2 - Federal Tax",
        "box3_ss_wages": "Box 3 - SS Wages",
        "box4_ss_tax": "Box 4 - SS Tax",
        "box5_medicare_wages": "Box 5 - Medicare Wages",
        "box6_medicare_tax": "Box 6 - Medicare Tax",
        "box7_ss_tips": "Box 7 - SS Tips",
        "box8_alloc_tips": "Box 8 - Allocated Tips",
        "box10_dependent_care": "Box 10 - Dependent Care",
        "box11_nonqualified": "Box 11 - Nonqualified Plans",
        "employee_ssn": "Employee SSN",
        "employer_ein": "Employer EIN",
        "employee_name": "Employee Name",
        "employer_name": "Employer Name",
        "taxyear": "Tax Year"
    }
    
    for internal_name, field_data in resolved_fields.items():
        display_name = field_mapping.get(internal_name, internal_name.replace('_', ' ').title())
        value = field_data.get("value") if isinstance(field_data, dict) else field_data
        
        if value and str(value).strip():
            display_fields[display_name] = str(value).strip()
    
    return display_fields

def format_1099_fields(resolved_fields):
    """Format 1099-NEC fields for UI display"""
    display_fields = {}
    
    field_mapping = {
        "payer_tin": "Payer TIN",
        "payer_name": "Payer Name",
        "recipient_tin": "Recipient TIN",
        "recipient_name": "Recipient Name",
        "nec_amount_box1": "Box 1 - Nonemployee Compensation",
        "fed_tax_withheld_box4": "Box 4 - Federal Tax Withheld",
        "taxyear": "Tax Year"
    }
    
    for internal_name, field_data in resolved_fields.items():
        display_name = field_mapping.get(internal_name, internal_name.replace('_', ' ').title())
        value = field_data.get("value") if isinstance(field_data, dict) else field_data
        
        if value and str(value).strip():
            display_fields[display_name] = str(value).strip()
    
    return display_fields

def normalize_expense_field_name(field_type):
    """Normalize AnalyzeExpense field names"""
    field_upper = field_type.upper()
    
    if 'VENDOR' in field_upper:
        return 'vendor'
    elif 'TOTAL' in field_upper and 'SUBTOTAL' not in field_upper:
        return 'total'
    elif 'SUBTOTAL' in field_upper:
        return 'subtotal'
    elif 'TAX' in field_upper:
        return 'tax'
    elif 'DATE' in field_upper:
        return 'date'
    elif 'INVOICE' in field_upper and 'NUMBER' in field_upper:
        return 'invoice_number'
    
    return None

def extract_bank_transactions(response):
    """Extract bank transactions from tables"""
    transactions = []
    blocks = {b["Id"]: b for b in response.get("Blocks", [])}
    
    for b in response.get("Blocks", []):
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
            
            # Convert to transactions
            for r in sorted(grid)[1:]:  # Skip header
                row = [grid[r].get(c, "") for c in sorted(grid[r])]
                if len(row) >= 3:
                    transactions.append(row)
    
    return transactions

def gather_text(blocks, blk, child_type):
    """Gather text from child blocks"""
    words = []
    for rel in blk.get("Relationships", []):
        if rel["Type"] == child_type:
            for cid in rel["Ids"]:
                c = blocks[cid]
                if c["BlockType"] in ("WORD", "SELECTION_ELEMENT", "LINE"):
                    if "Text" in c:
                        words.append(c["Text"])
    return " ".join(words).strip()

def extract_full_text(textract_response):
    """Extract full text from Textract response"""
    lines = []
    for block in textract_response.get('Blocks', []):
        if block['BlockType'] == 'LINE':
            lines.append(block.get('Text', ''))
    return '\n'.join(lines)

def extract_basic_fields(text, doc_type):
    """Basic field extraction fallback"""
    fields = {}
    lines = text.split('\n')
    
    for line in lines:
        if ':' in line and len(line) < 200:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value and len(key) < 50:
                    fields[key] = value
    
    return fields

def emit_processing_metrics(doc_type, fields_count, processing_time_ms, llm_calls, completeness_score):
    """Emit processing metrics for monitoring"""
    metrics = {
        "doc_type": doc_type,
        "extracted_fields_count": fields_count,
        "processing_time_ms": processing_time_ms,
        "llm_calls": llm_calls,
        "completeness_score": completeness_score,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    print(f"[METRICS] {json.dumps(metrics)}")
    return metrics