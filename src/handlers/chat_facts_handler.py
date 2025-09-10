import json
import boto3
from facts_publisher import resolve_field_key, query_facts, get_facts_count

def lambda_handler(event, context):
    """Handle chat queries using facts store"""
    try:
        body = json.loads(event['body'])
        user_id = body.get('user_id', 'guest')
        prompt = body.get('message', '').strip()
        
        # Handle stats request
        if 'stats' in prompt.lower() or 'count' in prompt.lower():
            stats = get_facts_count(user_id)
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'response': f"You have {stats['processed_docs']} processed documents with {stats['facts_count']} extracted facts.",
                    'stats': stats
                })
            }
        
        # Try to resolve field from prompt
        field_key = resolve_field_key(prompt)
        
        if field_key:
            # Query specific field
            facts = query_facts(user_id, field_key, limit=3)
            if facts:
                latest = facts[0]
                value = latest.get('value_str') or latest.get('value_num')
                confidence = latest.get('confidence', 0.9)
                
                response = {
                    'response': f"{field_key.replace('_', ' ').title()}: {value} (confidence: {int(confidence*100)}%)",
                    'source': {
                        'doc_id': latest['doc_id'],
                        'field_key': field_key,
                        'confidence': confidence
                    }
                }
                
                # Add bbox if available
                if 'bbox' in latest:
                    response['source']['bbox'] = json.loads(latest['bbox'])
                if 'page' in latest:
                    response['source']['page'] = latest['page']
                    
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(response)
                }
        
        # Fallback: show recent facts
        recent_facts = query_facts(user_id, limit=5)
        if recent_facts:
            fact_list = []
            for fact in recent_facts[:3]:
                value = fact.get('value_str') or fact.get('value_num')
                fact_list.append(f"• {fact['field_key'].replace('_', ' ').title()}: {value}")
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'response': f"I found these recent facts:\n" + "\n".join(fact_list) + f"\n\nTry asking about specific fields like 'employee name' or 'net pay'."
                })
            }
        
        # No facts found
        stats = get_facts_count(user_id)
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'response': f"I don't have any processed documents for you yet. Upload a document to get started! (Current stats: {stats['processed_docs']} docs, {stats['facts_count']} facts)",
                'stats': stats
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }