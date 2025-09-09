import os, json, uuid, re, base64, boto3, decimal
from datetime import datetime

textract = boto3.client("textract")
s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb").Table(os.environ.get("META_TABLE","TaxFlowsAI_Metadata"))
bedrock = boto3.client("bedrock-runtime")

UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET","taxflowsai-uploads")
CORS = {"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"POST,OPTIONS","Access-Control-Allow-Headers":"Content-Type","Content-Type":"application/json"}

# ---------- helpers

def ret(code, body): 
    return {"statusCode":code, "headers":CORS, "body":json.dumps(body, default=lambda o: float(o) if isinstance(o, decimal.Decimal) else o)}

def clean_b64(s):
    s = re.sub(r'^data:.*;base64,','',s, flags=re.I)
    s = re.sub(r'\s+','',s)
    s = s.replace('-','+').replace('_','/')
    rem = len(s)%4
    s += '='*(4-rem) if rem else ''
    return s

def lines_text(detect):
    return "\n".join(b["Text"] for b in detect.get("Blocks",[]) if b["BlockType"]=="LINE")

def call_claude_json(prompt, max_tokens=2000):
    try:
        resp = bedrock.invoke_model(
            modelId=os.environ.get("CLAUDE_ID","anthropic.claude-3-sonnet-20240229-v1:0"),
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version":"bedrock-2023-05-31",
                "max_tokens":max_tokens,
                "temperature":0,
                "messages":[{"role":"user","content":[{"type":"text","text":prompt}]}]
            })
        )
        txt = json.loads(resp["body"].read())["content"][0]["text"]
        # extract JSON only
        start, end = txt.find("{"), txt.rfind("}")
        if start==-1 or end==-1: return {}
        return json.loads(txt[start:end+1])
    except Exception as e:
        print(f"Claude error: {e}")
        return {}

# ---------- classification

LABELS = ["W-2","1099-NEC","1099-MISC","1099-INT","1099-DIV","INVOICE","RECEIPT","DRIVERS_LICENSE","PASSPORT","BANK_STATEMENT","LETTER","CONTRACT","UNKNOWN"]

def classify_doc(text):
    t = text.lower()
    if "wage and tax statement" in t or "form w-2" in t: return "W-2", 0.99
    for f in ["nec","misc","int","div"]:
        if f"form 1099-{f}" in t: return f"1099-{f.upper()}", 0.98
    if "invoice" in t and "total" in t: return "INVOICE", 0.9
    if "receipt" in t or ("merchant" in t and "tax" in t): return "RECEIPT", 0.85
    if "driver" in t and "license" in t: return "DRIVERS_LICENSE", 0.9
    if "passport" in t: return "PASSPORT", 0.9
    
    # Claude fallback
    p = ("Classify this document into one of: " + ", ".join(LABELS) +
         ". Return only JSON like {\"docType\":\"...\",\"confidence\":0..1}. TEXT:\n"+text[:12000])
    out = call_claude_json(p) or {}
    return out.get("docType","UNKNOWN"), float(out.get("confidence",0.6))

# ---------- Textract pieces

def analyze_doc(doc_arg, features, queries=None):
    kwargs = {"Document": doc_arg, "FeatureTypes": features}
    if queries: kwargs["QueriesConfig"] = {"Queries": queries}
    return textract.analyze_document(**kwargs)

def extract_query_answers(analyzed):
    blocks = analyzed.get("Blocks", [])
    alias_by_query = {}
    for b in blocks:
        if b["BlockType"]=="QUERY":
            alias = b.get("Query",{}).get("Alias")
            if alias: alias_by_query[b["Id"]] = alias
    answers = {}
    for b in blocks:
        if b["BlockType"]=="QUERY_RESULT":
            ans = (b.get("Text") or "").strip()
            conf = b.get("Confidence", 0.0)/100 if b.get("Confidence",1)>1 else b.get("Confidence",0.0)
            # map back to query alias
            for r in b.get("Relationships",[]):
                if r["Type"]=="ANSWER":
                    for pid in r["Ids"]:
                        if pid in alias_by_query:
                            answers[alias_by_query[pid]] = {"value": ans, "conf": conf}
    return answers

def forms_kv(analyzed):
    # generic KV extraction
    ids = {b["Id"]: b for b in analyzed.get("Blocks", [])}
    out = []
    for b in analyzed.get("Blocks", []):
        if b["BlockType"]=="KEY_VALUE_SET" and "KEY" in b.get("EntityTypes", []):
            key = get_text(b, ids)
            val = ""
            for r in b.get("Relationships",[]):
                if r["Type"]=="VALUE":
                    for vid in r["Ids"]:
                        val = (val + " " + get_text(ids[vid], ids)).strip()
            if key and val: out.append({"key": key, "value": val, "source":"textract"})
    return out

def get_text(block, ids):
    text = ""
    for r in block.get("Relationships", []):
        if r["Type"]=="CHILD":
            for cid in r["Ids"]:
                b = ids[cid]
                if b["BlockType"] in ("WORD","SELECTION_ELEMENT") and b.get("Text"):
                    text += b["Text"] + " "
    return text.strip()

def extract_tables(analyzed):
    # simple table harvesting → rows of strings
    ids = {b["Id"]: b for b in analyzed.get("Blocks", [])}
    tables = []
    for b in analyzed.get("Blocks", []):
        if b["BlockType"]=="TABLE":
            grid = {}
            for r in b.get("Relationships",[]):
                if r["Type"]=="CHILD":
                    for cid in r["Ids"]:
                        cell = ids[cid]
                        if cell["BlockType"]=="CELL":
                            row, col = cell["RowIndex"], cell["ColumnIndex"]
                            txt = get_text(cell, ids)
                            grid.setdefault(row, {})[col] = txt
            rows = []
            for r in sorted(grid):
                row = [grid[r].get(c,"") for c in sorted(grid[r])]
                rows.append(row)
            tables.append({"name":"Table","rows":rows})
    return tables

# ---------- Claude prompts

def prompt_for(docType):
    if docType=="W-2":
        return """Return ONLY JSON with these keys:
{"employee_ssn":"","employer_ein":"","employer_name":"","employer_address":"","control_number":"",
"employee_first":"","employee_last":"","employee_address":"",
"wages":"","federal_tax":"","ss_wages":"","ss_tax":"","medicare_wages":"","medicare_tax":"",
"box12":[{"code":"","amount":""}],
"state":"","state_id":"","state_wages":"","state_tax":""}
Use exact numbers with decimals. Keep SSN/EIN dashed. Empty string if not found."""
    elif docType=="1099-NEC":
        return """Return ONLY JSON with these keys:
{"payer_name":"","payer_address":"","payer_tin":"","recipient_name":"","recipient_address":"","recipient_tin":"",
"nonemployee_compensation":"","federal_tax_withheld":"","state_tax_withheld":"","state":"","payer_state_no":""}
Use exact numbers with decimals. Keep TIN dashed. Empty string if not found."""
    return """Return ONLY JSON: {"pairs":[{"key":"","value":""}], "_summary":"" }"""

def claude_extract(text, prompt):
    return call_claude_json(prompt + "\n\nTEXT:\n" + text[:20000])

# ---------- validation (W-2 example)

def validate_fields(docType, fields):
    issues=[]
    if docType=="W-2":
        def f(k): 
            try: return float(str(fields.get(k,"")).replace(",","").replace("$",""))
            except: return None
        ss_w, ss_t = f("ss_wages"), f("ss_tax")
        if ss_w and ss_t:
            exp = round(ss_w*0.062,2)
            if abs(ss_t-exp) > 0.03: issues.append(f"SS tax check failed: expected ~{exp}, got {ss_t}")
        med_w, med_t = f("medicare_wages"), f("medicare_tax")
        if med_w and med_t:
            exp = round(med_w*0.0145,2)
            if abs(med_t-exp) > 0.03: issues.append(f"Medicare tax check failed: expected ~{exp}, got {med_t}")
    return issues

# ---------- QUERIES (W-2 sample)

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
    {"Text":"Employer's state ID number (Box 15)","Alias":"state_id"},
    {"Text":"State wages, tips, etc. (Box 16)","Alias":"state_wages"},
    {"Text":"State income tax (Box 17)","Alias":"state_tax"}
]

QUERIES_1099_NEC = [
    {"Text":"Payer's name (Box 1)","Alias":"payer_name"},
    {"Text":"Payer's TIN (Box 2)","Alias":"payer_tin"},
    {"Text":"Recipient's name (Box 3)","Alias":"recipient_name"},
    {"Text":"Recipient's TIN (Box 4)","Alias":"recipient_tin"},
    {"Text":"Nonemployee compensation (Box 1)","Alias":"nonemployee_compensation"},
    {"Text":"Federal income tax withheld (Box 4)","Alias":"federal_tax_withheld"}
]

QUERIES_BY_FORM = {"W-2": QUERIES_W2, "1099-NEC": QUERIES_1099_NEC}

# ---------- merge (prefer query → Claude → fallback)

def merge_fields(docType, tex_q, claude_json, regex_json):
    out, src, conf = {}, {}, {}
    def g(d,k): 
        v = (d or {}).get(k)
        return v["value"] if isinstance(v,dict) else v
    def setv(k, v, s, c):
        if v not in (None, "", []):
            out[k]=v; src[k]=s; conf[k]=c
    
    keys = {
        "W-2": ["employee_ssn","employer_ein","employer_name","employer_address","control_number",
                "employee_first","employee_last","employee_address","wages","federal_tax","ss_wages",
                "ss_tax","medicare_wages","medicare_tax","state","state_id","state_wages","state_tax"],
        "1099-NEC": ["payer_name","payer_tin","recipient_name","recipient_tin","nonemployee_compensation","federal_tax_withheld"]
    }.get(docType, [])
    
    for k in keys:
        tq = tex_q.get(k)
        if tq and tq.get("value"):
            setv(k, tq["value"], "textract", tq.get("conf",0.9))
            continue
        cv = (claude_json or {}).get(k)
        if cv:
            setv(k, cv, "claude", 0.92)
            continue
        rv = (regex_json or {}).get(k)
        if rv:
            setv(k, rv, "regex", 0.7)
    
    if docType=="W-2":
        out["box12"] = (claude_json or {}).get("box12") or (regex_json or {}).get("box12") or []
        src["box12"] = "claude" if "box12" in (claude_json or {}) else "regex"
        conf["box12"]= 0.9 if src["box12"]=="claude" else 0.7
    
    return out, src, conf

def normalize_expense(exp):
    fields = {}
    for doc in exp.get("ExpenseDocuments", []):
        for field in doc.get("SummaryFields", []):
            field_type = field.get("Type", {}).get("Text", "")
            field_value = field.get("ValueDetection", {}).get("Text", "")
            if field_type and field_value:
                fields[field_type.lower().replace(" ", "_")] = field_value
    return fields

def normalize_id(idres):
    fields = {}
    for doc in idres.get("IdentityDocuments", []):
        for field in doc.get("IdentityDocumentFields", []):
            field_type = field.get("Type", {}).get("Text", "")
            field_value = field.get("ValueDetection", {}).get("Text", "")
            if field_type and field_value:
                fields[field_type.lower().replace(" ", "_")] = field_value
    return fields

def merge_generic_kv(textract_kv, claude_pairs):
    # Merge and dedupe key-value pairs
    merged = {}
    for item in textract_kv:
        key = item["key"].lower().strip()
        merged[key] = {"key": item["key"], "value": item["value"], "source": "textract"}
    
    for pair in claude_pairs:
        key = pair.get("key", "").lower().strip()
        if key and key not in merged:
            merged[key] = {"key": pair["key"], "value": pair["value"], "source": "claude"}
    
    return list(merged.values())

def ok_payload(docType, fields, source, confidence, issues, cls_conf=0.9, keyValues=[], tables=[], summary=""):
    return ret(200, {
        "docId": str(uuid.uuid4()),
        "docType": docType, 
        "docTypeConfidence": cls_conf,
        "summary": summary,
        "fields": fields, 
        "keyValues": keyValues, 
        "tables": tables,
        "source": source, 
        "confidence": confidence, 
        "issues": issues
    })

# ---------- main handler

