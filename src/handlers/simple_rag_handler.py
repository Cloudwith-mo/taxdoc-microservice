import json
import boto3
import logging
import requests
from datetime import datetime

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

# Table
table = dynamodb.Table('documentgpt-docs')

def lambda_handler(event, context):
    logger.info(f"RAG request: {json.dumps(event)}")
    
    # Handle OPTIONS for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': ''
        }
    
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        question = body.get('question')
        doc_id = body.get('docId')
        
        if not question:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing question'})
            }
        
        logger.info(f"Question: {question}, DocId: {doc_id}")
        
        # If specific docId provided, search that document
        if doc_id:
            return search_specific_document(question, doc_id)
        else:
            return search_all_documents(question)
            
    except Exception as e:
        logger.error(f"RAG error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def search_specific_document(question, doc_id):
    try:
        # Get document from DynamoDB
        response = table.get_item(
            Key={
                'tenant': 'default',
                'docId': doc_id
            }
        )
        
        if 'Item' not in response:
            logger.warning(f"Document {doc_id} not found in DynamoDB")
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'answer': 'Document not found.',
                    'citations': []
                })
            }
        
        doc = response['Item']
        logger.info(f"Found document: {doc.get('docName', 'Unknown')} with status: {doc.get('status', 'Unknown')}")
        
        # Check if document is processed
        if doc.get('status') != 'completed':
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'answer': f'Document is still being processed. Status: {doc.get("status", "unknown")}',
                    'citations': []
                })
            }
        
        # Get extracted text
        extracted_text = doc.get('extractedText', '')
        if not extracted_text:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'answer': 'No text content found in document.',
                    'citations': []
                })
            }
        
        # Get OpenAI API key
        openai_key = get_parameter('/documentgpt/openai_api_key')
        
        # Generate answer using OpenAI
        answer = generate_answer(question, extracted_text, openai_key)
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'answer': answer,
                'citations': [{
                    'docId': doc_id,
                    'docName': doc.get('docName', 'Unknown'),
                    'text': extracted_text[:200] + '...' if len(extracted_text) > 200 else extracted_text
                }]
            })
        }
        
    except Exception as e:
        logger.error(f"Error searching document {doc_id}: {str(e)}")
        raise

def search_all_documents(question):
    try:
        # Scan for all completed documents
        response = table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'completed'}
        )
        
        documents = response.get('Items', [])
        logger.info(f"Found {len(documents)} completed documents")
        
        if not documents:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'answer': 'No processed documents found.',
                    'citations': []
                })
            }
        
        # Combine text from all documents
        combined_text = ""
        citations = []
        
        for doc in documents[:5]:  # Limit to first 5 docs
            text = doc.get('extractedText', '')
            if text:
                combined_text += f"\n\nFrom {doc.get('docName', 'Unknown')}:\n{text}"
                citations.append({
                    'docId': doc.get('docId'),
                    'docName': doc.get('docName', 'Unknown'),
                    'text': text[:200] + '...' if len(text) > 200 else text
                })
        
        if not combined_text:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'answer': 'No text content found in any documents.',
                    'citations': []
                })
            }
        
        # Get OpenAI API key
        openai_key = get_parameter('/documentgpt/openai_api_key')
        
        # Generate answer
        answer = generate_answer(question, combined_text, openai_key)
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'answer': answer,
                'citations': citations
            })
        }
        
    except Exception as e:
        logger.error(f"Error searching all documents: {str(e)}")
        raise

def get_parameter(param_name):
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to get parameter {param_name}: {str(e)}")
        raise

def generate_answer(question, context, openai_key):
    try:
        # Limit context size
        if len(context) > 4000:
            context = context[:4000]
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {openai_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that answers questions based on the provided document content. If the answer is not in the documents, say so clearly.'
                    },
                    {
                        'role': 'user',
                        'content': f'Based on this document content:\n\n{context}\n\nQuestion: {question}'
                    }
                ],
                'max_tokens': 500,
                'temperature': 0.1
            },
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return "Sorry, I couldn't generate an answer at this time."
        
        answer = response.json()['choices'][0]['message']['content']
        logger.info(f"Generated answer: {answer[:100]}...")
        return answer
        
    except Exception as e:
        logger.error(f"Failed to generate answer: {str(e)}")
        return "Sorry, I couldn't generate an answer due to an error."