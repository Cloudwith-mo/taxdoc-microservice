import json
import boto3
from typing import Dict, Any
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.textract_service import TextractService
from services.enhanced_classifier import EnhancedClassifier
from services.three_layer_orchestrator import ThreeLayerOrchestrator
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
        classifier = EnhancedClassifier()
        orchestrator = ThreeLayerOrchestrator()
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
            doc_type, confidence = classifier.classify_document(textract_response)
            print(f"Document classified as: {doc_type} (confidence: {confidence:.2f})")
            
            # Step 3: Extract key fields using multi-form extractor
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
            
            extracted_data = orchestrator.extract_document_fields(
                document_bytes=document_bytes,
                document_type=doc_type
            )
            print(f"Multi-form extraction completed with {len(extracted_data)} fields")
            
            # Step 4: Structure the output with frontend formatting
            formatted_data = extracted_data.get('ExtractedData', {})
            
            # Format W-2 fields for frontend compatibility
            if doc_type == "W-2":
                field_mapping = {
                    'EmployeeName': 'e Employee\'s first name and initial',
                    'EmployeeSSN': 'a Employee\'s social security number', 
                    'EmployerName': 'c Employer\'s name, address, and ZIP code',
                    'EmployerEIN': 'b Employer identification number (EIN)',
                    'Box1_Wages': '1 Wages, tips, other compensation',
                    'Box2_FederalTaxWithheld': '2 Federal income tax withheld',
                    'Box3_SocialSecurityWages': '3 Social security wages',
                    'Box4_SocialSecurityTax': '4 Social security tax withheld',
                    'Box5_MedicareWages': '5 Medicare wages and tips',
                    'Box6_MedicareTax': '6 Medicare tax withheld',
                    'TaxYear': 'Tax Year'
                }
                
                frontend_data = {}
                for internal_name, display_name in field_mapping.items():
                    if internal_name in formatted_data:
                        frontend_data[display_name] = str(formatted_data[internal_name])
                formatted_data = frontend_data
            
            result = {
                "DocumentID": key.split('/')[-1],
                "DocumentType": doc_type,
                "ClassificationConfidence": confidence,
                "UploadDate": record['eventTime'],
                "S3Location": f"s3://{bucket}/{key}",
                "Data": formatted_data,
                "ProcessingStatus": "Completed",
                "ExtractionMetadata": extracted_data.get('ExtractionMetadata', {})
            }
            
            # Step 5: Store results
            print("Storing results to DynamoDB...")
            storage.save_document_metadata(result)
            print("Processing completed successfully")
        
            return {
                'statusCode': 200,
                'body': json.dumps(result, default=str)
            }
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        error_result = {
            "DocumentID": key.split('/')[-1] if 'key' in locals() else "unknown",
            "ProcessingStatus": "Failed",
            "Error": str(e),
            "ErrorType": type(e).__name__
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