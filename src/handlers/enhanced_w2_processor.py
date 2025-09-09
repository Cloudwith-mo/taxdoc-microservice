import json
import base64
import boto3
import uuid
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

# W-2 QuerySet v2
W2_QUERIES = [
    {"Text":"Tax year","Alias":"taxyear"},
    {"Text":"Employee's social security number","Alias":"employee_ssn"},
    {"Text":"Employee's first name and initial","Alias":"employee_first"},
    {"Text":"Employee's last name","Alias":"employee_last"},
    {"Text":"Employee's address and ZIP code","Alias":"employee_address"},
    {"Text":"Employer identification number","Alias":"employer_ein"},
    {"Text":"Employer's name, address, and ZIP code","Alias":"employer_address"},
    {"Text":"Wages, tips, other compensation (Box 1)","Alias":"box1_wages"},
    {"Text":"Federal income tax withheld (Box 2)","Alias":"box2_fed_tax"},
    {"Text":"Social security wages (Box 3)","Alias":"box3_ss_wages"},
    {"Text":"Social security tax withheld (Box 4)","Alias":"box4_ss_tax"},
    {"Text":"Medicare wages and tips (Box 5)","Alias":"box5_medicare_wages"},
    {"Text":"Medicare tax withheld (Box 6)","Alias":"box6_medicare_tax"},
    {"Text":"Social security tips (Box 7)","Alias":"box7_ss_tips"},
    {"Text":"Allocated tips (Box 8)","Alias":"box8_alloc_tips"},
    {"Text":"Dependent care benefits (Box 10)","Alias":"box10_dependent_care"},
    {"Text":"Nonqualified plans (Box 11)","Alias":"box11_nonqualified"},
    {"Text":"Box 12a Code","Alias":"box12a_code"},
    {"Text":"Box 12a Amount","Alias":"box12a_amount"},
    {"Text":"Box 12b Code","Alias":"box12b_code"},
    {"Text":"Box 12b Amount","Alias":"box12b_amount"},
    {"Text":"Box 12c Code","Alias":"box12c_code"},
    {"Text":"Box 12c Amount","Alias":"box12c_amount"},
    {"Text":"Box 12d Code","Alias":"box12d_code"},
    {"Text":"Box 12d Amount","Alias":"box12d_amount"},
    {"Text":"Statutory employee (Box 13)","Alias":"box13_statutory"},
    {"Text":"Retirement plan (Box 13)","Alias":"box13_retirement"},
    {"Text":"Third-party sick pay (Box 13)","Alias":"box13_sickpay"},
    {"Text":"State (Box 15)","Alias":"box15_state"},
    {"Text":"Employer's state ID number (Box 15)","Alias":"box15_state_id"},
    {"Text":"State wages, tips, etc. (Box 16)","Alias":"box16_state_wages"},
    {"Text":"State income tax (Box 17)","Alias":"box17_state_tax"},
    {"Text":"Local wages, tips, etc. (Box 18)","Alias":"box18_local_wages"},
    {"Text":"Local income tax (Box 19)","Alias":"box19_local_tax"},
    {"Text":"Locality name (Box 20)","Alias":"box20_locality"}
]

# Regex patterns
BOX12_RE = re.compile(r'\b12([a-d])\s*([A-Z]{1,2})\s+(\$?[\d,]+(?:\.\d{2})?)', re.I)
SSN_RE = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
EIN_RE = re.compile(r'\b\d{2}-\d{7}\b')
MONEY_RE = re.compile(r'^\$?\s*([\d,]+(?:\.\d{1,2})?)$')

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
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
        
        # Extract text and classify
        textract = boto3.client('textract')
        text_response = textract.detect_document_text(Document={'Bytes': document_bytes})
        full_text = extract_full_text(text_response)
        
        if not full_text.strip():
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'No text found in document'})}
        
        doc_type = classify_document(full_text)
        doc_id = str(uuid.uuid4())
        
        if doc_type == 'W-2':
            result = extract_w2(document_bytes, full_text)
            result.update({
                'docId': doc_id,
                'docType': doc_type,
                'docTypeConfidence': 0.95,
                'summary': f'W-2 processed with {len(result.get("fields", {}))} fields extracted'
            })
        else:
            # Fallback to simple extraction
            fields = extract_basic_fields(full_text, doc_type)
            key_values = [{'key': k, 'value': str(v)} for k, v in fields.items() if v]
            
            result = {
                'docId': doc_id,
                'docType': doc_type,
                'docTypeConfidence': 0.85,
                'summary': f'Successfully processed {doc_type} document',
                'fields': fields,
                'keyValues': key_values
            }
        
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps(result)}
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

