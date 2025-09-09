import json
import re
from collections import namedtuple
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Any

# Core data structures
Candidate = namedtuple("Candidate", "value conf src page geom")

# Enhanced regex patterns
MONEY_RE = re.compile(r'^\$?\s*([0-9,]+(?:\.[0-9]{1,2})?)$')
SSN_RE = re.compile(r'(\d{3})[- ]?(\d{2})[- ]?(\d{4})')
EIN_RE = re.compile(r'(\d{2})[- ]?(\d{7})')
DATE_RE = re.compile(r'(\d{4})[-/](\d{2})[-/](\d{2})|(\d{2})/(\d{2})/(\d{4})')

def collect_candidates(resp: dict, raw_text: str, doc_type: str) -> Dict[str, List[Candidate]]:
    """Collect all field candidates from multiple sources"""
    candidates = {}
    blocks = {b["Id"]: b for b in resp.get("Blocks", [])}
    
    # Q: Query results
    query_cands = extract_query_candidates(resp)
    for field, cand in query_cands.items():
        candidates.setdefault(field, []).append(cand)
    
    # F: Forms key-value pairs
    form_cands = extract_form_candidates(resp, blocks)
    for field, cand in form_cands.items():
        candidates.setdefault(field, []).append(cand)
    
    # T: Table cells
    table_cands = extract_table_candidates(resp, blocks, doc_type)
    for field, cand in table_cands.items():
        candidates.setdefault(field, []).append(cand)
    
    # R: Regex patterns
    regex_cands = extract_regex_candidates(raw_text)
    for field, cand in regex_cands.items():
        candidates.setdefault(field, []).append(cand)
    
    # H: Geometry heuristics
    geo_cands = extract_geometry_candidates(blocks, raw_text)
    for field, cand in geo_cands.items():
        candidates.setdefault(field, []).append(cand)
    
    return candidates

def extract_query_candidates(resp: dict) -> Dict[str, Candidate]:
    """Extract candidates from Textract query results"""
    candidates = {}
    blocks = {b["Id"]: b for b in resp.get("Blocks", [])}
    
    # Map queries to aliases
    query_to_alias = {}
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "QUERY":
            alias = b.get("Query", {}).get("Alias")
            if alias:
                query_to_alias[b["Id"]] = alias
    
    # Match results to queries
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "QUERY_RESULT":
            text = b.get("Text", "").strip()
            confidence = b.get("Confidence", 0) / 100 if b.get("Confidence", 0) > 1 else b.get("Confidence", 0)
            
            # Find parent query
            for rel in b.get("Relationships", []):
                for ref_id in rel.get("Ids", []):
                    if ref_id in query_to_alias:
                        alias = query_to_alias[ref_id]
                        candidates[alias] = Candidate(
                            value=text,
                            conf=confidence,
                            src="Q",
                            page=b.get("Page", 1),
                            geom=b.get("Geometry", {})
                        )
                        break
    
    # Fallback: position matching
    if not candidates:
        queries = [b for b in resp.get("Blocks", []) if b["BlockType"] == "QUERY"]
        results = [b for b in resp.get("Blocks", []) if b["BlockType"] == "QUERY_RESULT"]
        
        for query, result in zip(queries, results):
            alias = query.get("Query", {}).get("Alias")
            if alias:
                text = result.get("Text", "").strip()
                confidence = result.get("Confidence", 0) / 100 if result.get("Confidence", 0) > 1 else result.get("Confidence", 0)
                candidates[alias] = Candidate(
                    value=text,
                    conf=confidence,
                    src="Q",
                    page=result.get("Page", 1),
                    geom=result.get("Geometry", {})
                )
    
    return candidates

def extract_form_candidates(resp: dict, blocks: dict) -> Dict[str, Candidate]:
    """Extract candidates from Forms key-value pairs"""
    candidates = {}
    
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "KEY_VALUE_SET" and "KEY" in b.get("EntityTypes", []):
            key_text = gather_text(blocks, b, "CHILD").lower()
            val_text = ""
            
            for rel in b.get("Relationships", []):
                if rel["Type"] == "VALUE":
                    for vid in rel["Ids"]:
                        val_text = gather_text(blocks, blocks[vid], "CHILD")
            
            if key_text and val_text:
                # Map common form keys to field names
                field_name = map_form_key(key_text)
                if field_name:
                    candidates[field_name] = Candidate(
                        value=val_text,
                        conf=0.85,  # Forms generally reliable
                        src="F",
                        page=b.get("Page", 1),
                        geom=b.get("Geometry", {})
                    )
    
    return candidates

def extract_table_candidates(resp: dict, blocks: dict, doc_type: str) -> Dict[str, Candidate]:
    """Extract candidates from table cells"""
    candidates = {}
    
    for b in resp.get("Blocks", []):
        if b["BlockType"] == "TABLE":
            table_data = extract_table_data(b, blocks)
            
            # Map table data to fields based on document type
            if doc_type == "PAYSTUB":
                candidates.update(extract_paystub_table_fields(table_data))
            elif doc_type == "BANK_STATEMENT":
                candidates.update(extract_bank_table_fields(table_data))
    
    return candidates

def extract_regex_candidates(text: str) -> Dict[str, Candidate]:
    """Extract candidates using regex patterns"""
    candidates = {}
    
    # SSN patterns
    ssn_matches = SSN_RE.findall(text)
    if ssn_matches:
        candidates["employee_ssn"] = Candidate(
            value=f"{ssn_matches[0][0]}-{ssn_matches[0][1]}-{ssn_matches[0][2]}",
            conf=0.90,
            src="R",
            page=1,
            geom={}
        )
    
    # EIN patterns
    ein_matches = EIN_RE.findall(text)
    if ein_matches:
        candidates["employer_ein"] = Candidate(
            value=f"{ein_matches[0][0]}-{ein_matches[0][1]}",
            conf=0.90,
            src="R",
            page=1,
            geom={}
        )
    
    # Money amounts
    money_matches = re.findall(r'\$[0-9,]+(?:\.[0-9]{2})?', text)
    if money_matches:
        # Map first few amounts to common fields
        amount_fields = ["total", "subtotal", "tax", "amount_due"]
        for i, amount in enumerate(money_matches[:4]):
            if i < len(amount_fields):
                candidates[amount_fields[i]] = Candidate(
                    value=amount,
                    conf=0.75,
                    src="R",
                    page=1,
                    geom={}
                )
    
    return candidates

def extract_geometry_candidates(blocks: dict, text: str) -> Dict[str, Candidate]:
    """Extract candidates using geometric relationships"""
    candidates = {}
    
    # Find label-value pairs by proximity
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if ':' in line and len(line) < 200:
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip().lower()
                value = parts[1].strip()
                
                field_name = map_geometry_key(key)
                if field_name and value:
                    candidates[field_name] = Candidate(
                        value=value,
                        conf=0.70,
                        src="H",
                        page=1,
                        geom={}
                    )
    
    return candidates

def resolve_field(candidates: List[Candidate], field_key: str) -> Optional[dict]:
    """Smart field resolver with scoring and tie-breakers"""
    if not candidates:
        return None
    
    def base_score(c):
        return min(max(c.conf, 0.0), 1.0)
    
    def plausibility_bonus(field, v):
        s = str(v).strip()
        
        # SSN validation
        if field.endswith("_ssn"):
            return 0.2 if re.fullmatch(r"\d{3}-\d{2}-\d{4}", s) else -0.2
        
        # EIN validation
        if field.endswith("_ein"):
            return 0.2 if re.fullmatch(r"\d{2}-\d{7}", s) else -0.2
        
        # Money validation
        if any(k in field for k in ["wages", "tax", "total", "amount", "subtotal", "balance"]):
            try:
                float(s.replace(",", "").replace("$", ""))
                return 0.1
            except:
                return -0.3
        
        # Date validation
        if "date" in field:
            return 0.1 if normalize_date(s) else -0.2
        
        return 0.0
    
    def geometry_bonus(c):
        return 0.1 if c.src in ("H", "F_geo") else 0.0
    
    # Score all candidates
    scored = []
    for c in candidates:
        score = base_score(c) + plausibility_bonus(field_key, c.value) + geometry_bonus(c)
        scored.append((score, c))
    
    # Get best candidate
    best_score, best = max(scored)
    
    # Normalize value
    normalized_value = normalize_value(field_key, best.value)
    
    return {
        "value": normalized_value,
        "confidence": round(min(1.0, best_score + 0.15), 3),
        "source": best.src
    }

def normalize_value(key: str, val: Any) -> str:
    """Normalize values based on field type"""
    s = "" if val is None else str(val).strip()
    
    # Money normalization
    if re.search(r"(total|amount|wages|tax|subtotal|balance|ytd|gross|net)", key, re.I):
        try:
            clean_val = s.replace('$', '').replace(',', '')
            return f"${float(clean_val):,.2f}"
        except:
            return s
    
    # EIN normalization
    if re.search(r"(ein)$", key, re.I):
        m = re.search(r"(\d{2})[- ]?(\d{7})", s)
        return f"{m.group(1)}-{m.group(2)}" if m else s
    
    # SSN normalization
    if re.search(r"(ssn)$", key, re.I):
        m = re.search(r"(\d{3})[- ]?(\d{2})[- ]?(\d{4})", s)
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else s
    
    # Date normalization
    if "date" in key:
        return normalize_date(s) or s
    
    return s

def normalize_date(s: str) -> Optional[str]:
    """Normalize date to ISO format"""
    m = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})|(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        if m.group(1):  # YYYY-MM-DD format
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        else:  # MM/DD/YYYY format
            return f"{m.group(6)}-{m.group(4)}-{m.group(5)}"
    return None

def validate_document(fields: dict, doc_type: str) -> tuple[bool, List[str]]:
    """Cross-field validation with document-specific rules"""
    errors = []
    
    if doc_type == "W-2":
        # Check for required fields
        required = ["box1_wages", "box2_fed_tax", "box3_ss_wages"]
        missing = [f for f in required if not fields.get(f)]
        if missing:
            errors.append(f"Missing required W-2 fields: {missing}")
        
        # Validate amounts are non-negative
        for field in ["box1_wages", "box2_fed_tax", "box3_ss_wages", "box4_ss_tax"]:
            if field in fields:
                try:
                    val = float(str(fields[field]).replace('$', '').replace(',', ''))
                    if val < 0:
                        errors.append(f"{field} cannot be negative")
                except:
                    pass
    
    elif doc_type == "INVOICE":
        # Validate invoice math
        subtotal = get_numeric_value(fields.get("subtotal", 0))
        tax = get_numeric_value(fields.get("tax", 0))
        total = get_numeric_value(fields.get("total", 0))
        
        if subtotal and tax and total:
            expected = subtotal + tax
            if abs(expected - total) / total > 0.01:  # 1% tolerance
                errors.append(f"Invoice math error: {subtotal} + {tax} ≠ {total}")
    
    elif doc_type == "PAYSTUB":
        # Validate paystub math
        gross = get_numeric_value(fields.get("gross_pay", 0))
        net = get_numeric_value(fields.get("net_pay", 0))
        
        if gross and net and gross < net:
            errors.append("Net pay cannot exceed gross pay")
    
    needs_review = len(errors) > 0
    return needs_review, errors

def check_acceptance(fields: dict, doc_type: str) -> bool:
    """Check if document meets acceptance criteria"""
    if doc_type == "W-2":
        core_fields = ["box1_wages", "box2_fed_tax", "box3_ss_wages", "box4_ss_tax", "box5_medicare_wages", "box6_medicare_tax"]
        id_fields = ["employee_ssn", "employer_ein", "taxyear"]
        
        core_count = sum(1 for f in core_fields if fields.get(f))
        id_count = sum(1 for f in id_fields if fields.get(f))
        
        return core_count >= 6 and id_count >= 2
    
    elif doc_type == "INVOICE":
        required = ["vendor", "date", "total"]
        return all(fields.get(f) for f in required)
    
    elif doc_type == "ID_CARD":
        required = ["first_name", "last_name", "document_number", "date_of_birth"]
        return all(fields.get(f) for f in required)
    
    return len(fields) >= 3  # Default: at least 3 fields

# Helper functions
def gather_text(blocks: dict, blk: dict, child_type: str) -> str:
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

def map_form_key(key: str) -> Optional[str]:
    """Map form keys to standardized field names"""
    key_lower = key.lower()
    
    if 'employee' in key_lower and 'ssn' in key_lower:
        return 'employee_ssn'
    elif 'employer' in key_lower and ('ein' in key_lower or 'id' in key_lower):
        return 'employer_ein'
    elif 'employee' in key_lower and 'name' in key_lower:
        return 'employee_name'
    elif 'employer' in key_lower and 'name' in key_lower:
        return 'employer_name'
    elif 'account' in key_lower and 'number' in key_lower:
        return 'account_number'
    elif 'total' in key_lower:
        return 'total'
    elif 'amount' in key_lower and 'due' in key_lower:
        return 'amount_due'
    
    return None

def map_geometry_key(key: str) -> Optional[str]:
    """Map geometry-detected keys to field names"""
    key_lower = key.lower()
    
    if 'account' in key_lower:
        return 'account_number'
    elif 'total' in key_lower:
        return 'total'
    elif 'date' in key_lower:
        return 'date'
    elif 'amount' in key_lower:
        return 'amount_due'
    
    return None

def extract_table_data(table_block: dict, blocks: dict) -> List[List[str]]:
    """Extract structured data from table"""
    grid = {}
    
    for rel in table_block.get("Relationships", []):
        if rel["Type"] == "CHILD":
            for cid in rel["Ids"]:
                cell = blocks[cid]
                if cell["BlockType"] == "CELL":
                    row, col = cell["RowIndex"], cell["ColumnIndex"]
                    text = gather_text(blocks, cell, "CHILD")
                    grid.setdefault(row, {})[col] = text
    
    rows = []
    for r in sorted(grid):
        row = [grid[r].get(c, "") for c in sorted(grid[r])]
        rows.append(row)
    
    return rows

def extract_paystub_table_fields(table_data: List[List[str]]) -> Dict[str, Candidate]:
    """Extract paystub-specific fields from table data"""
    candidates = {}
    
    for row in table_data:
        if len(row) >= 2:
            desc = row[0].lower()
            amount = row[-1]
            
            if 'regular' in desc or 'salary' in desc:
                candidates['regular_pay'] = Candidate(amount, 0.80, "T", 1, {})
            elif 'overtime' in desc:
                candidates['overtime_pay'] = Candidate(amount, 0.80, "T", 1, {})
            elif 'federal' in desc and 'tax' in desc:
                candidates['federal_tax'] = Candidate(amount, 0.80, "T", 1, {})
    
    return candidates

def extract_bank_table_fields(table_data: List[List[str]]) -> Dict[str, Candidate]:
    """Extract bank statement fields from table data"""
    candidates = {}
    
    # Calculate totals from transactions
    total_deposits = 0
    total_withdrawals = 0
    
    for row in table_data[1:]:  # Skip header
        if len(row) >= 3:
            try:
                amount = float(row[-1].replace(',', '').replace('$', ''))
                if amount > 0:
                    total_deposits += amount
                else:
                    total_withdrawals += abs(amount)
            except:
                continue
    
    if total_deposits > 0:
        candidates['total_deposits'] = Candidate(f"${total_deposits:,.2f}", 0.85, "T", 1, {})
    if total_withdrawals > 0:
        candidates['total_withdrawals'] = Candidate(f"${total_withdrawals:,.2f}", 0.85, "T", 1, {})
    
    return candidates

def get_numeric_value(val: Any) -> float:
    """Extract numeric value from string"""
    try:
        return float(str(val).replace('$', '').replace(',', ''))
    except:
        return 0.0