def lambda_handler(event, ctx):
    print(f"Event: {json.dumps(event)}")
    
    # S3 event OR API Gateway (POST JSON with {filename, contentBase64})
    if "Records" in event and event["Records"][0].get("s3"):
        rec = event["Records"][0]["s3"]
        bucket = rec["bucket"]["name"]
        key = rec["object"]["key"]
        doc_arg = {"S3Object":{"Bucket":bucket,"Name":key}}
        
        print(f"Processing S3 object: s3://{bucket}/{key}")
        
        detected = textract.detect_document_text(Document=doc_arg)
        text = lines_text(detected)
        print(f"Extracted text length: {len(text)}")
        
        docType, cls_conf = classify_doc(text)
        print(f"Classified as: {docType} (confidence: {cls_conf})")

        # Route based on document type
        if docType in QUERIES_BY_FORM:
            analyzed = analyze_doc(doc_arg, ["FORMS","TABLES","QUERIES"], QUERIES_BY_FORM[docType])
            tex_q = extract_query_answers(analyzed)
            claude = claude_extract(text, prompt_for(docType))
            rx = {}  # add regex if you like
            fields, source, conf = merge_fields(docType, tex_q, claude, rx)
            issues = validate_fields(docType, fields)
            
            # Store in DynamoDB
            doc_id = str(uuid.uuid4())
            item = {
                "DocumentID": doc_id,
                "docType": docType, 
                "docTypeConfidence": decimal.Decimal(str(cls_conf)),
                "fields": fields, 
                "issues": issues, 
                "s3": {"bucket":bucket,"key":key}, 
                "timestamp": datetime.utcnow().isoformat(),
                "filename": key.split('/')[-1]
            }
            ddb.put_item(Item=item)
            
            # Tag S3 object
            s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet":[{"Key":"DocType","Value":docType}]})
            
            return ok_payload(docType, fields, source, conf, issues, cls_conf)

        elif docType in {"INVOICE","RECEIPT"}:
            exp = textract.analyze_expense(Document=doc_arg)
            fields = normalize_expense(exp)
            
            # Store in DynamoDB
            doc_id = str(uuid.uuid4())
            item = {
                "DocumentID": doc_id,
                "docType":docType,
                "fields":fields,
                "s3":{"bucket":bucket,"key":key},
                "timestamp":datetime.utcnow().isoformat(),
                "filename": key.split('/')[-1]
            }
            ddb.put_item(Item=item)
            s3.put_object_tagging(Bucket=bucket,Key=key,Tagging={"TagSet":[{"Key":"DocType","Value":docType}]})
            
            return ok_payload(docType, fields, {"_all":"textract"}, {"_all":0.95}, [], cls_conf)

        elif docType in {"DRIVERS_LICENSE","PASSPORT","ID"}:
            # AnalyzeID expects DocumentPages array (only S3 today)
            idres = textract.analyze_id(DocumentPages=[{"S3Object":{"Bucket":bucket,"Name":key}}])
            fields = normalize_id(idres)
            
            s3.put_object_tagging(Bucket=bucket,Key=key,Tagging={"TagSet":[{"Key":"DocType","Value":"ID"}]})
            return ok_payload("ID", fields, {"_all":"textract"}, {"_all":0.95}, [], cls_conf)

        else:
            # Generic document processing
            analyzed = analyze_doc(doc_arg, ["FORMS","TABLES"])
            kv = forms_kv(analyzed)
            tables = extract_tables(analyzed)
            claude_kv = call_claude_json(
                'Extract 15 key/value pairs and a one-sentence summary. Return only {"pairs":[...],"_summary":""}.\n\n'+text[:20000]
            )
            keyValues = merge_generic_kv(kv, claude_kv.get("pairs",[]))
            
            payload = {
                "docId": str(uuid.uuid4()), 
                "docType": docType, 
                "docTypeConfidence": decimal.Decimal(str(cls_conf)),
                "summary": claude_kv.get("_summary",""), 
                "keyValues": keyValues, 
                "tables": tables,
                "fields": {}, 
                "issues": []
            }
            
            item = {
                "DocumentID": payload['docId'],
                "docType": payload['docType'],
                "docTypeConfidence": payload['docTypeConfidence'],
                "summary": payload['summary'],
                "keyValues": payload['keyValues'],
                "tables": payload['tables'],
                "fields": payload['fields'],
                "issues": payload['issues'],
                "s3": {"bucket":bucket,"key":key},
                "timestamp": datetime.utcnow().isoformat(),
                "filename": key.split('/')[-1]
            }
            ddb.put_item(Item=item)
            s3.put_object_tagging(Bucket=bucket,Key=key,Tagging={"TagSet":[{"Key":"DocType","Value":docType}]})
            
            return ret(200, payload)

    # API Gateway dev path (JSON bytes)
    method = (event.get("httpMethod") or event.get("requestContext",{}).get("http",{}).get("method"))
    if method=="OPTIONS": 
        return {"statusCode":200,"headers":CORS,"body":""}
    
    if method=="POST":
        body = json.loads(event.get("body") or "{}")
        fname = body.get("filename","upload.bin")
        b64 = clean_b64(body.get("contentBase64",""))
        content = base64.b64decode(b64) if b64 else b""
        
        if not content: 
            return ret(400, {"error":"empty file"})
        
        # Put to S3 then recurse like S3 event
        key = f"uploads/{uuid.uuid4()}_{fname}"
        s3.put_object(Bucket=UPLOAD_BUCKET, Key=key, Body=content)
        
        # Simulate S3 event
        s3_event = {"Records":[{"s3":{"bucket":{"name":UPLOAD_BUCKET},"object":{"key":key}}}]}
        return lambda_handler(s3_event, None)

    return ret(400, {"error":"bad request"})