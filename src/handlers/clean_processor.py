import os, json, uuid, re, boto3, decimal
from datetime import datetime

textract = boto3.client("textract")
s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb").Table(os.environ.get("RESULTS_TABLE", "DrDocDocuments-prod"))
bedrock = boto3.client("bedrock-runtime")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json"
}

def ret(code, body):
    return {
        "statusCode": code,
        "headers": CORS,
        "body": json.dumps(body, default=lambda o: float(o) if isinstance(o, decimal.Decimal) else o)
    }

def detect_text_bytes(bucket, key):
    """Read from S3 and call Textract with Bytes to avoid KMS/S3 access issues"""
    obj = s3.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    response = textract.detect_document_text(Document={"Bytes": body})
    lines = [b["Text"] for b in response.get("Blocks", []) if b["BlockType"] == "LINE"]
    text = "\n".join(lines)
    print(f"OCR bytes={len(body)}, lines={len(lines)} for s3://{bucket}/{key}")
    return text, body

def classify_doc(text):
    """Enhanced heuristic classification for W-2 detection"""
    t = text.lower()
    
    # W-2 specific patterns
    w2_patterns = [
        "wage and tax statement", "form w-2", "w-2", "wages tips", 
        "federal income tax withheld", "social security wages", 
        "medicare wages", "employer identification number", "ein",
        "employee social security number", "control number",
        "wages salaries tips", "box 1", "box 2", "box 3", "box 5"
    ]
    
    w2_score = sum(1 for pattern in w2_patterns if pattern in t)
    if w2_score >= 3:  # Multiple W-2 indicators
        return "W-2", min(0.85 + (w2_score * 0.03), 0.99)
    
    # Other document types
    if "form 1099-nec" in t:
        return "1099-NEC", 0.98
    if "form 1099-misc" in t:
        return "1099-MISC", 0.98
    if "invoice" in t and "total" in t:
        return "INVOICE", 0.9
    if "receipt" in t:
        return "RECEIPT", 0.85
    
    return "UNKNOWN", 0.6

def lambda_handler(event, ctx):
    print(f"Event: {json.dumps(event)}")
    
    # Handle API Gateway events
    if "httpMethod" in event or "requestContext" in event:
        try:
            body = event.get('body', '{}')
            if isinstance(body, str):
                body = json.loads(body)
            
            s3_key = body.get('s3Key', '')
            if not s3_key:
                return ret(400, {"error": "No s3Key provided"})
            
            # Convert to S3 event format
            bucket = "taxflowsai-uploads"  # Match upload handler bucket
            if not s3_key.startswith('uploads/'):
                s3_key = f'uploads/{s3_key}'
            
            # Process as S3 event
            return process_document(bucket, s3_key)
            
        except Exception as e:
            print(f"API Gateway processing error: {e}")
            return ret(500, {"error": str(e)})
    
    # Handle S3 events
    elif "Records" in event and event["Records"][0].get("s3"):
        rec = event["Records"][0]["s3"]
        bucket = rec["bucket"]["name"]
        key = rec["object"]["key"]
        return process_document(bucket, key)
    
    return ret(400, {"error": "Invalid event format"})

def extract_fields_with_ai(text, doc_type):
    """Extract fields using Claude AI for any document type"""
    try:
        if doc_type == "W-2":
            schema = '{"employee_name": "", "employer_name": "", "wages": "", "federal_tax_withheld": "", "social_security_wages": "", "social_security_tax": "", "medicare_wages": "", "medicare_tax": "", "ssn": "", "ein": "", "state": "", "state_wages": "", "state_tax": ""}'
        elif doc_type == "1099-NEC":
            schema = '{"payer_name": "", "payer_address": "", "payer_tin": "", "recipient_name": "", "recipient_address": "", "recipient_tin": "", "nonemployee_compensation": "", "federal_tax_withheld": "", "state_tax_withheld": "", "state": "", "account_number": ""}'
        elif doc_type == "1099-MISC":
            schema = '{"payer_name": "", "payer_address": "", "payer_tin": "", "recipient_name": "", "recipient_address": "", "recipient_tin": "", "rents": "", "royalties": "", "other_income": "", "federal_tax_withheld": "", "state_tax_withheld": "", "state": ""}'
        elif doc_type == "INVOICE":
            schema = '{"invoice_number": "", "invoice_date": "", "due_date": "", "vendor_name": "", "vendor_address": "", "customer_name": "", "customer_address": "", "subtotal": "", "tax_amount": "", "total_amount": "", "payment_terms": ""}'
        elif doc_type == "RECEIPT":
            schema = '{"merchant_name": "", "merchant_address": "", "transaction_date": "", "transaction_time": "", "items": "", "subtotal": "", "tax_amount": "", "total_amount": "", "payment_method": "", "receipt_number": ""}'
        else:
            schema = '{"document_type": "", "date": "", "amount": "", "description": "", "parties_involved": ""}'

        prompt = f"""Extract data from this {doc_type} document and return ONLY a JSON object matching this schema:

{schema}

OCR Text:
{text}

Return only the JSON object, no other text:"""

        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        ai_response = result['content'][0]['text'].strip()
        
        # Extract JSON from response
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(ai_response[json_start:json_end])
            
    except Exception as e:
        print(f"AI extraction failed: {e}")
    
    return {"error": "AI extraction failed", "raw_text_length": len(text)}

def extract_1099_fields_with_ai(text):
    """Extract 1099-NEC fields using Claude AI"""
    try:
        prompt = f"""Extract 1099-NEC tax form data from this OCR text and return ONLY a JSON object with these exact field names:

{{
  "payer_name": "company/payer name",
  "payer_address": "payer address",
  "payer_tin": "payer tax ID number",
  "recipient_name": "recipient/contractor name",
  "recipient_address": "recipient address", 
  "recipient_tin": "recipient tax ID/SSN",
  "nonemployee_compensation": "box 1 amount",
  "federal_tax_withheld": "box 4 amount if any",
  "state_tax_withheld": "box 5 amount if any",
  "state": "state abbreviation",
  "account_number": "account number if any"
}}

OCR Text:
{text}

Return only the JSON object, no other text:"""

        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        ai_response = result['content'][0]['text'].strip()
        
        # Extract JSON from response
        json_start = ai_response.find('{')
        json_end = ai_response.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(ai_response[json_start:json_end])
            
    except Exception as e:
        print(f"AI extraction failed: {e}")
    
    # Fallback to basic extraction
    return {"extracted_text_length": len(text)}

def extract_w2_fields_basic(text):
    """Basic W-2 field extraction as fallback"""
    fields = {}
    
    # Extract key fields from the actual OCR output
    patterns = {
        'employee_name': r'(?:Last name|e Employee).*?([A-Z][a-z]+).*?(?:first name).*?([A-Z][a-z]+)',
        'employer_name': r'c Employer.*?\n([^\n]+)',
        'wages': r'1 Wages.*?([\d,]+\.\d{2})',
        'federal_tax_withheld': r'2 Federal income tax.*?([\d,]+\.\d{2})',
        'social_security_wages': r'3 Social security wages.*?([\d,]+\.\d{2})',
        'social_security_tax': r'4 Social security tax.*?([\d,]+\.\d{2})',
        'medicare_wages': r'5 Medicare wages.*?([\d,]+\.\d{2})',
        'medicare_tax': r'6 Medicare tax.*?([\d,]+\.\d{2})',
        'ssn': r'a Employee.*?(\d{3}-\d{2}-\d{4})',
        'ein': r'b Employer.*?(\d{2}-\d{7})',
        'state': r'15 State\s+([A-Z]{2})',
        'state_wages': r'16 State wages.*?([\d,]+)',
        'state_tax': r'17 State income tax.*?([\d,]+)'
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            if field == 'employee_name' and match.lastindex >= 2:
                fields[field] = f"{match.group(2)} {match.group(1)}"
            else:
                fields[field] = match.group(1).strip()
    
    return fields

def process_document(bucket, key):
    """Process document from S3 bucket and key"""
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
    
    # Extract fields using AI for all document types
    fields = extract_fields_with_ai(text, docType)
    
    result = {
        "docId": doc_id,
        "docType": docType,
        "docTypeConfidence": cls_conf,
        "summary": f"Processed {docType} document",
        "fields": fields,
        "keyValues": [],
        "tables": [],
        "issues": [],
        "s3": {"bucket": bucket, "key": key}
    }
    
    # Store in DynamoDB
    try:
        ddb.put_item(Item={
            "pk": "user#unknown",
            "sk": f"doc#{doc_id}",
            "docType": docType,
            "docTypeConfidence": decimal.Decimal(str(cls_conf)),
            "fields": result["fields"],
            "s3": {"bucket": bucket, "key": key},
            "ts": datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"DynamoDB error: {e}")
    
    return ret(200, result)