import json
import os
import boto3
from boto3.dynamodb.conditions import Key

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        qs = event.get("queryStringParameters") or {}
        user = (qs.get("userId") or "ANON").strip()
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('META_TABLE', 'DrDocDocuments-prod'))
        
        response = table.query(
            KeyConditionExpression=Key("pk").eq(f"USER#{user}") & Key("sk").begins_with("DOC#"),
            Limit=200
        )
        
        items = [{
            "docId": item.get("docId"),
            "filename": item.get("filename"),
            "docType": item.get("docType"),
            "docTypeConfidence": item.get("docTypeConfidence"),
            "status": item.get("status", "PROCESSED"),
            "processedAt": item.get("processedAt"),
            "fieldsCount": len(item.get("fields", {}))
        } for item in response.get("Items", [])]
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({"items": items})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({"error": str(e), "items": []})
        }