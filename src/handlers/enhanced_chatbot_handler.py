import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """Enhanced chatbot with sentiment analysis"""
    
    try:
        # Parse the request
        body = json.loads(event.get('body', '{}'))
        message = body.get('message', '')
        document_data = body.get('document_data', {})
        user_sentiment = body.get('user_sentiment', 'neutral')
        response_tone = body.get('response_tone', 'neutral')
        user_tier = body.get('user_tier', 'free')
        
        if not message:
            raise Exception('Message is required')
        
        # Analyze sentiment using Amazon Comprehend
        sentiment_data = analyze_sentiment(message) if user_tier == 'premium' else None
        
        # Generate AI response with sentiment awareness
        ai_response = generate_ai_response(
            message, 
            document_data, 
            user_sentiment, 
            response_tone,
            user_tier
        )
        
        # Store chat history if user is authenticated
        auth_header = event.get('headers', {}).get('Authorization', '')
        if auth_header.startswith('Bearer '):
            user_id = extract_user_id(auth_header)
            store_chat_message(user_id, message, ai_response, sentiment_data)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'response': ai_response,
                'detected_sentiment': sentiment_data.get('Sentiment') if sentiment_data else None,
                'sentiment_confidence': sentiment_data.get('SentimentScore', {}).get('Mixed', 0) if sentiment_data else None,
                'user_tier': user_tier
            })
        }
        
    except Exception as e:
        print(f"Error in enhanced_chatbot_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': str(e)})
        }

def analyze_sentiment(text):
    """Analyze sentiment using Amazon Comprehend"""
    
    try:
        comprehend = boto3.client('comprehend')
        
        response = comprehend.detect_sentiment(
            Text=text,
            LanguageCode='en'
        )
        
        return response
        
    except Exception as e:
        print(f"Error analyzing sentiment: {str(e)}")
        return None

def generate_ai_response(message, document_data, user_sentiment, response_tone, user_tier):
    """Generate AI response with sentiment awareness"""
    
    try:
        bedrock = boto3.client('bedrock-runtime')
        
        # Adjust prompt based on sentiment and tone
        system_prompt = get_system_prompt(response_tone, user_tier)
        
        # Create context from document data
        context = create_document_context(document_data)
        
        # Build the prompt
        prompt = f"""
{system_prompt}

Document Context:
{context}

User Question (sentiment: {user_sentiment}): {message}

Please provide a helpful response that addresses the user's question about their document data.
"""

        # Call Claude via Bedrock
        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1000,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        ai_response = response_body['content'][0]['text']
        
        return ai_response
        
    except Exception as e:
        print(f"Error generating AI response: {str(e)}")
        return get_fallback_response(user_sentiment)

def get_system_prompt(response_tone, user_tier):
    """Get system prompt based on response tone and user tier"""
    
    base_prompt = "You are a helpful AI assistant that helps users understand their tax and financial documents."
    
    if response_tone == 'empathetic':
        return f"{base_prompt} The user seems frustrated or confused, so please be extra patient, understanding, and provide clear, step-by-step explanations. Use reassuring language and acknowledge their concerns."
    elif response_tone == 'enthusiastic':
        return f"{base_prompt} The user seems positive and engaged, so you can be more energetic and detailed in your responses. Feel free to provide additional insights and tips."
    else:
        return f"{base_prompt} Provide clear, concise, and helpful responses."

def create_document_context(document_data):
    """Create context string from document data"""
    
    if not document_data or not document_data.get('Data'):
        return "No document data available."
    
    context_parts = []
    data = document_data.get('Data', {})
    doc_type = document_data.get('DocumentType', 'Unknown')
    
    context_parts.append(f"Document Type: {doc_type}")
    
    for key, value in data.items():
        formatted_key = key.replace('_', ' ').title()
        context_parts.append(f"{formatted_key}: {value}")
    
    return "\n".join(context_parts)

def get_fallback_response(user_sentiment):
    """Get fallback response based on user sentiment"""
    
    if user_sentiment == 'negative':
        return "I'm sorry you're having trouble. I'm here to help you understand your document. Could you please rephrase your question or let me know what specific information you're looking for?"
    elif user_sentiment == 'positive':
        return "I'm glad you're engaged! I'd be happy to help you with your document. What would you like to know more about?"
    else:
        return "I'm here to help you understand your document. What specific information are you looking for?"

def extract_user_id(auth_header):
    """Extract user ID from JWT token (simplified)"""
    
    # In production, you'd properly decode and validate the JWT
    token = auth_header.split('Bearer ')[1]
    return f"user_{token[:10]}"

def store_chat_message(user_id, message, response, sentiment_data):
    """Store chat message in DynamoDB"""
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('CHAT_HISTORY_TABLE', 'DrDocChatHistory-prod'))
        
        table.put_item(
            Item={
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'message': message,
                'response': response,
                'sentiment': sentiment_data.get('Sentiment') if sentiment_data else None,
                'sentiment_scores': sentiment_data.get('SentimentScore') if sentiment_data else None
            }
        )
        
    except Exception as e:
        print(f"Error storing chat message: {str(e)}")
        # Don't fail the request if chat storage fails