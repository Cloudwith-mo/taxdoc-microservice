import os, json, uuid, re, base64, boto3, decimal
from datetime import datetime

textract = boto3.client("textract")
s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb").Table(os.environ.get("META_TABLE","TaxFlowsAI_Metadata"))
bedrock = boto3.client("bedrock-runtime")

UPLOAD_BUCKET = os.environ.get("UPLOAD_BUCKET","taxflowsai-uploads")
CORS = {"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"POST,OPTIONS","Access-Control-Allow-Headers":"Content-Type","Content-Type":"application/json"}

def ret(code, body): 
    return {"statusCode":code, "headers":CORS, "body":json.dumps(body, default=lambda o: float(o) if isinstance(o, decimal.Decimal) else o)}

def clean_b64(s):
    s = re.sub(r'^data:.*;base64,','',s, flags=re.I)
    s = re.sub(r'\s+','',s)
    s = s.replace('-','+').replace('_','/')
    rem = len(s)%4
    s += '='*(4-rem) if rem else ''
    return s

def detect_text_bytes(bucket, key):
    """Read from S3 and call Textract with Bytes to avoid KMS/S3 access issues"""
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    response = textract.detect_document_text(Document={"Bytes": body})
    lines = [b["Text"] for b in response.get("Blocks", []) if b["BlockType"] == "LINE"]
    text = "\n".join(lines)
    print(f"OCR bytes={len(body)}, lines={len(lines)} for s3://{bucket}/{key}")
    return text, body

def analyze_doc_bytes(body, features, queries=None):
    """Analyze document using Bytes instead of S3Object"""
    kwargs = {"Document": {"Bytes": body}, "FeatureTypes": features}
    if queries: kwargs["QueriesConfig"] = {"Queries": queries}
    return textract.analyze_document(**kwargs)

def call_claude_json(prompt, max_tokens=2000):
    import time
    import random
    
    for attempt in range(4):
        try:
            resp = bedrock.invoke_model(
                modelId=os.environ.get("CLAUDE_ID","anthropic.claude-3-5-sonnet-20240620-v1:0"),
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
            start, end = txt.find("{"), txt.rfind("}")
            if start==-1 or end==-1: return {}
            try: return json.loads(txt[start:end+1])
            except: return {}
        except Exception as e:
            if "ThrottlingException" in str(e) and attempt < 3:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            return {}
    return {}

# Classification
def classify_doc(text):
    # Heuristic classification
    t = text.lower()
    if "wage and tax statement" in t or "form w-2" in t: return "W-2", 0.99
    if "form 1099-nec" in t: return "1099-NEC", 0.98
    if "form 1099-misc" in t: return "1099-MISC", 0.98
    if "invoice" in t and "total" in t: return "INVOICE", 0.9
    if "receipt" in t: return "RECEIPT", 0.85
    if "driver" in t and "license" in t: return "DRIVERS_LICENSE", 0.9
    if "passport" in t: return "PASSPORT", 0.9
    
    # Comprehend classifier (if available)
    comprehend_result = classify_with_comprehend(text)
    if comprehend_result and comprehend_result[1] > 0.8:
        return comprehend_result
    
    # Claude fallback
    p = f"Classify this document into one of: W-2, 1099-NEC, 1099-MISC, INVOICE, RECEIPT, DRIVERS_LICENSE, PASSPORT, CONTRACT, LETTER, BANK_STATEMENT, UNKNOWN. Return only JSON like {{\"docType\":\"...\",\"confidence\":0.95}}. TEXT:\n{text[:12000]}"
    out = call_claude_json(p) or {}
    return out.get("docType","UNKNOWN"), float(out.get("confidence",0.6))

def classify_with_comprehend(text):
    """Use Comprehend custom classifier if available"""
    endpoint_arn = os.environ.get("COMPREHEND_ENDPOINT")
    if not endpoint_arn:
        return None
    
    try:
        comprehend = boto3.client("comprehend")
        response = comprehend.classify_document(
            Text=text[:5000],  # Comprehend limit
            EndpointArn=endpoint_arn
        )
        
        classes = response.get("Classes", [])
        if classes:
            top_class = max(classes, key=lambda x: x["Score"])
            return top_class["Name"], top_class["Score"]
    except Exception as e:
        print(f"Comprehend classification failed: {e}")
    
    return None

# Textract helpers
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
            for r in b.get("Relationships",[]):
                if r["Type"]=="ANSWER":
                    for pid in r["Ids"]:
                        if pid in alias_by_query:
                            answers[alias_by_query[pid]] = {"value": ans, "conf": conf}
    return answers

def forms_kv(analyzed):
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

# W-2 Queries
QUERIES_W2 = [
    {"Text":"Employee's social security number","Alias":"employee_ssn"},
    {"Text":"Employer identification number EIN","Alias":"employer_ein"},
    {"Text":"Employer name","Alias":"employer_name"},
    {"Text":"Wages, tips, other compensation","Alias":"wages"},
    {"Text":"Federal income tax withheld","Alias":"federal_tax"},
    {"Text":"Social security wages","Alias":"ss_wages"},
    {"Text":"Social security tax withheld","Alias":"ss_tax"},
    {"Text":"Medicare wages and tips","Alias":"medicare_wages"},
    {"Text":"Medicare tax withheld","Alias":"medicare_tax"}
]

def prompt_for_w2():
    return """Return ONLY JSON with these W-2 fields:
{"employee_ssn":"","employer_ein":"","employer_name":"","wages":"","federal_tax":"","ss_wages":"","ss_tax":"","medicare_wages":"","medicare_tax":""}
Use exact numbers with decimals. Keep SSN/EIN dashed. Empty string if not found."""

def merge_w2_fields(tex_q, claude_json):
    out, src, conf = {}, {}, {}
    fields = ["employee_ssn","employer_ein","employer_name","wages","federal_tax","ss_wages","ss_tax","medicare_wages","medicare_tax"]
    
    for k in fields:
        tq = tex_q.get(k)
        if tq and tq.get("value"):
            out[k] = tq["value"]
            src[k] = "textract"
            conf[k] = tq.get("conf", 0.9)
        elif claude_json and claude_json.get(k):
            out[k] = claude_json[k]
            src[k] = "claude"
            conf[k] = 0.92
        else:
            out[k] = ""
            src[k] = "none"
            conf[k] = 0.0
    
    return out, src, conf

def validate_w2_fields(fields):
    issues = []
    try:
        ss_w = float(str(fields.get("ss_wages","")).replace(",","").replace("$",""))
        ss_t = float(str(fields.get("ss_tax","")).replace(",","").replace("$",""))
        if ss_w and ss_t:
            exp = round(ss_w * 0.062, 2)
            if abs(ss_t - exp) > 0.03:
                issues.append(f"SS tax check failed: expected ~{exp}, got {ss_t}")
    except:
        pass
    return issues

def normalize_expense(exp):
    fields = {}
    for doc in exp.get("ExpenseDocuments", []):
        for field in doc.get("SummaryFields", []):
            key = field.get("Type", {}).get("Text", "")
            value = field.get("ValueDetection", {}).get("Text", "")
            if key and value:
                fields[key.lower().replace(" ", "_")] = value
    return fields

def normalize_id(idres):
    fields = {}
    for doc in idres.get("IdentityDocuments", []):
        for field in doc.get("IdentityDocumentFields", []):
            key = field.get("Type", {}).get("Text", "")
            value = field.get("ValueDetection", {}).get("Text", "")
            if key and value:
                fields[key.lower().replace(" ", "_")] = value
    return fields

def merge_generic_kv(textract_kv, claude_pairs):
    seen = set()
    merged = []
    
    for item in textract_kv:
        key_lower = item["key"].lower()
        if key_lower not in seen:
            merged.append(item)
            seen.add(key_lower)
    
    for pair in claude_pairs:
        key_lower = pair.get("key", "").lower()
        if key_lower not in seen and pair.get("value"):
            merged.append({"key": pair["key"], "value": pair["value"], "source": "claude"})
            seen.add(key_lower)
    
    return merged

def get_user_id(event):
    """Extract user ID from event context or headers"""
    # Try to get from API Gateway context
    if event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub"):
        return event["requestContext"]["authorizer"]["claims"]["sub"]
    
    # Try to get from headers
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization") or headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # For now, use a simple user ID extraction
        return "user_" + str(hash(auth_header))[-8:]
    
    # Default fallback
    return "anonymous_user"

def lambda_handler(event, ctx):
    user_id = get_user_id(event)
    
    # S3 event
    if "Records" in event and event["Records"][0].get("s3"):
        rec = event["Records"][0]["s3"]
        bucket = rec["bucket"]["name"]
        key = rec["object"]["key"]
        
        try:
            text, body = detect_text_bytes(bucket, key)
        except Exception as e:
            print(f"OCR failed for s3://{bucket}/{key}: {e}")
            return ret(500, {"error": f"OCR failed: {str(e)}"})
        
        if not text.strip():
            print(f"No text extracted from s3://{bucket}/{key}")
            return ret(400, {"error": "No readable text found in document"})
        
        docType, cls_conf = classify_doc(text)
        
        doc_id = str(uuid.uuid4())
        
        if docType == "W-2":
            if not QUERIES_W2:
                raise RuntimeError("W-2 QuerySet missing; cannot extract.")
            analyzed = analyze_doc_bytes(body, ["FORMS","TABLES","QUERIES"], QUERIES_W2)
            tex_q = extract_query_answers(analyzed)
            claude = call_claude_json(prompt_for_w2() + "\n\nTEXT:\n" + text[:20000])
            fields, source, conf = merge_w2_fields(tex_q, claude)
            issues = validate_w2_fields(fields)
            
            item = {
                "pk": f"user#{user_id}", "sk": f"doc#{doc_id}",
                "docType": docType, "docTypeConfidence": decimal.Decimal(str(cls_conf)),
                "fields": fields, "issues": issues, 
                "s3": {"bucket":bucket,"key":key}, 
                "ts": datetime.utcnow().isoformat(),
                "filename": key.split('/')[-1]
            }
            ddb.put_item(Item=item)
            s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet":[{"Key":"DocType","Value":docType}]})
            
            return ret(200, {
                "docId": doc_id, "docType": docType, "docTypeConfidence": cls_conf,
                "summary": "", "fields": fields, "keyValues": [], "tables": [],
                "source": source, "confidence": conf, "issues": issues,
                "s3": {"bucket": bucket, "key": key}
            })
        
        elif docType in {"INVOICE","RECEIPT"}:
            exp = textract.analyze_expense(Document={"Bytes": body})
            fields = normalize_expense(exp)
            
            item = {
                "pk": f"user#{user_id}", "sk": f"doc#{doc_id}",
                "docType": docType, "fields": fields,
                "s3": {"bucket":bucket,"key":key}, 
                "ts": datetime.utcnow().isoformat(),
                "filename": key.split('/')[-1]
            }
            ddb.put_item(Item=item)
            s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet":[{"Key":"DocType","Value":docType}]})
            
            return ret(200, {
                "docId": doc_id, "docType": docType, "docTypeConfidence": cls_conf,
                "summary": "", "fields": fields, "keyValues": [], "tables": [],
                "source": {"_all":"textract"}, "confidence": {"_all":0.95}, "issues": [],
                "s3": {"bucket": bucket, "key": key}
            })
        
        else:
            # Generic document processing
            return process_generic_document(body, text, docType, cls_conf, bucket, key, doc_id)

def process_generic_document(body, text, docType, cls_conf, bucket, key, doc_id):
    """Process unknown/generic documents with comprehensive extraction"""
    
    # Multi-layer extraction for unknowns
    analyzed = analyze_doc_bytes(body, ["FORMS","TABLES"])
    
    # Layer 1: Textract forms and tables
    kv_pairs = forms_kv(analyzed)
    tables = extract_tables(analyzed)
    
    # Layer 2: LLM comprehensive extraction
    llm_prompt = f"""Analyze this document and extract ALL useful information. Return JSON:
{{
  "document_type_guess": "CONTRACT|LETTER|BANK_STATEMENT|INSURANCE|OTHER",
  "key_information": {{"field_name": "value"}},
  "summary": "one sentence summary",
  "entities": [{{"type": "PERSON|ORG|DATE|AMOUNT", "value": "...", "confidence": 0.9}}]
}}

TEXT:\n{text[:15000]}"""
    
    llm_result = call_claude_json(llm_prompt)
    
    # Update document type if LLM has better guess
    if llm_result.get("document_type_guess") and cls_conf < 0.7:
        docType = llm_result["document_type_guess"]
        cls_conf = 0.8
    
    # Merge all extracted data
    all_fields = llm_result.get("key_information", {})
    entities = llm_result.get("entities", [])
    summary = llm_result.get("summary", "")
    
    # Convert entities to key-value pairs
    for entity in entities:
        if entity.get("confidence", 0) > 0.7:
            key_name = f"{entity['type'].lower()}_{len(all_fields)}"
            all_fields[key_name] = entity["value"]
    
    # Merge Textract KV pairs
    keyValues = merge_generic_kv(kv_pairs, [{"key": k, "value": v} for k, v in all_fields.items()])
    
    payload = {
        "docId": doc_id, "docType": docType, "docTypeConfidence": cls_conf,
        "summary": summary, "keyValues": keyValues, "tables": tables,
        "fields": all_fields, "entities": entities, "issues": [],
        "s3": {"bucket": bucket, "key": key}
    }
    
    ddb.put_item(Item={"pk":f"user#{user_id}","sk":f"doc#{doc_id}", "filename": key.split('/')[-1], **payload})
    s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet":[{"Key":"DocType","Value":docType}]})
    
    return ret(200, payload)

def extract_tables(analyzed):
    """Extract tables from Textract response"""
    ids = {b["Id"]: b for b in analyzed.get("Blocks", [])}
    tables = []
    
    for b in analyzed.get("Blocks", []):
        if b["BlockType"] == "TABLE":
            grid = {}
            for r in b.get("Relationships", []):
                if r["Type"] == "CHILD":
                    for cid in r["Ids"]:
                        cell = ids[cid]
                        if cell["BlockType"] == "CELL":
                            row, col = cell["RowIndex"], cell["ColumnIndex"]
                            txt = get_text(cell, ids)
                            grid.setdefault(row, {})[col] = txt
            
            rows = []
            for r in sorted(grid):
                row = [grid[r].get(c, "") for c in sorted(grid[r])]
                rows.append(row)
            
            if rows:
                tables.append({"name": f"Table {len(tables)+1}", "rows": rows})
    
    return tables
    
    # API Gateway
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
        
        # Upload to S3 then process
        key = f"uploads/{uuid.uuid4()}_{fname}"
        s3.put_object(Bucket=UPLOAD_BUCKET, Key=key, Body=content)
        
        # Recurse as S3 event with user context
        s3_event = {
            "Records":[{"s3":{"bucket":{"name":UPLOAD_BUCKET},"object":{"key":key}}}],
            "requestContext": event.get("requestContext", {}),
            "headers": event.get("headers", {})
        }
        return lambda_handler(s3_event, None)
    
    return ret(400, {"error":"bad request"})