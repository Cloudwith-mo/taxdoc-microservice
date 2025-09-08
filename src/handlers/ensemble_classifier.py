import os
import boto3
import json
import re
from typing import Dict, Tuple, Optional

class EnsembleClassifier:
    """Production-ready ensemble classifier with heuristics, Comprehend, and LLM fallback"""
    
    def __init__(self):
        self.comprehend = boto3.client("comprehend")
        self.bedrock = boto3.client("bedrock-runtime")
        self.endpoint_arn = os.environ.get("COMPREHEND_ENDPOINT")
        self.conf_thresh_primary = float(os.environ.get("CONF_THRESH_PRIMARY", "0.80"))
        self.conf_thresh_heuristic = float(os.environ.get("CONF_THRESH_HEURISTIC", "0.85"))
    
    def classify(self, text: str) -> Dict:
        """Ensemble classification with confidence thresholds and tracing"""
        
        # Stage A: Heuristics (fastest)
        heuristic_result = self._classify_heuristic(text)
        
        # Stage B: Comprehend (primary ML)
        comprehend_result = self._classify_comprehend(text)
        
        # Decision logic with tracing
        trace = {
            "heuristic": heuristic_result["score"],
            "comprehend": comprehend_result["score"] if comprehend_result else None,
            "llm": None
        }
        
        # Use Comprehend if high confidence
        if comprehend_result and comprehend_result["score"] >= self.conf_thresh_primary:
            return {
                "label": comprehend_result["label"],
                "score": comprehend_result["score"],
                "source": "comprehend",
                "trace": trace
            }
        
        # Use heuristics if high confidence
        if heuristic_result["score"] >= self.conf_thresh_heuristic:
            return {
                "label": heuristic_result["label"],
                "score": heuristic_result["score"],
                "source": "heuristic",
                "trace": trace
            }
        
        # Stage C: LLM fallback (selective)
        llm_result = self._classify_llm(text[:8000])  # Trim for cost
        trace["llm"] = llm_result["score"]
        
        return {
            "label": llm_result["label"],
            "score": llm_result["score"],
            "source": "llm",
            "trace": trace
        }
    
    def _classify_heuristic(self, text: str) -> Dict:
        """Fast heuristic classification with confidence scoring"""
        t = text.lower()
        
        # High confidence patterns
        if "wage and tax statement" in t or "form w-2" in t:
            return {"label": "W-2", "score": 0.99}
        if "form 1099-nec" in t:
            return {"label": "1099-NEC", "score": 0.98}
        if "form 1099-misc" in t:
            return {"label": "1099-MISC", "score": 0.98}
        
        # Medium confidence patterns
        if "invoice" in t and ("total" in t or "amount due" in t):
            return {"label": "INVOICE", "score": 0.90}
        if "receipt" in t or ("merchant" in t and "purchase" in t):
            return {"label": "RECEIPT", "score": 0.85}
        if "driver" in t and "license" in t:
            return {"label": "DRIVERS_LICENSE", "score": 0.90}
        if "passport" in t and ("united states" in t or "department of state" in t):
            return {"label": "PASSPORT", "score": 0.90}
        
        # Lower confidence patterns
        if "contract" in t or "agreement" in t:
            return {"label": "CONTRACT", "score": 0.75}
        if "bank statement" in t or "account summary" in t:
            return {"label": "BANK_STATEMENT", "score": 0.80}
        if "dear" in t or "sincerely" in t:
            return {"label": "LETTER", "score": 0.70}
        
        return {"label": "UNKNOWN", "score": 0.50}
    
    def _classify_comprehend(self, text: str) -> Optional[Dict]:
        """Comprehend custom classifier with error handling"""
        if not self.endpoint_arn:
            return None
        
        try:
            response = self.comprehend.classify_document(
                Text=text[:5000],  # Comprehend limit
                EndpointArn=self.endpoint_arn
            )
            
            classes = response.get("Classes", [])
            if classes:
                top_class = max(classes, key=lambda x: x["Score"])
                return {
                    "label": top_class["Name"],
                    "score": top_class["Score"]
                }
        except Exception as e:
            print(f"Comprehend classification failed: {e}")
        
        return None
    
    def _classify_llm(self, text: str) -> Dict:
        """LLM classification with structured prompt"""
        
        prompt = f"""Classify this document into one category. Return ONLY JSON:
{{"docType": "W-2|1099-NEC|1099-MISC|INVOICE|RECEIPT|DRIVERS_LICENSE|PASSPORT|CONTRACT|LETTER|BANK_STATEMENT|UNKNOWN", "confidence": 0.95}}

Document text:
{text}"""
        
        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",  # Faster/cheaper for classification
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 100,
                    "temperature": 0,
                    "messages": [{"role": "user", "content": prompt}]
                })
            )
            
            result = json.loads(response["body"].read())
            content = result["content"][0]["text"]
            
            # Extract JSON
            start, end = content.find("{"), content.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(content[start:end+1])
                return {
                    "label": parsed.get("docType", "UNKNOWN"),
                    "score": float(parsed.get("confidence", 0.75))
                }
        except Exception as e:
            print(f"LLM classification failed: {e}")
        
        return {"label": "UNKNOWN", "score": 0.60}

def get_hierarchical_labels(doc_type: str, extracted_fields: Dict) -> list:
    """Generate hierarchical labels for enhanced tagging"""
    labels = [doc_type.lower()]
    
    # Add subtype labels
    if doc_type == "INVOICE" and "vendor" in extracted_fields:
        vendor = extracted_fields["vendor"].get("value", "").lower()
        if vendor:
            labels.append(f"invoice:vendor/{vendor}")
    
    if doc_type.startswith("1099") and "payer_name" in extracted_fields:
        payer = extracted_fields["payer_name"].get("value", "").lower()
        if payer:
            labels.append(f"1099:payer/{payer}")
    
    # Add tax year if date found
    for field_name, field_data in extracted_fields.items():
        if "date" in field_name.lower() and isinstance(field_data, dict):
            date_str = field_data.get("value", "")
            year_match = re.search(r"20\d{2}", str(date_str))
            if year_match:
                labels.append(f"taxyear/{year_match.group()}")
                break
    
    return labels