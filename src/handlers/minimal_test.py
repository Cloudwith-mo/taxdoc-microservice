import json

def lambda_handler(event, context):
    print(f"Event received: {json.dumps(event, default=str)}")
    
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Content-Type": "application/json"
    }
    
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": cors_headers, "body": ""}
    
    return {
        "statusCode": 200, 
        "headers": cors_headers, 
        "body": json.dumps({"message": "Hello from Lambda", "event_keys": list(event.keys())})
    }