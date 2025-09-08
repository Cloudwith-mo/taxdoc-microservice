import os, json, uuid, re, boto3, decimal
from datetime import datetime

textract = boto3.client("textract")
s3 = boto3.client("s3")
ddb = boto3.resource("dynamodb").Table(os.environ.get("RESULTS_TABLE", "TaxDocuments-dev"))
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
            bucket = 'taxflowsai-uploads'
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
    
    # Simple response for all document types
    result = {
        "docId": doc_id,
        "docType": docType,
        "docTypeConfidence": cls_conf,
        "summary": f"Processed {docType} document",
        "fields": {"extracted_text_length": len(text)},
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