def extract_w2(body_bytes, raw_text):
    textract = boto3.client('textract')
    
    # Analyze with QUERIES, FORMS, TABLES
    response = textract.analyze_document(
        Document={"Bytes": body_bytes},
        FeatureTypes=["QUERIES", "FORMS", "TABLES"],
        QueriesConfig={"Queries": W2_QUERIES}
    )
    
    queries = parse_query_results(response)
    forms = parse_forms_kv(response)
    
    # Store raw text for regex fallbacks
    queries["_raw_text"] = raw_text
    
    # Enrich with regex fallbacks
    enrich_box12(queries, forms, raw_text)
    enrich_box13(queries, forms)
    normalize_money_and_ids(queries)
    
    # Build structured output
    w2_data = {
        "employee": {
            "ssn": get_val(queries, "employee_ssn"),
            "first": get_val(queries, "employee_first"),
            "last": get_val(queries, "employee_last"),
            "address": get_val(queries, "employee_address")
        },
        "employer": {
            "ein": get_val(queries, "employer_ein"),
            "address": get_val(queries, "employer_address")
        },
        "wages": {
            "box1": get_money(queries, "box1_wages"),
            "box2": get_money(queries, "box2_fed_tax"),
            "box3": get_money(queries, "box3_ss_wages"),
            "box4": get_money(queries, "box4_ss_tax"),
            "box5": get_money(queries, "box5_medicare_wages"),
            "box6": get_money(queries, "box6_medicare_tax"),
            "box7": get_money(queries, "box7_ss_tips"),
            "box8": get_money(queries, "box8_alloc_tips"),
            "box10": get_money(queries, "box10_dependent_care"),
            "box11": get_money(queries, "box11_nonqualified")
        },
        "box12": {
            "a": {"code": get_code(queries, "box12a_code"), "amount": get_money(queries, "box12a_amount")},
            "b": {"code": get_code(queries, "box12b_code"), "amount": get_money(queries, "box12b_amount")},
            "c": {"code": get_code(queries, "box12c_code"), "amount": get_money(queries, "box12c_amount")},
            "d": {"code": get_code(queries, "box12d_code"), "amount": get_money(queries, "box12d_amount")}
        },
        "box13": {
            "statutory_employee": get_bool(queries, "box13_statutory"),
            "retirement_plan": get_bool(queries, "box13_retirement"),
            "third_party_sickpay": get_bool(queries, "box13_sickpay")
        },
        "state_local": [{
            "state": get_val(queries, "box15_state"),
            "state_id": get_val(queries, "box15_state_id"),
            "state_wages": get_money(queries, "box16_state_wages"),
            "state_tax": get_money(queries, "box17_state_tax"),
            "local_wages": get_money(queries, "box18_local_wages"),
            "local_tax": get_money(queries, "box19_local_tax"),
            "locality": get_val(queries, "box20_locality")
        }],
        "taxyear": get_val(queries, "taxyear")
    }
    
    # Flatten for frontend display
    fields = flatten_w2_for_display(w2_data)
    key_values = [{'key': k, 'value': str(v)} for k, v in fields.items() if v]
    
    return {
        'fields': fields,
        'keyValues': key_values,
        'w2_structured': w2_data
    }

def parse_query_results(resp):
    out = {}
    alias_map = {}
    
    # Build alias mapping
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "QUERY":
            alias = b.get("Query", {}).get("Alias")
            if alias:
                alias_map[b["Id"]] = alias
    
    # Extract results
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "QUERY_RESULT":
            query_id = None
            for rel in b.get("Relationships", []):
                if rel["Type"] == "ANSWER":
                    for qid in rel["Ids"]:
                        if qid in alias_map:
                            query_id = qid
                            break
            
            if query_id and query_id in alias_map:
                alias = alias_map[query_id]
                confidence = b.get("Confidence", 0)
                if confidence > 1:
                    confidence = confidence / 100
                
                out[alias] = {
                    "value": b.get("Text", "").strip(),
                    "confidence": confidence
                }
    
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

def gather_text(blocks, blk, child_type):
    words = []
    for rel in blk.get("Relationships", []):
        if rel["Type"] == child_type:
            for cid in rel["Ids"]:
                c = blocks[cid]
                if c["BlockType"] in ("WORD", "SELECTION_ELEMENT", "LINE"):
                    if c["BlockType"] == "SELECTION_ELEMENT":
                        if c.get("SelectionStatus") == "SELECTED":
                            words.append("[X]")
                    else:
                        if "Text" in c:
                            words.append(c["Text"])
    return " ".join(words).strip()

