import json
import base64
import boto3
from datetime import datetime
from typing import Dict, Any
from services.tax_form_processor import TaxFormProcessor
from services.ai_insights_service import AIInsightsService
from services.chatbot_service import ChatbotService
from services.analytics_service import AnalyticsService

def lambda_handler(event, context):
    """Enhanced API handler with AI insights and analytics"""
    
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        action = event.get('pathParameters', {}).get('action', 'process')
        
        if action == 'process':
            return handle_document_processing(body)
        elif action == 'insights':
            return handle_insights_request(body)
        elif action == 'chat':
            return handle_chat_request(body)
        elif action == 'analytics':
            return handle_analytics_request(body)
        else:
            return error_response('Invalid action', 400)
            
    except Exception as e:
        return error_response(str(e), 500)

def handle_document_processing(body: Dict[str, Any]) -> Dict[str, Any]:
    """Process document with enhanced insights"""
    
    filename = body.get('filename', '')
    file_content = body.get('file_content', '')
    include_insights = body.get('include_insights', True)
    
    if not file_content:
        return error_response('No file content provided', 400)
    
    start_time = datetime.now()
    
    # Decode and process document
    document_bytes = base64.b64decode(file_content)
    processor = TaxFormProcessor()
    result = processor.process_tax_document(document_bytes, filename)
    
    processing_time = (datetime.now() - start_time).total_seconds()
    
    if result.get('success') and include_insights:
        # Add AI insights
        insights_service = AIInsightsService()
        
        # Extract document text for sentiment analysis
        textract = boto3.client('textract')
        textract_response = textract.detect_document_text(Document={'Bytes': document_bytes})
        document_text = extract_text_from_textract(textract_response)
        
        # Generate insights
        insights = insights_service.generate_insights(result['extracted_fields'], result['form_type'])
        sentiment = insights_service.analyze_sentiment(document_text, result['form_type'])
        action_items = insights_service.extract_action_items(document_text, result['form_type'])
        
        result.update({
            'ai_insights': insights,
            'sentiment_analysis': sentiment,
            'action_items': action_items,
            'processing_time': processing_time
        })
    
    # Track analytics
    analytics = AnalyticsService()
    analytics.track_processing_event({
        'document_type': result.get('form_type', 'Unknown'),
        'status': 'Success' if result.get('success') else 'Failed',
        'processing_time': processing_time,
        'confidence': result.get('classification_confidence', 0)
    })
    
    return success_response(result)

def handle_insights_request(body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle insights-only requests"""
    
    document_data = body.get('document_data', {})
    document_text = body.get('document_text', '')
    document_type = body.get('document_type', 'Unknown')
    
    insights_service = AIInsightsService()
    
    insights = insights_service.generate_insights(document_data, document_type)
    sentiment = insights_service.analyze_sentiment(document_text, document_type)
    action_items = insights_service.extract_action_items(document_text, document_type)
    
    return success_response({
        'insights': insights,
        'sentiment': sentiment,
        'action_items': action_items
    })

def handle_chat_request(body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle chatbot Q&A requests"""
    
    question = body.get('question', '')
    document_data = body.get('document_data', {})
    document_text = body.get('document_text', '')
    conversation_id = body.get('conversation_id')
    
    if not question:
        return error_response('No question provided', 400)
    
    chatbot = ChatbotService()
    
    if body.get('cross_document'):
        # Cross-document analysis
        documents = body.get('documents', [])
        answer = chatbot.get_cross_document_insights(question, documents)
    else:
        # Single document Q&A
        answer = chatbot.ask_question(question, document_data, document_text)
    
    return success_response({
        'question': question,
        'answer': answer,
        'conversation_id': conversation_id,
        'timestamp': datetime.now().isoformat()
    })

def handle_analytics_request(body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle analytics dashboard requests"""
    
    analytics_type = body.get('type', 'processing')
    days = body.get('days', 30)
    
    analytics = AnalyticsService()
    
    if analytics_type == 'processing':
        data = analytics.get_processing_insights(days)
    elif analytics_type == 'team':
        data = analytics.get_team_productivity_metrics()
    elif analytics_type == 'cost':
        data = analytics.get_cost_optimization_insights()
    else:
        return error_response('Invalid analytics type', 400)
    
    return success_response(data)

def extract_text_from_textract(textract_response: Dict[str, Any]) -> str:
    """Extract plain text from Textract response"""
    
    text_lines = []
    for block in textract_response.get('Blocks', []):
        if block['BlockType'] == 'LINE':
            text_lines.append(block.get('Text', ''))
    
    return '\n'.join(text_lines)

def success_response(data: Any) -> Dict[str, Any]:
    """Return success response"""
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(data)
    }

def error_response(message: str, status_code: int = 500) -> Dict[str, Any]:
    """Return error response"""
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }