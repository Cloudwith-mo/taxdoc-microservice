import json
import os
import boto3
import time

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,PATCH,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('META_TABLE', 'DrDocDocuments-prod'))
        
        if event.get('httpMethod') == 'GET':
            return handle_get(event, table, headers)
        elif event.get('httpMethod') == 'PATCH':
            return handle_patch(event, table, headers)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": str(e)})
        }

def handle_get(event, table, headers):
    qs = event.get("queryStringParameters") or {}
    user = (qs.get("userId") or "ANON").strip()
    doc_id = qs["docId"]
    
    response = table.get_item(Key={"pk": f"USER#{user}", "sk": f"DOC#{doc_id}"})
    item = response.get("Item")
    
    if not item:
        return {'statusCode': 404, 'headers': headers, 'body': json.dumps({"error": "not found"})}
    
    # Compute final fields = fields overlaid by overrides
    fields = item.get("fields") or {}
    overrides = item.get("overrides") or {}
    final_fields = {**fields, **overrides}
    
    item["finalFields"] = final_fields
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(item, default=str)
    }

def handle_patch(event, table, headers):
    body = json.loads(event.get("body") or "{}")
    user = (body.get("userId") or "ANON").strip()
    doc_id = body["docId"]
    edits = body.get("edits") or {}
    remove_keys = body.get("removeKeys") or []
    
    # Fetch current document
    response = table.get_item(Key={"pk": f"USER#{user}", "sk": f"DOC#{doc_id}"})
    item = response.get("Item") or {}
    
    overrides = item.get("overrides") or {}
    
    # Apply edits
    for k, v in edits.items():
        overrides[k] = {"value": v, "confidence": 1.0, "source": "human"}
    
    # Remove keys
    for k in remove_keys:
        overrides.pop(k, None)
    
    # Audit trail
    history = item.get("editHistory") or []
    history.append({
        "ts": int(time.time()),
        "edits": edits,
        "remove": remove_keys
    })
    
    # Update document
    table.update_item(
        Key={"pk": f"USER#{user}", "sk": f"DOC#{doc_id}"},
        UpdateExpression="SET overrides = :o, editHistory = :h, lastEditedAt = :t, lastEditedBy = :u",
        ExpressionAttributeValues={
            ":o": overrides,
            ":h": history,
            ":t": int(time.time()),
            ":u": user
        }
    )
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({"ok": True})
    }