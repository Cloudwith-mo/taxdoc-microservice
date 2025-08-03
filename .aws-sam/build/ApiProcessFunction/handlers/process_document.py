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
    
    try:
        # Parse S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Initialize services
        textract = TextractService()
        classifier = ClassifierService()
        extractor = ExtractorService()
        storage = StorageService()
        
        # Step 1: Extract text and form data using Textract
        textract_response = textract.analyze_document(bucket, key)
        
        # Step 2: Classify document type
        doc_type = classifier.classify_document(textract_response)
        
        # Step 3: Extract key fields based on document type
        extracted_data = extractor.extract_fields(textract_response, doc_type)
        
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
        storage.save_document_metadata(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        error_result = {
            "DocumentID": key.split('/')[-1] if 'key' in locals() else "unknown",
            "ProcessingStatus": "Failed",
            "Error": str(e)
        }
        
        return {
            'statusCode': 500,
            'body': json.dumps(error_result)
        }