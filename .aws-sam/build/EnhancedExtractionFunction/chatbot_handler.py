"""
Chatbot Handler
Handles Q&A requests for tax document assistance
"""
import json
import logging
from services.chatbot_service import ChatbotService

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Handle chatbot Q&A requests"""
    
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': ''
            }
        
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        question = body.get('question', '').strip()
        context = body.get('context', {})
        
        if not question:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing question',
                    'message': 'Please provide a question to ask the chatbot'
                })
            }
        
        # Process with chatbot service
        chatbot = ChatbotService()
        response = chatbot.chat(question, context)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({
                'success': True,
                'question': question,
                'response': response,
                'quick_answers': chatbot.get_quick_answers()
            })
        }
        
    except Exception as e:
        logger.error(f"Chatbot handler error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Chatbot service failed',
                'message': str(e)
            })
        }