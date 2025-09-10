import json
import base64
import boto3
import uuid
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from validators.document_validators import get_validator
from schema_extractors import (
    extract_receipt_schema, extract_bank_statement_schema, 
    extract_1099_nec_schema, extract_paystub_schema, classify_document_llm
)

# Enhanced W-2 QuerySet with precise field targeting
QUERIES_W2 = [
    {"Text":"Employee's social security number (Box a)","Alias":"employee_ssn"},
    {"Text":"Employer identification number EIN (Box b)","Alias":"employer_ein"},
    {"Text":"Employer name and address (Box c)","Alias":"employer_name_address"},
    {"Text":"Control number (Box d)","Alias":"control_number"},
    {"Text":"Employee first name and initial (Box e)","Alias":"employee_first"},
    {"Text":"Employee last name (Box e)","Alias":"employee_last"},
    {"Text":"Employee address and ZIP code (Box f)","Alias":"employee_address"},
    {"Text":"Wages, tips, other compensation (Box 1)","Alias":"wages"},
    {"Text":"Federal income tax withheld (Box 2)","Alias":"federal_tax"},
    {"Text":"Social security wages (Box 3)","Alias":"ss_wages"},
    {"Text":"Social security tax withheld (Box 4)","Alias":"ss_tax"},
    {"Text":"Medicare wages and tips (Box 5)","Alias":"medicare_wages"},
    {"Text":"Medicare tax withheld (Box 6)","Alias":"medicare_tax"},
    {"Text":"State (Box 15)","Alias":"state"},
    {"Text":"Employer's state ID number (Box 15)","Alias":"state_id"}
]

FEATURES = ["FORMS","TABLES","QUERIES"]

