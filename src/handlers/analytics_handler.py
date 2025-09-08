import json
import boto3
from datetime import datetime, timedelta

ddb = boto3.resource('dynamodb')
table = ddb.Table('DrDocDocuments-prod')

def lambda_handler(event, context):
    try:
        # Get analytics from DynamoDB
        response = table.scan()
        items = response.get('Items', [])
        
        total_docs = len(items)
        processed_docs = len([i for i in items if i.get('docType') != 'Unknown'])
        failed_docs = total_docs - processed_docs
        
        # Calculate confidence average
        confidences = [float(item.get('docTypeConfidence', 0)) for item in items if 'docTypeConfidence' in item]
        avg_confidence = round(sum(confidences) / len(confidences) * 100) if confidences else 0
        
        # Document type distribution
        doc_types = {}
        error_types = {'OCR_FAILED': 0, 'CLASSIFICATION_FAILED': 0, 'PROCESSING_ERROR': 0}
        
        for item in items:
            doc_type = item.get('docType', 'Unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            # Count error types
            if doc_type == 'Unknown':
                error_types['CLASSIFICATION_FAILED'] += 1
        
        # Success rate
        success_rate = round((processed_docs / total_docs * 100)) if total_docs > 0 else 0
        
        # Recent activity (last 7 uploads)
        recent_items = sorted(items, key=lambda x: x.get('ts', ''), reverse=True)[:7]
        recent_activity = []
        for item in recent_items:
            recent_activity.append({
                'filename': item.get('s3', {}).get('key', '').split('/')[-1],
                'type': item.get('docType', 'Unknown'),
                'status': 'success' if item.get('docType') != 'Unknown' else 'failed',
                'timestamp': item.get('ts', ''),
                'confidence': float(item.get('docTypeConfidence', 0))
            })
        
        # Storage calculation (estimate)
        storage_used = total_docs * 150000  # Estimate 150KB per doc
        
        # Credits (mock for now)
        credits_remaining = max(0, 1000 - total_docs)
        credits_consumed = total_docs
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'total_documents': total_docs,
                'processed_documents': processed_docs,
                'failed_documents': failed_docs,
                'success_rate': success_rate,
                'avg_confidence': avg_confidence,
                'avg_processing_time_p50': 2.8,
                'avg_processing_time_p95': 5.2,
                'manual_edits_count': 0,
                'storage_used_bytes': storage_used,
                'credits_remaining': credits_remaining,
                'credits_consumed': credits_consumed,
                'document_types': doc_types,
                'error_types': error_types,
                'recent_activity': recent_activity
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }