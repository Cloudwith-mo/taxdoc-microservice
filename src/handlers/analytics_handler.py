import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

def lambda_handler(event, context):
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        user_id = event.get('queryStringParameters', {}).get('userId', 'ANON')
        period = event.get('queryStringParameters', {}).get('period', '7d')
        
        # Get analytics data
        analytics = get_user_analytics(user_id, period)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(analytics, default=decimal_default)
        }
        
    except Exception as e:
        print(f"Analytics error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def get_user_analytics(user_id, period):
    """Get comprehensive analytics for a user"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('DrDocDocuments-prod')
    
    # Calculate time ranges
    now = datetime.utcnow()
    if period == '1d':
        start_time = now - timedelta(days=1)
    elif period == '7d':
        start_time = now - timedelta(days=7)
    elif period == '30d':
        start_time = now - timedelta(days=30)
    else:
        start_time = datetime(2020, 1, 1)  # All time
    
    # Query user documents
    try:
        response = table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'USER#{user_id}'}
        )
        items = response.get('Items', [])
    except:
        items = []
    
    # Filter by time period
    filtered_items = []
    for item in items:
        try:
            item_time = datetime.fromisoformat(item.get('processedAt', '2020-01-01T00:00:00').replace('Z', '+00:00'))
            if item_time >= start_time:
                filtered_items.append(item)
        except:
            continue
    
    # Calculate metrics
    total_docs = len(filtered_items)
    processed = [d for d in filtered_items if d.get('status') == 'PROCESSED']
    failed = [d for d in filtered_items if d.get('status') == 'FAILED']
    
    # Processing latency (mock data for now)
    processing_times = [float(d.get('processingTimeMs', 9200)) / 1000 for d in processed]
    avg_latency = sum(processing_times) / len(processing_times) if processing_times else 9.2
    p95_latency = sorted(processing_times)[int(len(processing_times) * 0.95)] if processing_times else 12.5
    
    # Confidence metrics
    confidences = [float(d.get('docTypeConfidence', 0.85)) for d in processed]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.85
    
    # Document type distribution
    doc_types = {}
    for doc in filtered_items:
        doc_type = doc.get('docType', 'Unknown')
        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
    
    # Time-based metrics
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    today_docs = [d for d in filtered_items if datetime.fromisoformat(d.get('processedAt', '2020-01-01T00:00:00').replace('Z', '+00:00')) >= today]
    week_docs = [d for d in filtered_items if datetime.fromisoformat(d.get('processedAt', '2020-01-01T00:00:00').replace('Z', '+00:00')) >= week_ago]
    
    # Upload source analysis (mock data)
    upload_sources = {
        'UI': int(total_docs * 0.7),
        'API': int(total_docs * 0.2),
        'Batch': int(total_docs * 0.1)
    }
    
    # Storage usage (mock calculation)
    avg_file_size = 250  # KB
    storage_used_mb = (total_docs * avg_file_size) / 1024
    
    # Manual review rate
    needs_review = [d for d in processed if d.get('flags', {}).get('needs_review', False)]
    review_rate = (len(needs_review) / len(processed)) * 100 if processed else 0
    
    return {
        'totalDocs': total_docs,
        'processed': len(processed),
        'failed': len(failed),
        'successRate': (len(processed) / total_docs) * 100 if total_docs > 0 else 0,
        'avgConfidence': avg_confidence * 100,
        'avgLatency': round(avg_latency, 1),
        'p95Latency': round(p95_latency, 1),
        'todayDocs': len(today_docs),
        'weekDocs': len(week_docs),
        'docTypes': doc_types,
        'uploadSources': upload_sources,
        'storageUsedMb': round(storage_used_mb, 1),
        'reviewRate': round(review_rate, 1),
        'queueDepth': 0,  # Mock - would come from SQS
        'creditsRemaining': 1000,  # Mock - would come from billing system
        'recentActivity': [
            {
                'action': 'PROCESSED',
                'docType': item.get('docType', 'Unknown'),
                'filename': item.get('filename', 'Unknown'),
                'timestamp': item.get('processedAt', ''),
                'confidence': item.get('docTypeConfidence', 0)
            }
            for item in sorted(filtered_items, key=lambda x: x.get('processedAt', ''), reverse=True)[:20]
        ],
        'alerts': generate_alerts(len(processed), len(failed), avg_confidence, avg_latency, review_rate),
        'period': period,
        'generatedAt': now.isoformat()
    }

def generate_alerts(processed, failed, avg_confidence, avg_latency, review_rate):
    """Generate alerts based on metrics"""
    alerts = []
    
    total = processed + failed
    if total > 0:
        success_rate = (processed / total) * 100
        if success_rate < 95:
            alerts.append({
                'type': 'warning',
                'message': f'Success rate below 95%: {success_rate:.1f}%',
                'metric': 'success_rate',
                'value': success_rate
            })
    
    if avg_confidence < 0.8:
        alerts.append({
            'type': 'warning',
            'message': f'Average confidence below 80%: {avg_confidence*100:.1f}%',
            'metric': 'confidence',
            'value': avg_confidence * 100
        })
    
    if avg_latency > 15:
        alerts.append({
            'type': 'error',
            'message': f'Processing latency above SLA: {avg_latency:.1f}s',
            'metric': 'latency',
            'value': avg_latency
        })
    
    if review_rate > 20:
        alerts.append({
            'type': 'info',
            'message': f'High manual review rate: {review_rate:.1f}%',
            'metric': 'review_rate',
            'value': review_rate
        })
    
    return alerts

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError