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

def detect_text_bytes(body):
    """Call Textract with Bytes"""
    response = textract.detect_document_text(Document={"Bytes": body})
    lines = [b["Text"] for b in response.get("Blocks", []) if b["BlockType"] == "LINE"]
    text = "\n".join(lines)
    print(f"OCR bytes={len(body)}, lines={len(lines)}")
    return text

def classify_doc(text):
    """Simple document classification"""
    t = text.lower()
    if "wage and tax statement" in t or "form w-2" in t: return "W-2", 0.99
    if "form 1099-nec" in t: return "1099-NEC", 0.98
    if "form 1099-misc" in t: return "1099-MISC", 0.98
    if "invoice" in t and "total" in t: return "INVOICE", 0.9
    if "receipt" in t: return "RECEIPT", 0.85
    return "UNKNOWN", 0.6

def lambda_handler(event, context):
    print(f"Event: {json.dumps(event)}")
    
    # Handle OPTIONS for CORS
    method = event.get("httpMethod", "")
    if method == "OPTIONS":
        return {"statusCode": 200, "headers": CORS, "body": ""}
    
    if method != "POST":
        return ret(405, {"error": "Method not allowed"})
    
    try:
        body = json.loads(event.get("body", "{}"))
        fname = body.get("filename", "upload.bin")
        b64 = clean_b64(body.get("contentBase64", ""))
        
        if not b64:
            return ret(400, {"error": "No contentBase64 provided"})
        
        content = base64.b64decode(b64)
        if not content:
            return ret(400, {"error": "Empty file"})
        
        # Extract text using Textract
        text = detect_text_bytes(content)
        if not text.strip():
            return ret(400, {"error": "No readable text found in document"})
        
        # Classify document
        docType, confidence = classify_doc(text)
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Simple field extraction for demo
        fields = {}
        keyValues = []
        
        # Extract basic info from text
        lines = text.split('\n')
        for line in lines[:10]:  # First 10 lines
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value:
                        fields[key] = value
                        keyValues.append({"key": key, "value": value})
        
        result = {
            "docId": doc_id,
            "docType": docType,
            "docTypeConfidence": confidence,
            "summary": f"Processed {docType} document with {len(fields)} fields extracted",
            "fields": fields,
            "keyValues": keyValues
        }
        
        return ret(200, result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return ret(500, {"error": str(e)})