# Core QuerySets (≤15 queries each) - Production Ready
QUERYSETS = {
    "w2": QUERIES_W2,
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

# Enhanced regex patterns with strict money validation (requires .XX decimal)
MONEY = re.compile(r'^\$?\s*\d{1,3}(?:,\d{3})*\.\d{2}$')
MONEY_RE = re.compile(r'^\$?\s*([\d,]+(?:\.\d{1,2})?)$')
SSN_RE = re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b')
EIN_RE = re.compile(r'\b\d{2}-?\d{7}\b')
DATE_RE = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
PHONE_RE = re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')
EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# Claude prompt for W-2 processing
CLAUDE_W2_PROMPT = """You are an expert tax form parser. Return ONLY JSON:
{
  "employee_ssn":"", "employer_ein":"", "employer_name":"", "employer_address":"", "control_number":"",
  "employee_first":"", "employee_last":"", "employee_address":"",
  "wages":"", "federal_tax":"", "ss_wages":"", "ss_tax":"", "medicare_wages":"", "medicare_tax":"",
  "box12":[{"code":"","amount":""}],
  "state":"", "state_id":"", "state_wages":"", "state_tax":"",
  "local_wages":"", "local_tax":"", "locality_name":""
}
Rules:
- Box 1 is "Wages, tips, other compensation" ONLY. Do NOT use "Local wages".
- Use exact numbers with decimals (e.g., 50000.00). Keep SSN/EIN dashed.
- Employer/Employee addresses may be multi-line—preserve lines in one string separated by newline.
- If not found, use "".
"""

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': 'https://d11rn2gcciu6ti.cloudfront.net',
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
    """High-accuracy ensemble processor with per-field confidence"""
    
    # Step 1: Fast-path for digital PDFs (skip OCR)
    if filename.lower().endswith('.pdf'):
        try:
            pdf_text = extract_pdf_text_with_coordinates(document_bytes)
            if pdf_text and len(pdf_text.strip()) > 50:
                print(f"[TurboParse™] Using PDF fast-path for {filename}")
                return process_with_pdf_text(pdf_text, filename)
        except Exception as e:
            print(f"PDF fast-path failed: {e}, falling back to OCR")
    
    # Step 2: OCR path with preprocessing
    textract = boto3.client('textract')
    text_response = textract.detect_document_text(Document={'Bytes': document_bytes})
    full_text = extract_full_text(text_response)
    
    if len(full_text.strip()) < 10:
        return {'error': 'Document appears empty or unreadable', 'status': 'FAILED_EMPTY'}
    
    # Step 3: Document classification with confidence
    classification = classify_document_with_confidence(full_text)
    doc_type = classification.get('doc_type', 'Other')
    doc_confidence = classification.get('confidence', 0.5)
    
    doc_id = str(uuid.uuid4())
    print(f"[TurboParse™] {doc_type} | {doc_confidence:.2f} | {filename}")
    
    # Step 4: Ensemble extraction with per-field confidence
    if doc_type == 'Pay Stub':
        result = extract_paystub_ensemble(document_bytes, full_text)
    elif doc_type == 'W-2':
        result = extract_w2_ensemble(document_bytes, full_text)
    elif doc_type == 'Receipt':
        result = extract_receipt_ensemble(document_bytes, full_text)
    elif doc_type == 'Bank Statement':
        result = extract_bank_statement_ensemble(document_bytes, full_text)
    else:
        result = extract_with_fallback(document_bytes, full_text, doc_type)
    
    # Step 5: Validation and review determination
    needs_review = determine_needs_review(result, doc_confidence)
    
    # Add high-accuracy metadata
    result.update({
        'docId': doc_id,
        'docType': doc_type,
        'docTypeConfidence': doc_confidence,
        'filename': filename,
        'processedAt': datetime.utcnow().isoformat(),
        'engine': 'TurboParse™ Ensemble',
        'version': '4.0',
        'needs_review': needs_review,
        'extraction_sources': get_extraction_sources(result)
    })
    
    # Publish facts for chatbot
    try:
        from facts_publisher import publish_facts
        user_id = 'guest'  # Default user - should come from auth
        facts_count = publish_facts(user_id, doc_id, result)
        print(f"Published {facts_count} facts for doc {doc_id}")
    except Exception as e:
        print(f"Failed to publish facts: {e}")
    
    return result

def extract_paystub_ensemble(document_bytes, full_text):
    """High-accuracy paystub extraction with ensemble approach"""
    from ensemble_extractor import EnsembleExtractor, process_document
    
    try:
        return process_document(document_bytes, full_text)
    except Exception as e:
        print(f"Ensemble extraction failed: {e}")
        # Fallback to existing extraction
        return extract_paystub_schema(document_bytes, full_text)

def classify_document_with_confidence(text):
    """Enhanced classification with confidence scoring"""
    text_lower = text.lower()
    
    # High confidence patterns
    if 'pay stub' in text_lower or 'payroll' in text_lower:
        if any(x in text_lower for x in ['gross pay', 'net pay', 'deductions']):
            return {'doc_type': 'Pay Stub', 'confidence': 0.95}
    
    if any(x in text_lower for x in ['w-2', 'wage and tax statement']):
        return {'doc_type': 'W-2', 'confidence': 0.95}
    
    # Medium confidence patterns
    if any(x in text_lower for x in ['pay period', 'earnings', 'ytd']):
        return {'doc_type': 'Pay Stub', 'confidence': 0.85}
    
    if any(x in text_lower for x in ['receipt', 'invoice', 'total']):
        return {'doc_type': 'Receipt', 'confidence': 0.80}
    
    return {'doc_type': 'Other', 'confidence': 0.50}

def determine_needs_review(result, doc_confidence):
    """Determine if document needs human review"""
    # Low document classification confidence
    if doc_confidence < 0.8:
        return True
    
    # Check field confidences
    fields = result.get('fields', {})
    for field_data in fields.values():
        if isinstance(field_data, dict) and field_data.get('confidence', 1.0) < 0.6:
            return True
    
    # Math validation failures
    if result.get('validation', {}).get('errors'):
        return True
    
    return False

def get_extraction_sources(result):
    """Get list of extraction sources used"""
    sources = set()
    fields = result.get('fields', {})
    
    for field_data in fields.values():
        if isinstance(field_data, dict) and 'source' in field_data:
            sources.add(field_data['source'])
    
    return list(sources)

def extract_pdf_text_with_coordinates(document_bytes):
    """Extract text from PDF with coordinates (placeholder)"""
    # Placeholder for PDF.js-extract functionality
    # In production, this would use pdf.js-extract or similar
    return None

def process_with_pdf_text(pdf_text, filename):
    """Process document using extracted PDF text"""
    # Placeholder for PDF text processing
    return {'error': 'PDF text processing not implemented'}

def extract_w2_ensemble(document_bytes, full_text):
    """W-2 extraction with ensemble approach"""
    return extract_w2_schema(document_bytes, full_text)

def extract_receipt_ensemble(document_bytes, full_text):
    """Receipt extraction with ensemble approach"""
    return extract_receipt_schema(document_bytes, full_text)

def extract_bank_statement_ensemble(document_bytes, full_text):
    """Bank statement extraction with ensemble approach"""
    return extract_bank_statement_schema(document_bytes, full_text)

def extract_with_fallback(document_bytes, full_text, doc_type):
    """Fallback extraction for unknown document types"""
    return extract_anydoc(document_bytes, full_text, doc_type)

def classify_document_llm(text):
    """LLM-based document classification"""
    # Load classifier prompt
    try:
        with open('/Users/muhammadadeyemi/Documents/microproc/src/prompts/classifier.txt', 'r') as f:
            prompt = f.read()
    except:
        prompt = "Classify document type."
    
    # Simplified classification based on keywords
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

def analyze_w2(doc_arg):
    """Analyze W-2 with Textract QUERIES"""
    textract = boto3.client('textract')
    return textract.analyze_document(
        Document=doc_arg, FeatureTypes=FEATURES,
        QueriesConfig={"Queries": QUERIES_W2}
    )

def extract_query_answers(analyzed):
    """Extract query answers with alias mapping"""
    blocks = analyzed.get("Blocks", [])
    alias_by_query_id = {}
    for b in blocks:
        if b["BlockType"] == "QUERY":
            alias = b.get("Query",{}).get("Alias")
            if alias: alias_by_query_id[b["Id"]] = alias

    out = {}
    for b in blocks:
        if b["BlockType"] == "QUERY_RESULT":
            ans = (b.get("Text") or "").strip()
            conf = b.get("Confidence", 0.0)/100 if b.get("Confidence",1)>1 else b.get("Confidence",0.0)
            # link back to parent QUERY
            for r in b.get("Relationships",[]):
                if r["Type"] == "ANSWER":
                    for pid in r["Ids"]:
                        alias = alias_by_query_id.get(pid)
                        if alias:
                            out[alias] = {"value": ans, "conf": conf}
    return out

def call_claude_json(prompt):
    """Call Claude for JSON extraction (placeholder - implement with actual Claude API)"""
    # Placeholder - in production, integrate with Claude API
    # For now, return empty dict to avoid errors
    return {}

def as_money_or_none(v):
    """Validate money format"""
    s = str(v).strip()
    return s if MONEY.match(s) else None

def merge_w2(tex_q, claude, rx):
    """Merge W-2 data with precedence: Textract Query > Claude > Regex"""
    out, src, conf = {}, {}, {}
    
    def choose(key, money=False):
        # Prefer Textract Query (conf >= 0.88)
        tq = tex_q.get(key)
        if tq and tq.get("value"):
            val = tq["value"].strip()
            if money: val = as_money_or_none(val)
            if val and tq.get("conf", 0) >= 0.88:
                out[key]=val; src[key]="textract"; conf[key]=max(0.88, tq.get("conf",0.9)); return
        
        # Claude fallback
        cv = (claude or {}).get(key, "").strip()
        if cv:
            if money: cv = as_money_or_none(cv)
            if cv:
                out[key]=cv; src[key]="claude"; conf[key]=0.92; return
        
        # Regex fallback
        rv = (rx or {}).get(key, "").strip()
        if rv:
            if money: rv = as_money_or_none(rv)
            if rv:
                out[key]=rv; src[key]="regex"; conf[key]=0.70

    money_keys = {"wages","federal_tax","ss_wages","ss_tax","medicare_wages","medicare_tax","state_wages","state_tax","local_wages","local_tax"}
    keys = ["employee_ssn","employer_ein","employer_name","employer_address","control_number",
            "employee_first","employee_last","employee_address"] + list(money_keys) + ["state","state_id","locality_name"]

    for k in keys: choose(k, money=(k in money_keys))

    out["box12"] = (claude or {}).get("box12") or (rx or {}).get("box12") or []
    src["box12"] = "claude" if "box12" in (claude or {}) else ("regex" if "box12" in (rx or {}) else "")
    conf["box12"]= 0.9 if src["box12"]=="claude" else (0.7 if src["box12"]=="regex" else 0)

    return out, src, conf

def rx_w2(text):
    """Strengthened regex fallback to avoid 'local wages' confusion"""
    rx={}
    money = lambda pat: (m.group(1) if (m:=re.search(pat+r'.{0,35}?\$?\s*([0-9,]+\.\d{2}|\d{1,3}(?:,\d{3})*)', text, re.I)) else "")
    
    # Explicit labels, negative lookbehind to avoid "local wages"
    rx["wages"]          = money(r'(?:box\s*1\b|wages,\s*tips,\s*other\s*compensation)(?<!local\s+wages)')
    rx["federal_tax"]    = money(r'(?:box\s*2\b|federal\s+income\s+tax\s+withheld)')
    rx["ss_wages"]       = money(r'(?:box\s*3\b|social\s+security\s+wages)')
    rx["ss_tax"]         = money(r'(?:box\s*4\b|social\s+security\s+tax\s+withheld)')
    rx["medicare_wages"] = money(r'(?:box\s*5\b|medicare\s+wages)')
    rx["medicare_tax"]   = money(r'(?:box\s*6\b|medicare\s+tax\s+withheld)')
    rx["state"]          = (m.group(1) if (m:=re.search(r'\bbox\s*15\b.*?\b([A-Z]{2})\b', text, re.I|re.S)) else "")
    rx["state_id"]       = (m.group(1) if (m:=re.search(r'\bbox\s*15\b.*?([0-9]{3,})', text, re.I|re.S)) else "")
    rx["state_wages"]    = money(r'(?:box\s*16\b|state\s+wages)')
    rx["state_tax"]      = money(r'(?:box\s*17\b|state\s+income\s+tax)')
    rx["local_wages"]    = money(r'(?:box\s*18\b|local\s+wages)')
    rx["local_tax"]      = money(r'(?:box\s*19\b|local\s+income\s+tax)')
    rx["locality_name"]  = (m.group(1).strip() if (m:=re.search(r'\bbox\s*20\b.*?([A-Z]{2,}|[A-Za-z][A-Za-z\s\-]{1,20})', text, re.I|re.S)) else "")
    
    # Box 12 list
    rows = re.findall(r'\bbox\s*12\w?\b.*?(?:code[:\s]+)?([A-Z]{1,2})\D{0,20}(\$?\s*[0-9,]+(?:\.\d{2})?)',
                      text, re.I|re.S)
    rx["box12"] = [{"code": c.upper(), "amount": re.sub(r'[^\d.]','', a)} for c,a in rows]
    return rx

def validate_w2_audit(fields):
    """Audit W-2 for tax calculation errors"""
    flags = []
    
    try:
        # Check SS tax = 6.2% of SS wages
        ss_wages = float(str(fields.get('ss_wages', '0')).replace('$', '').replace(',', '') or '0')
        ss_tax = float(str(fields.get('ss_tax', '0')).replace('$', '').replace(',', '') or '0')
        
        if ss_wages > 0 and ss_tax > 0:
            expected_ss_tax = ss_wages * 0.062
            if abs(ss_tax - expected_ss_tax) > 1.0:  # Allow $1 rounding
                flags.append(f"SS Tax mismatch: {ss_tax} ≠ 6.2% of {ss_wages} ({expected_ss_tax:.2f})")
        
        # Check Medicare tax = 1.45% of Medicare wages
        medicare_wages = float(str(fields.get('medicare_wages', '0')).replace('$', '').replace(',', '') or '0')
        medicare_tax = float(str(fields.get('medicare_tax', '0')).replace('$', '').replace(',', '') or '0')
        
        if medicare_wages > 0 and medicare_tax > 0:
            expected_medicare_tax = medicare_wages * 0.0145
            if abs(medicare_tax - expected_medicare_tax) > 1.0:  # Allow $1 rounding
                flags.append(f"Medicare Tax mismatch: {medicare_tax} ≠ 1.45% of {medicare_wages} ({expected_medicare_tax:.2f})")
    
    except (ValueError, TypeError):
        pass
    
    return flags

def extract_w2_schema(document_bytes, full_text):
    """Enhanced W-2 extraction with Textract QUERIES + Claude + validation"""
    print(f"[W2] Processing with TurboParse™ engine")
    
    # Step 1: Textract QUERIES
    analyzed = analyze_w2({"Bytes": document_bytes})
    tex_q = extract_query_answers(analyzed)
    print(f"[W2] Textract queries extracted: {len(tex_q)} fields")
    
    # Step 2: Claude fallback (full text, no 2k limit)
    claude_json = call_claude_json(CLAUDE_W2_PROMPT + "\n\nTEXT:\n" + full_text[:20000])
    print(f"[W2] Claude extracted: {len(claude_json)} fields")
    
    # Step 3: Regex fallback
    rx = rx_w2(full_text)
    print(f"[W2] Regex extracted: {len(rx)} fields")
    
    # Step 4: Merge with precedence
    merged, sources, confidences = merge_w2(tex_q, claude_json, rx)
    print(f"[W2] Merged: {len(merged)} fields")
    
    # Step 5: Validate like an auditor
    audit_flags = validate_w2_audit(merged)
    needs_review = len(audit_flags) > 0
    
    # Step 6: Format for UI display
    fields = {}
    key_values = []
    
    # Employer section
    if merged.get('employer_ein'): fields['Employer EIN'] = merged['employer_ein']
    if merged.get('employer_name'): fields['Employer Name'] = merged['employer_name']
    if merged.get('employer_address'): fields['Employer Address'] = merged['employer_address']
    if merged.get('control_number'): fields['Control Number'] = merged['control_number']
    
    # Employee section
    if merged.get('employee_ssn'): fields['Employee SSN'] = merged['employee_ssn']
    if merged.get('employee_first') or merged.get('employee_last'):
        name = f"{merged.get('employee_first', '')} {merged.get('employee_last', '')}".strip()
        if name: fields['Employee Name'] = name
    if merged.get('employee_address'): fields['Employee Address'] = merged['employee_address']
    
    # Federal section (Boxes 1-6)
    money_fields = {
        'wages': 'Box 1 - Wages, tips, other compensation',
        'federal_tax': 'Box 2 - Federal income tax withheld',
        'ss_wages': 'Box 3 - Social security wages',
        'ss_tax': 'Box 4 - Social security tax withheld',
        'medicare_wages': 'Box 5 - Medicare wages and tips',
        'medicare_tax': 'Box 6 - Medicare tax withheld'
    }
    
    for key, label in money_fields.items():
        if merged.get(key):
            # Format to 2 decimals
            try:
                val = float(str(merged[key]).replace('$', '').replace(',', ''))
                formatted = f"${val:,.2f}"
                fields[label] = formatted
                
                # Add source badge and confidence
                source = sources.get(key, 'unknown')
                conf = confidences.get(key, 0) * 100
                key_values.append({
                    'key': label,
                    'value': f"{formatted} ({source} {conf:.0f}%)"
                })
            except (ValueError, TypeError):
                fields[label] = merged[key]
                key_values.append({'key': label, 'value': merged[key]})
    
    # Box 12 table
    if merged.get('box12'):
        box12_items = merged['box12']
        if isinstance(box12_items, list) and box12_items:
            fields['Box 12 Items'] = f"{len(box12_items)} codes"
            for i, item in enumerate(box12_items[:4]):  # Show first 4
                if isinstance(item, dict) and item.get('code') and item.get('amount'):
                    fields[f"Box 12{chr(97+i)} - {item['code']}"] = item['amount']
    
    # State section (Boxes 15-17)
    if merged.get('state'): fields['State (Box 15)'] = merged['state']
    if merged.get('state_id'): fields['State ID (Box 15)'] = merged['state_id']
    if merged.get('state_wages'):
        try:
            val = float(str(merged['state_wages']).replace('$', '').replace(',', ''))
            fields['State wages (Box 16)'] = f"${val:,.2f}"
        except (ValueError, TypeError):
            fields['State wages (Box 16)'] = merged['state_wages']
    if merged.get('state_tax'):
        try:
            val = float(str(merged['state_tax']).replace('$', '').replace(',', ''))
            fields['State income tax (Box 17)'] = f"${val:,.2f}"
        except (ValueError, TypeError):
            fields['State income tax (Box 17)'] = merged['state_tax']
    
    # Local section (Boxes 18-20)
    if merged.get('local_wages'):
        try:
            val = float(str(merged['local_wages']).replace('$', '').replace(',', ''))
            fields['Local wages (Box 18)'] = f"${val:,.2f}"
        except (ValueError, TypeError):
            fields['Local wages (Box 18)'] = merged['local_wages']
    if merged.get('local_tax'):
        try:
            val = float(str(merged['local_tax']).replace('$', '').replace(',', ''))
            fields['Local income tax (Box 19)'] = f"${val:,.2f}"
        except (ValueError, TypeError):
            fields['Local income tax (Box 19)'] = merged['local_tax']
    if merged.get('locality_name'): fields['Locality name (Box 20)'] = merged['locality_name']
    
    # Add remaining fields to key_values if not already added
    for k, v in fields.items():
        if not any(kv['key'] == k for kv in key_values):
            key_values.append({'key': k, 'value': str(v)})
    
    print(f"[W2] Final output: {len(fields)} fields, audit_flags={len(audit_flags)}")
    
    return {
        'docTypeConfidence': 0.95,
        'summary': f'W-2 processed with {len(fields)} fields extracted' + (f', {len(audit_flags)} audit flags' if audit_flags else ''),
        'fields': fields,
        'keyValues': key_values,
        'auditFlags': audit_flags,
        'flags': {'needs_review': needs_review, 'contains_pii': True}
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
    """Enhanced paystub extraction with column-aware parsing and validation"""
    print(f"[PAYSTUB] Processing with enhanced extraction")
    
    # Load prompt template
    try:
        with open('/Users/muhammadadeyemi/Documents/microproc/src/config/paystub_extractor_prompt.txt', 'r') as f:
            prompt_template = f.read()
    except:
        prompt_template = "Extract paystub data as JSON with validation."
    
    # Step 1: Get tables for column-aware parsing
    textract = boto3.client('textract')
    response = textract.analyze_document(
        Document={"Bytes": document_bytes},
        FeatureTypes=["FORMS", "TABLES"]
    )
    
    # Step 2: Column-aware table parsing
    tables = extract_tables_with_headers(response)
    parsed_data = parse_paystub_tables(tables, full_text)
    
    # Step 3: LLM extraction with strict prompt
    llm_data = call_paystub_llm(prompt_template, full_text)
    
    # Step 4: Merge and validate
    merged = merge_paystub_data(parsed_data, llm_data)
    validated = validate_paystub(merged)
    
    # Step 5: Format for UI
    fields, key_values = format_paystub_output(validated)
    
    needs_review = len(validated.get('validation', {}).get('errors', [])) > 0
    confidence = calculate_paystub_confidence(validated)
    
    print(f"[PAYSTUB] Extracted {len(fields)} fields, confidence={confidence:.2f}")
    
    return {
        'docTypeConfidence': confidence,
        'summary': f'Paystub processed with {len(fields)} fields extracted',
        'fields': fields,
        'keyValues': key_values,
        'validation': validated.get('validation', {}),
        'flags': {'needs_review': needs_review, 'contains_pii': True}
    }

def extract_tables_with_headers(response):
    """Extract tables with header awareness"""
    tables = []
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
            
            # Convert to structured table with headers
            if grid:
                headers = [grid[1].get(c, "") for c in sorted(grid.get(1, {}))] if 1 in grid else []
                rows = []
                for r in sorted(grid)[1:]:  # Skip header row
                    row = [grid[r].get(c, "") for c in sorted(grid[r])]
                    rows.append(row)
                
                tables.append({"headers": headers, "rows": rows})
    
    return tables

def parse_paystub_tables(tables, full_text):
    """Parse paystub tables with column awareness"""
    data = {
        'income_items': [],
        'deduction_items': [],
        'gross_current': None,
        'gross_ytd': None,
        'net_current': None,
        'net_ytd': None,
        'deduction_total_current': None,
        'deduction_total_ytd': None
    }
    
    for table in tables:
        headers = [h.lower() for h in table.get('headers', [])]
        rows = table.get('rows', [])
        
        # Find column indices
        current_col = next((i for i, h in enumerate(headers) if 'current' in h and 'amount' in h), -1)
        ytd_col = next((i for i, h in enumerate(headers) if 'ytd' in h or 'year' in h), -1)
        type_col = 0  # Usually first column
        
        for row in rows:
            if len(row) <= type_col:
                continue
                
            item_type = row[type_col].strip()
            current_val = normalize_money(row[current_col] if current_col >= 0 and current_col < len(row) else "")
            ytd_val = normalize_money(row[ytd_col] if ytd_col >= 0 and ytd_col < len(row) else "")
            
            # Categorize items
            if any(x in item_type.lower() for x in ['regular', 'overtime', 'bonus', 'salary']):
                data['income_items'].append({"type": item_type, "current": current_val, "ytd": ytd_val})
            elif any(x in item_type.lower() for x in ['federal', 'state', 'medicare', 'ei', 'cpp', 'tax', '401k']):
                data['deduction_items'].append({"type": item_type, "current": current_val, "ytd": ytd_val})
            elif 'gross' in item_type.lower():
                data['gross_current'] = current_val
                data['gross_ytd'] = ytd_val
            elif 'net' in item_type.lower():
                data['net_current'] = current_val
                data['net_ytd'] = ytd_val
    
    # Calculate deduction totals
    if data['deduction_items']:
        data['deduction_total_current'] = sum_money([d['current'] for d in data['deduction_items']])
        data['deduction_total_ytd'] = sum_money([d['ytd'] for d in data['deduction_items']])
    
    return data

def call_paystub_llm(prompt, text):
    """Call LLM for paystub extraction (placeholder)"""
    # Placeholder - in production, integrate with Claude/GPT
    return {
        'employee_name': extract_with_anchor(text, ['employee:', 'name:']),
        'employer_name': extract_employer_name(text),
        'employer_address': extract_employer_address(text),
        'cycle_start': extract_date(text, 'cycle start'),
        'cycle_end': extract_date(text, 'cycle end'),
        'pay_date': extract_date(text, 'pay date'),
        'pay_rate': extract_with_anchor(text, ['rate:', 'hourly:']),
        'current_hours': extract_with_anchor(text, ['hours:', 'current hours:'])
    }

def merge_paystub_data(parsed, llm):
    """Merge parsed table data with LLM extraction"""
    merged = parsed.copy()
    
    # Add LLM fields
    for key, value in llm.items():
        if value and not merged.get(key):
            merged[key] = value
    
    return merged

def validate_paystub(data):
    """Validate paystub with math checks using validator class"""
    validator = get_validator('PAYSTUB')
    return validator.validate(data)

def format_paystub_output(data):
    """Format paystub data for UI display"""
    fields = {}
    key_values = []
    
    # Basic info
    if data.get('employee_name'): fields['Employee Name'] = data['employee_name']
    if data.get('employer_name'): fields['Employer Name'] = data['employer_name']
    if data.get('employer_address'): fields['Employer Address'] = data['employer_address']
    
    # Pay period
    if data.get('cycle_start'): fields['Pay Period Start'] = data['cycle_start']
    if data.get('cycle_end'): fields['Pay Period End'] = data['cycle_end']
    if data.get('pay_date'): fields['Pay Date'] = data['pay_date']
    
    # Pay info
    if data.get('pay_rate'): fields['Pay Rate'] = f"${data['pay_rate']}"
    if data.get('current_hours'): fields['Current Hours'] = data['current_hours']
    
    # Totals
    if data.get('gross_current'): fields['Gross Pay (Current)'] = f"${data['gross_current']}"
    if data.get('gross_ytd'): fields['Gross Pay (YTD)'] = f"${data['gross_ytd']}"
    if data.get('net_current'): fields['Net Pay (Current)'] = f"${data['net_current']}"
    if data.get('net_ytd'): fields['Net Pay (YTD)'] = f"${data['net_ytd']}"
    if data.get('deduction_total_current'): fields['Total Deductions (Current)'] = f"${data['deduction_total_current']}"
    
    # Create key_values with validation info
    for k, v in fields.items():
        confidence = 90  # Default confidence
        if any(err in str(v) for err in data.get('validation', {}).get('errors', [])):
            confidence = 50
        key_values.append({'key': k, 'value': f"{v} ({confidence}%)"})
    
    return fields, key_values

def calculate_paystub_confidence(data):
    """Calculate overall confidence score"""
    base_score = 0.85
    errors = len(data.get('validation', {}).get('errors', []))
    warnings = len(data.get('validation', {}).get('warnings', []))
    
    # Reduce confidence for validation issues
    penalty = (errors * 0.15) + (warnings * 0.05)
    return max(0.3, base_score - penalty)

# Helper functions
def normalize_money(value):
    """Normalize money to ####.## format"""
    if not value:
        return None
    
    # Remove $ and commas, keep only digits and decimal
    cleaned = re.sub(r'[^\d.]', '', str(value))
    try:
        return f"{float(cleaned):.2f}"
    except (ValueError, TypeError):
        return None

def sum_money(amounts):
    """Sum money amounts safely"""
    total = 0
    for amount in amounts:
        if amount:
            try:
                total += float(amount)
            except (ValueError, TypeError):
                continue
    return f"{total:.2f}"

def validate_date_format(date_str):
    """Validate YYYY-MM-DD format"""
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False

def extract_with_anchor(text, anchors):
    """Extract value after anchor text"""
    for anchor in anchors:
        pattern = rf'{re.escape(anchor)}\s*([^\n\r]+)'
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip()
    return None

def extract_employer_name(text):
    """Extract employer name (first line of employer info)"""
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if any(x in line.lower() for x in ['company', 'corp', 'inc', 'ltd']):
            return line.strip()
    return None

def extract_employer_address(text):
    """Extract employer address (lines after employer name)"""
    lines = text.split('\n')
    address_lines = []
    found_employer = False
    
    for line in lines:
        if any(x in line.lower() for x in ['company', 'corp', 'inc', 'ltd']):
            found_employer = True
            continue
        elif found_employer and any(c.isdigit() for c in line):
            address_lines.append(line.strip())
            if len(address_lines) >= 2:  # Usually 2 lines max
                break
    
    return '\n'.join(address_lines) if address_lines else None

def extract_date(text, context):
    """Extract date in context and convert to YYYY-MM-DD"""
    # Look for dates near context
    pattern = rf'{re.escape(context)}[^\d]*([\d/\-]+)'
    match = re.search(pattern, text, re.I)
    if match:
        date_str = match.group(1)
        # Convert to YYYY-MM-DD
        try:
            from datetime import datetime
            # Try common formats
            for fmt in ['%m/%d/%Y', '%m-%d-%Y', '%Y-%m-%d', '%m/%d/%y']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        except:
            pass
    return None

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