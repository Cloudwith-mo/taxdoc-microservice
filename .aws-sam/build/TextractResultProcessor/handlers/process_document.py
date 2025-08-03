import json
import boto3
from typing import Dict, Any
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.textract_service import TextractService
from services.classifier_service import ClassifierService
from services.extractor_service import ExtractorService
from services.storage_service import StorageService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for document processing"""
    
    print(f"Processing event: {json.dumps(event)}")
    
    try:
        # Parse S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        print(f"Processing document: s3://{bucket}/{key}")
        
        # Initialize services
        textract = TextractService()
        classifier = ClassifierService()
        extractor = ExtractorService()
        storage = StorageService()
        
        # Step 1: Determine if async processing needed
        if key.lower().endswith('.pdf') or key.lower().endswith('.tiff'):
            print(f"Starting async Textract job for {key}")
            job_id = textract.start_async_analysis(bucket, key)
            
            # Save initial record with Processing status
            result = {
                "DocumentID": key.split('/')[-1],
                "DocumentType": "Processing",
                "UploadDate": record['eventTime'],
                "S3Location": f"s3://{bucket}/{key}",
                "ProcessingStatus": "Processing",
                "JobId": job_id
            }
            storage.save_document_metadata(result)
            print(f"Started async job {job_id}, saved initial record")
            
            return {
                'statusCode': 202,
                'body': json.dumps({"message": "Processing started", "DocumentID": result["DocumentID"]})
            }
        else:
            # Synchronous processing for small files
            print("Using synchronous Textract for small document...")
            textract_response = textract.analyze_document(bucket, key)
            print(f"Textract response received with {len(textract_response.get('Blocks', []))} blocks")
        
            # Step 2: Classify document type
            print("Classifying document type...")
            doc_type = classifier.classify_document(textract_response)
            print(f"Document classified as: {doc_type}")
            
            # Step 3: Extract key fields based on document type
            print("Extracting key fields...")
            extracted_data = extractor.extract_fields(textract_response, doc_type)
            print(f"Extracted data: {json.dumps(extracted_data)}")
            
            # Step 4: Structure the output
            result = {
                "DocumentID": key.split('/')[-1],
                "DocumentType": doc_type,
                "UploadDate": record['eventTime'],
                "S3Location": f"s3://{bucket}/{key}",
                "Data": extracted_data,
                "ProcessingStatus": "Completed"
            }
            
            # Step 5: Store results
            print("Storing results to DynamoDB...")
            storage.save_document_metadata(result)
            print("Processing completed successfully")
        
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        error_result = {
            "DocumentID": key.split('/')[-1] if 'key' in locals() else "unknown",
            "ProcessingStatus": "Failed",
            "Error": str(e)
        }
        
        # Try to store error result
        try:
            storage = StorageService()
            storage.save_document_metadata(error_result)
        except:
            print("Failed to store error result")
        
        return {
            'statusCode': 500,
            'body': json.dumps(error_result)
        }