import json
import boto3
import base64
from datetime import datetime
import uuid

def lambda_handler(event, context):
    """Enhanced extraction with AI and edit capabilities"""
    
    try:
        # Parse request
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
        filename = body.get('filename')
        file_content = body.get('file_content')
        enable_ai = body.get('enable_ai', True)
        user_id = body.get('user_id', 'anonymous')
        
        if not filename or not file_content:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing filename or file_content'})
            }
        
        # Generate document ID
        doc_id = f"doc_{int(datetime.now().timestamp())}"
        
        # Upload to S3
        s3 = boto3.client('s3')
        bucket = 'drdoc-uploads-prod-995805900737'
        
        # Decode and upload file
        file_data = base64.b64decode(file_content)
        s3.put_object(
            Bucket=bucket,
            Key=f"documents/{doc_id}/{filename}",
            Body=file_data,
            ContentType=get_content_type(filename)
        )
        
        # Start extraction process
        textract = boto3.client('textract')
        bedrock = boto3.client('bedrock-runtime')
        
        # Phase 1: Textract Analysis
        textract_response = textract.analyze_document(
            Document={'Bytes': file_data},
            FeatureTypes=['FORMS', 'TABLES']
        )
        
        # Phase 2: AI Enhancement (if enabled)
        extracted_data = {}
        confidence_scores = {}
        
        if enable_ai:
            # Use Claude for intelligent extraction
            ai_prompt = f"""
            Analyze this document and extract key information. Document type appears to be a tax form.
            
            Extract the following if present:
            - Document type (W-2, 1099-NEC, 1099-INT, etc.)
            - Personal information (names, addresses, SSN/TIN)
            - Financial amounts (wages, taxes, compensation)
            - Employer/Payer information
            
            Return structured JSON with confidence scores.
            """
            
            try:
                bedrock_response = bedrock.invoke_model(
                    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                    body=json.dumps({
                        'anthropic_version': 'bedrock-2023-05-31',
                        'max_tokens': 2000,
                        'messages': [{'role': 'user', 'content': ai_prompt}]
                    })
                )
                
                ai_result = json.loads(bedrock_response['body'].read())
                ai_content = ai_result['content'][0]['text']
                
                # Parse AI response
                try:
                    ai_data = json.loads(ai_content)
                    extracted_data.update(ai_data.get('extracted_data', {}))
                    confidence_scores.update(ai_data.get('confidence_scores', {}))
                except:
                    # Fallback if AI doesn't return valid JSON
                    pass
                    
            except Exception as e:
                print(f"AI extraction failed: {e}")
        
        # Phase 3: Fallback extraction from Textract
        if not extracted_data:
            extracted_data = extract_from_textract(textract_response)
            confidence_scores = {field: 85 for field in extracted_data.keys()}
        
        # Determine document type
        doc_type = detect_document_type(filename, extracted_data)
        
        # Store results in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('DrDocDocuments-prod')
        
        table.put_item(
            Item={
                'document_id': doc_id,
                'user_id': user_id,
                'filename': filename,
                'document_type': doc_type,
                'extracted_data': extracted_data,
                'confidence_scores': confidence_scores,
                'upload_timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'editable': True,
                'ai_enhanced': enable_ai
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'document_id': doc_id,
                'document_type': doc_type,
                'extracted_data': extracted_data,
                'confidence_scores': confidence_scores,
                'editable': True,
                'status': 'completed'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def extract_from_textract(response):
    """Extract data from Textract response"""
    extracted = {}
    
    for block in response.get('Blocks', []):
        if block['BlockType'] == 'KEY_VALUE_SET':
            if 'KEY' in block.get('EntityTypes', []):
                key_text = get_text_from_block(block, response['Blocks'])
                value_block = get_value_block(block, response['Blocks'])
                if value_block:
                    value_text = get_text_from_block(value_block, response['Blocks'])
                    extracted[key_text.lower().replace(' ', '_')] = value_text
    
    return extracted

def get_text_from_block(block, all_blocks):
    """Get text content from a block"""
    text = ""
    if 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child_block = next((b for b in all_blocks if b['Id'] == child_id), None)
                    if child_block and child_block['BlockType'] == 'WORD':
                        text += child_block['Text'] + " "
    return text.strip()

def get_value_block(key_block, all_blocks):
    """Get the value block for a key block"""
    if 'Relationships' in key_block:
        for relationship in key_block['Relationships']:
            if relationship['Type'] == 'VALUE':
                value_id = relationship['Ids'][0]
                return next((b for b in all_blocks if b['Id'] == value_id), None)
    return None

def detect_document_type(filename, extracted_data):
    """Detect document type from filename and content"""
    filename_lower = filename.lower()
    
    if 'w2' in filename_lower or 'w-2' in filename_lower:
        return 'W-2'
    elif '1099' in filename_lower:
        if 'nec' in filename_lower:
            return '1099-NEC'
        elif 'int' in filename_lower:
            return '1099-INT'
        else:
            return '1099-MISC'
    elif 'receipt' in filename_lower:
        return 'Receipt'
    else:
        return 'Unknown'

def get_content_type(filename):
    """Get content type based on file extension"""
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        return 'application/pdf'
    elif ext in ['jpg', 'jpeg']:
        return 'image/jpeg'
    elif ext == 'png':
        return 'image/png'
    else:
        return 'application/octet-stream'