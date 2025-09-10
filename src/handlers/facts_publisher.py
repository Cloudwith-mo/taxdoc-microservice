import json
import boto3
from datetime import datetime
from typing import Dict, Any, List, Generator

dynamodb = boto3.resource('dynamodb')
facts_table = dynamodb.Table('ParsePilot-Facts')

# Field synonyms for chat intent mapping
FIELD_SYNONYMS = {
    "employee_name": ["employee name", "employee", "name", "employee full name"],
    "employer_name": ["employer", "company", "employer name"],
    "pay_period_start": ["pay period start", "start date", "period start"],
    "pay_period_end": ["pay period end", "end date", "period end"],
    "pay_date": ["pay date", "check date", "paycheck date"],
    "gross_pay_current": ["gross pay", "gross this period", "gross current"],
    "gross_pay_ytd": ["gross ytd", "total gross ytd"],
    "net_pay_current": ["net pay", "take-home", "net this period"],
    "net_pay_ytd": ["net ytd", "take-home ytd"],
    "box1_wages": ["wages", "box 1", "wages tips compensation"],
    "box2_fed_tax": ["federal tax", "box 2", "federal income tax"],
    "box3_ss_wages": ["social security wages", "box 3", "ss wages"],
    "box4_ss_tax": ["social security tax", "box 4", "ss tax"],
    "box5_medicare_wages": ["medicare wages", "box 5"],
    "box6_medicare_tax": ["medicare tax", "box 6"]
}

def publish_facts(user_id: str, doc_id: str, parsed_data: Dict[str, Any]):
    """Flatten parsed document into queryable facts"""
    doc_type = parsed_data.get('docType', 'UNKNOWN')
    fields = parsed_data.get('fields', {})
    
    facts = []
    timestamp = int(datetime.now().timestamp() * 1000)
    
    # Core fields
    for field_key, field_data in fields.items():
        if not field_data:
            continue
            
        value = field_data.get('value') if isinstance(field_data, dict) else field_data
        if not value or str(value).strip() == "":
            continue
            
        fact = {
            'PK': user_id,
            'SK': f"{doc_id}#{field_key}#{timestamp}",
            'doc_id': doc_id,
            'doc_type': doc_type,
            'field_key': field_key,
            'created_at': timestamp
        }
        
        # Store value by type
        if isinstance(value, (int, float)):
            fact['value_num'] = float(value)
        else:
            fact['value_str'] = str(value)
            
        # Store confidence and bbox if available
        if isinstance(field_data, dict):
            fact['confidence'] = field_data.get('confidence', 0.9)
            if 'bbox' in field_data:
                fact['bbox'] = json.dumps(field_data['bbox'])
            if 'page' in field_data:
                fact['page'] = field_data['page']
                
        facts.append(fact)
    
    # Line items (earnings/deductions)
    for category in ['earnings', 'deductions']:
        items = parsed_data.get('line_items', {}).get(category, [])
        for item in items:
            if 'type' in item and 'amount_current' in item:
                fact = {
                    'PK': user_id,
                    'SK': f"{doc_id}#{category}:{item['type']}:amount_current#{timestamp}",
                    'doc_id': doc_id,
                    'doc_type': doc_type,
                    'field_key': f"{category}:{item['type']}:amount_current",
                    'value_num': float(item['amount_current']),
                    'confidence': item.get('confidence', 0.9),
                    'created_at': timestamp
                }
                facts.append(fact)
    
    # Batch write facts
    if facts:
        with facts_table.batch_writer() as batch:
            for fact in facts:
                batch.put_item(Item=fact)
    
    return len(facts)

def resolve_field_key(prompt: str) -> str:
    """Map user prompt to field key using synonyms"""
    prompt_lower = prompt.lower()
    for field_key, synonyms in FIELD_SYNONYMS.items():
        if any(syn in prompt_lower for syn in synonyms):
            return field_key
    return None

def query_facts(user_id: str, field_key: str = None, limit: int = 5) -> List[Dict]:
    """Query facts for user, optionally filtered by field"""
    if field_key:
        # Query specific field
        response = facts_table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk)',
            ExpressionAttributeValues={
                ':pk': user_id,
                ':sk': f"#{field_key}#"
            },
            ScanIndexForward=False,
            Limit=limit
        )
    else:
        # Query all facts for user
        response = facts_table.query(
            KeyConditionExpression='PK = :pk',
            ExpressionAttributeValues={':pk': user_id},
            ScanIndexForward=False,
            Limit=limit
        )
    
    return response.get('Items', [])

def get_facts_count(user_id: str) -> Dict[str, int]:
    """Get document and facts count for user"""
    response = facts_table.query(
        KeyConditionExpression='PK = :pk',
        ExpressionAttributeValues={':pk': user_id},
        Select='COUNT'
    )
    
    facts_count = response['Count']
    
    # Get unique document count
    doc_response = facts_table.query(
        KeyConditionExpression='PK = :pk',
        ExpressionAttributeValues={':pk': user_id},
        ProjectionExpression='doc_id'
    )
    
    unique_docs = len(set(item['doc_id'] for item in doc_response.get('Items', [])))
    
    return {
        'processed_docs': unique_docs,
        'facts_count': facts_count
    }