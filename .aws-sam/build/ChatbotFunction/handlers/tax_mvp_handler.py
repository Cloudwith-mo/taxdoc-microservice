"""
TaxDoc V1 MVP Handler
Simple tax document extraction for W-2 and 1099 forms
"""
import json
import boto3
import base64
import os
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
textract = boto3.client('textract')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Import our services
import sys
sys.path.append('/opt/python')
sys.path.append('/var/task')

from services.tax_classifier import TaxClassifier
from services.enhanced_tax_extractor import EnhancedTaxExtractor
from services.ai_insights_service import AIInsightsService
from services.sentiment_service import SentimentService
from services.chatbot_service import ChatbotService

def lambda_handler(event, context):
    """
    Main handler for tax document processing
    Expects: POST /process-document with JSON body containing filename and base64 content
    """
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
                },
                'body': ''
            }
        
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
            
        filename = body.get('filename')
        file_content = body.get('file_content')
        
        if not filename or not file_content:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Missing filename or file_content',
                    'message': 'Please provide both filename and base64-encoded file content'
                })
            }
        
        # Decode file content
        try:
            file_bytes = base64.b64decode(file_content)
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Invalid base64 content',
                    'message': str(e)
                })
            }
        
        # Process document
        result = process_tax_document(file_bytes, filename)
        
        # Store in DynamoDB for analytics
        store_document_metadata(result, filename)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Processing failed',
                'message': str(e)
            })
        }

def store_document_metadata(result: Dict[str, Any], filename: str):
    """Store document processing metadata in DynamoDB for analytics"""
    try:
        table_name = os.environ.get('DOCUMENTS_TABLE', 'DrDocDocuments-mvp')
        table = dynamodb.Table(table_name)
        
        import uuid
        from datetime import datetime, timedelta
        
        document_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        ttl = int((datetime.now() + timedelta(days=30)).timestamp())
        
        # Convert floats to Decimal for DynamoDB
        def convert_floats(obj):
            if isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats(v) for v in obj]
            elif isinstance(obj, float):
                from decimal import Decimal
                return Decimal(str(obj))
            return obj
        
        item = {
            'document_id': document_id,
            'filename': filename,
            'timestamp': timestamp,
            'ttl': ttl,
            'status': 'completed' if result.get('success') else 'failed',
            'document_type': result.get('document_type', 'Unknown'),
            'extracted_data': convert_floats(result.get('extracted_data', {})),
            'processing_info': convert_floats(result.get('processing_info', {}))
        }
        
        table.put_item(Item=item)
        logger.info(f"Stored document metadata: {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to store metadata: {str(e)}")
        # Don't fail the main request if metadata storage fails

def process_tax_document(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process tax document through extraction pipeline"""
    
    # Step 1: OCR with Textract
    logger.info(f"Processing document: {filename}")
    
    try:
        textract_response = textract.analyze_document(
            Document={'Bytes': file_bytes},
            FeatureTypes=['FORMS', 'TABLES']
        )
    except Exception as e:
        logger.error(f"Textract failed: {str(e)}")
        raise Exception(f"OCR processing failed: {str(e)}")
    
    # Step 2: Classify document type
    classifier = TaxClassifier()
    doc_type = classifier.classify_tax_document(textract_response)
    
    if doc_type == "Unsupported":
        return {
            'success': False,
            'error': 'Unsupported document type',
            'message': 'Only W-2 and 1099 tax forms are supported in this version',
            'filename': filename
        }
    
    # Step 3: Extract data using enhanced three-layer pipeline
    extractor = EnhancedTaxExtractor()
    extracted_data = extractor.extract_with_three_layers(textract_response, doc_type)
    
    # Step 4: Generate AI insights
    insights_service = AIInsightsService()
    ai_insights = insights_service.generate_insights(extracted_data, doc_type)
    
    # Step 5: Generate sentiment analysis
    sentiment_service = SentimentService()
    sentiment_analysis = sentiment_service.analyze_document_sentiment(extracted_data, doc_type)
    
    # Step 6: Generate chatbot summary
    chatbot_service = ChatbotService()
    document_summary = chatbot_service.get_document_summary(extracted_data, doc_type)
    
    # Step 7: Format response with all enhancements
    return {
        'success': True,
        'filename': filename,
        'document_type': doc_type,
        'extracted_data': extracted_data,
        'ai_insights': ai_insights,
        'sentiment_analysis': sentiment_analysis,
        'document_summary': document_summary,
        'processing_info': {
            'ocr_blocks': len(textract_response.get('Blocks', [])),
            'extraction_method': 'three_layer_pipeline',
            'layers_used': extracted_data.get('layers_used', []),
            'total_fields': extracted_data.get('total_fields_extracted', 0),
            'insights_generated': True,
            'sentiment_analyzed': True,
            'chatbot_enabled': True,
            'version': 'enhanced-mvp-v2'
        }
    }

def handle_options(event, context):
    """Handle CORS preflight requests"""
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
        },
        'body': ''
    }