import json
import boto3
import os
from typing import Dict, List, Optional

def llm_verify_missing(text: str, known: dict, targets: List[str]) -> dict:
    """Fill missing fields using LLM with surgical precision"""
    if not targets:
        return {}
    
    # Trim text to manageable size
    trimmed_text = trim_text_with_context(text, targets, max_chars=6000)
    
    # Build verification prompt
    prompt = build_verify_prompt(known, targets, trimmed_text)
    
    try:
        # Call Bedrock Claude
        bedrock = boto3.client('bedrock-runtime')
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 250,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = bedrock.invoke_model(
            modelId=os.getenv("CLAUDE_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [{}])[0].get('text', '{}')
        
        # Parse JSON response
        result = json.loads(content)
        
        # Validate result contains only requested keys
        filtered_result = {k: v for k, v in result.items() if k in targets and v is not None}
        
        return filtered_result
        
    except Exception as e:
        print(f"LLM verification failed: {e}")
        return {}

def build_verify_prompt(known: dict, targets: List[str], text: str) -> str:
    """Build surgical LLM prompt for missing field extraction"""
    
    known_json = json.dumps(known, indent=2) if known else "{}"
    targets_json = json.dumps(targets, indent=2)
    
    prompt = f"""You are a terse information extractor.
Return ONLY JSON object with the requested keys. Do not include prose.

Known fields (may be empty):
{known_json}

From the document text below, fill ONLY these keys if you can
with best-guess values:
{targets_json}

Rules:
- Dates in ISO YYYY-MM-DD format
- Money as numbers like 12345.67 (no $ or commas)
- If unknown, return null for that key
- Return valid JSON only

--- TEXT START ---
{text}
--- TEXT END ---

JSON:"""

    return prompt

def trim_text_with_context(text: str, targets: List[str], max_chars: int = 6000) -> str:
    """Trim text while preserving context around target fields"""
    
    if len(text) <= max_chars:
        return text
    
    # Create search terms from targets
    search_terms = []
    for target in targets:
        # Convert field names to likely text patterns
        terms = target.replace('_', ' ').split()
        search_terms.extend(terms)
        
        # Add common variations
        if 'ssn' in target:
            search_terms.extend(['social security', 'ssn'])
        elif 'ein' in target:
            search_terms.extend(['employer id', 'ein', 'tax id'])
        elif 'box' in target:
            search_terms.append('box')
        elif 'wages' in target:
            search_terms.extend(['wages', 'compensation'])
        elif 'tax' in target:
            search_terms.extend(['tax', 'withheld'])
    
    # Find relevant sections
    lines = text.split('\n')
    relevant_lines = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Include line if it contains search terms
        if any(term.lower() in line_lower for term in search_terms):
            # Include context (2 lines before and after)
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            relevant_lines.extend(lines[start:end])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_lines = []
    for line in relevant_lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    # Join and trim to max_chars
    result = '\n'.join(unique_lines)
    
    if len(result) > max_chars:
        # Take first max_chars characters
        result = result[:max_chars]
        # Try to end at a complete line
        last_newline = result.rfind('\n')
        if last_newline > max_chars * 0.8:  # If we can save 80% of content
            result = result[:last_newline]
    
    return result

def get_missing_fields(resolved_fields: dict, required_fields: List[str], confidence_threshold: float = 0.85) -> List[str]:
    """Identify fields that are missing or have low confidence"""
    missing = []
    
    for field in required_fields:
        if field not in resolved_fields:
            missing.append(field)
        else:
            field_data = resolved_fields[field]
            if isinstance(field_data, dict):
                confidence = field_data.get('confidence', 0)
                if confidence < confidence_threshold:
                    missing.append(field)
            elif not field_data or str(field_data).strip() == '':
                missing.append(field)
    
    return missing

def enhance_fields_with_llm(resolved_fields: dict, raw_text: str, doc_type: str) -> dict:
    """Enhance resolved fields with LLM for missing/low-confidence values"""
    
    # Define required fields by document type
    required_by_type = {
        "W-2": [
            "employee_ssn", "employer_ein", "employee_name", "employer_name",
            "box1_wages", "box2_fed_tax", "box3_ss_wages", "box4_ss_tax",
            "box5_medicare_wages", "box6_medicare_tax", "taxyear"
        ],
        "1099-NEC": [
            "payer_tin", "recipient_tin", "recipient_name", "payer_name",
            "nec_amount_box1", "taxyear"
        ],
        "INVOICE": [
            "vendor", "invoice_number", "invoice_date", "total", "subtotal"
        ],
        "PAYSTUB": [
            "employee_name", "employer_name", "pay_date", "gross_pay", "net_pay"
        ],
        "UTILITY_BILL": [
            "provider_name", "account_number", "amount_due", "due_date"
        ]
    }
    
    required_fields = required_by_type.get(doc_type, [])
    missing_fields = get_missing_fields(resolved_fields, required_fields)
    
    if not missing_fields:
        return resolved_fields
    
    print(f"[LLM] Enhancing {len(missing_fields)} missing fields: {missing_fields}")
    
    # Get LLM enhancements
    llm_results = llm_verify_missing(raw_text, resolved_fields, missing_fields)
    
    # Merge LLM results into resolved fields
    enhanced_fields = resolved_fields.copy()
    
    for field, value in llm_results.items():
        if value is not None and str(value).strip():
            enhanced_fields[field] = {
                "value": str(value).strip(),
                "confidence": 0.75,  # LLM confidence
                "source": "LLM"
            }
            print(f"[LLM] Enhanced {field} = {value}")
    
    return enhanced_fields

# Document-specific field requirements
DOCUMENT_REQUIREMENTS = {
    "W-2": {
        "core": ["box1_wages", "box2_fed_tax", "box3_ss_wages", "box4_ss_tax", "box5_medicare_wages", "box6_medicare_tax"],
        "identity": ["employee_ssn", "employer_ein", "taxyear"],
        "optional": ["employee_name", "employer_name", "box7_ss_tips", "box8_alloc_tips"]
    },
    "1099-NEC": {
        "core": ["nec_amount_box1"],
        "identity": ["payer_tin", "recipient_tin", "taxyear"],
        "optional": ["payer_name", "recipient_name", "fed_tax_withheld_box4"]
    },
    "INVOICE": {
        "core": ["vendor", "total"],
        "identity": ["invoice_number", "invoice_date"],
        "optional": ["subtotal", "tax", "due_date"]
    },
    "PAYSTUB": {
        "core": ["gross_pay", "net_pay"],
        "identity": ["employee_name", "pay_date"],
        "optional": ["employer_name", "pay_period_start", "pay_period_end"]
    }
}

def calculate_completeness_score(fields: dict, doc_type: str) -> float:
    """Calculate document completeness score"""
    requirements = DOCUMENT_REQUIREMENTS.get(doc_type, {"core": [], "identity": [], "optional": []})
    
    core_fields = requirements["core"]
    identity_fields = requirements["identity"]
    optional_fields = requirements["optional"]
    
    # Count found fields
    core_found = sum(1 for f in core_fields if f in fields and fields[f])
    identity_found = sum(1 for f in identity_fields if f in fields and fields[f])
    optional_found = sum(1 for f in optional_fields if f in fields and fields[f])
    
    # Calculate weighted score
    core_weight = 0.6
    identity_weight = 0.3
    optional_weight = 0.1
    
    core_score = (core_found / len(core_fields)) if core_fields else 1.0
    identity_score = (identity_found / len(identity_fields)) if identity_fields else 1.0
    optional_score = (optional_found / len(optional_fields)) if optional_fields else 1.0
    
    total_score = (core_score * core_weight + 
                   identity_score * identity_weight + 
                   optional_score * optional_weight)
    
    return round(total_score, 3)