def enrich_box12(queries, forms, raw_text):
    for match in BOX12_RE.finditer(raw_text):
        slot, code, amt = match.group(1).lower(), match.group(2), match.group(3)
        code_key = f"box12{slot}_code"
        amt_key = f"box12{slot}_amount"
        
        if code_key not in queries:
            queries[code_key] = {"value": code, "confidence": 0.75}
        if amt_key not in queries:
            queries[amt_key] = {"value": amt, "confidence": 0.75}

def enrich_box13(queries, forms):
    checkboxes = [
        ("statutory employee", "box13_statutory"),
        ("retirement plan", "box13_retirement"),
        ("third-party sick pay", "box13_sickpay"),
    ]
    
    for label, alias in checkboxes:
        if alias not in queries:
            present = any(label in k and "[x]" in v.lower() for k, v in forms.items())
            queries[alias] = {"value": "true" if present else "false", "confidence": 0.7}

def normalize_money_and_ids(queries):
    for k, v in list(queries.items()):
        if not isinstance(v, dict):
            continue
        
        x = (v.get("value") or "").strip()
        
        # Fix SSN/EIN format
        if SSN_RE.fullmatch(x) or EIN_RE.fullmatch(x):
            queries[k]["value"] = x
        
        # Normalize money
        money_match = MONEY_RE.match(x)
        if money_match:
            try:
                d = Decimal(money_match.group(1).replace(',', ''))
                queries[k]["value"] = f"{d:,.2f}"
            except InvalidOperation:
                pass

def flatten_w2_for_display(w2_data):
    fields = {}
    
    # Employee info
    if w2_data["employee"]["ssn"]:
        fields["Employee SSN"] = w2_data["employee"]["ssn"]
    if w2_data["employee"]["first"] or w2_data["employee"]["last"]:
        name_parts = [w2_data["employee"]["first"], w2_data["employee"]["last"]]
        fields["Employee Name"] = " ".join(filter(None, name_parts))
    if w2_data["employee"]["address"]:
        fields["Employee Address"] = w2_data["employee"]["address"]
    
    # Employer info
    if w2_data["employer"]["ein"]:
        fields["Employer EIN"] = w2_data["employer"]["ein"]
    if w2_data["employer"]["address"]:
        fields["Employer Address"] = w2_data["employer"]["address"]
    
    # Wage boxes
    wage_labels = {
        "box1": "Box 1 - Wages, tips, other compensation",
        "box2": "Box 2 - Federal income tax withheld",
        "box3": "Box 3 - Social security wages",
        "box4": "Box 4 - Social security tax withheld",
        "box5": "Box 5 - Medicare wages and tips",
        "box6": "Box 6 - Medicare tax withheld",
        "box7": "Box 7 - Social security tips",
        "box8": "Box 8 - Allocated tips",
        "box10": "Box 10 - Dependent care benefits",
        "box11": "Box 11 - Nonqualified plans"
    }
    
    for box, label in wage_labels.items():
        value = w2_data["wages"][box]
        if value:
            fields[label] = value
    
    # Box 12 codes and amounts
    for slot in ["a", "b", "c", "d"]:
        box12_data = w2_data["box12"][slot]
        if box12_data["code"] or box12_data["amount"]:
            fields[f"Box 12{slot.upper()} Code"] = box12_data["code"] or ""
            fields[f"Box 12{slot.upper()} Amount"] = box12_data["amount"] or ""
    
    # Tax year
    if w2_data["taxyear"]:
        fields["Tax Year"] = w2_data["taxyear"]
    
    return fields

# Helper functions
def get_val(q, k): return (q.get(k) or {}).get("value")
def get_money(q, k): return (q.get(k) or {}).get("value")
def get_code(q, k): return (q.get(k) or {}).get("value")
def get_bool(q, k): return str((q.get(k) or {}).get("value", "")).strip().lower() in ("true", "yes", "x", "checked", "[x]")

def extract_full_text(textract_response):
    lines = []
    for block in textract_response.get('Blocks', []):
        if block['BlockType'] == 'LINE':
            lines.append(block.get('Text', ''))
    return '\n'.join(lines)

def classify_document(text):
    text_lower = text.lower()
    if 'w-2' in text_lower or 'wage and tax statement' in text_lower:
        return 'W-2'
    elif '1099-nec' in text_lower:
        return '1099-NEC'
    elif '1099-misc' in text_lower:
        return '1099-MISC'
    elif 'invoice' in text_lower and ('total' in text_lower or 'amount' in text_lower):
        return 'INVOICE'
    elif 'receipt' in text_lower:
        return 'RECEIPT'
    else:
        return 'UNKNOWN'

def extract_basic_fields(text, doc_type):
    fields = {}
    lines = text.split('\n')
    
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value and len(key) < 50 and len(value) < 200:
                    fields[key] = value
    
    return fields