import json
import boto3
from typing import Dict, Any
import sys
import os
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.textract_service import TextractService
from services.enhanced_classifier import EnhancedClassifier
from services.multi_form_extractor import MultiFormExtractor
from services.storage_service import StorageService
from services.comprehend_service import ComprehendService
from services.bedrock_service import BedrockService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle SNS notifications from Textract async jobs"""
    
    print(f"Received SNS event: {json.dumps(event)}")
    
    try:
        for record in event['Records']:
            message = json.loads(record['Sns']['Message'])
            
            job_id = message['JobId']
            status = message['Status']
            bucket = message['DocumentLocation']['S3Bucket']
            key = message['DocumentLocation']['S3ObjectName']
            doc_id = key.split('/')[-1]
            
            print(f"Processing Textract job {job_id} with status {status} for {doc_id}")
            
            # Initialize services
            textract = TextractService()
            classifier = EnhancedClassifier()
            extractor = MultiFormExtractor()
            storage = StorageService()
            comprehend = ComprehendService()
            bedrock = BedrockService()
            
            if status == "SUCCEEDED":
                # Determine job type from JobTag or API used
                job_type = 'expense' if 'Expense' in message.get('JobTag', '') else 'analysis'
                
                # Retrieve async results
                print(f"Retrieving {job_type} results for job {job_id}")
                textract_response = textract.get_async_results(job_id, job_type)
                
                # Get text for classification
                text = textract.get_text_from_response(textract_response)
                print(f"Extracted {len(text)} characters of text")
                
                # Classify document type with enhanced classifier
                print("Classifying document type...")
                doc_type, classification_confidence = classifier.classify_document(textract_response)
                print(f"Document classified as: {doc_type} (confidence: {classification_confidence:.2f})")
                
                # Optional: Use ML classification as additional validation
                ml_prediction, ml_confidence = None, 0.0
                try:
                    ml_prediction, ml_confidence = comprehend.classify_document(text)
                    if ml_prediction and ml_prediction != doc_type:
                        print(f"ML classification differs: {ml_prediction} (confidence: {ml_confidence:.3f})")
except Exception as e:
                    print(f"ML classification failed: {e}")
                
                # Extract key fields using multi-form extractor
                print("Extracting key fields using 3-layer approach...")
                
                # Get document bytes for AI processing
                document_bytes = None
                try:
                    s3_client = boto3.client('s3')
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    document_bytes = response['Body'].read()
                    print(f"Retrieved document bytes for processing: {len(document_bytes)} bytes")
                except Exception as e:
                    print(f"Failed to retrieve document bytes: {e}")
                
                extracted_data = extractor.extract_document_fields(
                    textract_response=textract_response,
                    document_type=doc_type,
                    document_bytes=document_bytes,
                    s3_bucket=bucket,
                    s3_key=key
                )
                
                # Add AI-powered fuzzy fields as fallback
                try:
                    fuzzy_fields = bedrock.extract_fuzzy_fields(text, doc_type)
                    if fuzzy_fields:
                        for field, value in fuzzy_fields.items():
                            if field not in extracted_data or not extracted_data[field]:
                                extracted_data[field] = value
                        print(f"Added fuzzy fields: {fuzzy_fields}")
                except Exception as e:
                    print(f"Fuzzy field extraction failed: {e}")
                
                print(f"Final extracted data: {json.dumps(extracted_data, default=str)}")
                
                # Generate summary if enabled
                summary = bedrock.generate_summary(text, doc_type)
                if summary:
                    print(f"Generated summary: {summary[:100]}...")
                
                # Structure final result
                result = {
                    "DocumentID": doc_id,
                    "DocumentType": doc_type,
                    "ClassificationConfidence": classification_confidence,
                    "UploadDate": message.get('Timestamp', datetime.utcnow().isoformat()),
                    "S3Location": f"s3://{bucket}/{key}",
                    "Data": extracted_data,
                    "ProcessingStatus": "Completed",
                    "JobId": job_id,
                    "ExtractionMetadata": extracted_data.get('_extraction_metadata', {}),
                    "MLClassificationUsed": bool(ml_prediction),
                    "MLConfidence": ml_confidence
                }
                
                # Add summary if generated
                if summary:
                    result["Summary"] = summary
                
                # Store results
                print("Storing final results to DynamoDB...")
                storage.save_document_metadata(result)
                print(f"Successfully processed document {doc_id}")
                
            elif status == "FAILED":
                # Handle failed Textract job
                error_info = message.get('StatusMessage', 'Textract job failed')
                print(f"Textract job {job_id} failed: {error_info}")
                
                # Update DynamoDB with failure status
                result = {
                    "DocumentID": doc_id,
                    "ProcessingStatus": "Failed",
                    "Error": error_info,
                    "JobId": job_id
                }
                
                storage.save_document_metadata(result)
                print(f"Stored failure status for {doc_id}")
            
            else:
                print(f"Unknown status {status} for job {job_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'SNS event processed successfully'})
        }
        
    except Exception as e:
        print(f"Error processing SNS event: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }