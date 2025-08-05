import json
import boto3
import base64
import time
from typing import Dict, Any
import sys
import os
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch AWS SDK calls for X-Ray tracing
patch_all()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.tax_orchestrator import TaxOrchestrator, UnsupportedTaxDocument
from services.enhanced_classifier import EnhancedClassifier
from services.storage_service import StorageService
from services.monitoring_service import MonitoringService

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Enhanced API Gateway handler with three-layer processing"""
    
    try:
        # Validate event structure
        if not isinstance(event, dict):
            print(f"ERROR: Event is not a dict: {type(event)} - {event}")
            return {
                'statusCode': 500,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid event format'})
            }
        
        http_method = event.get('httpMethod', 'UNKNOWN')
        path = event.get('path', '/unknown')
        
        print(f"Processing {http_method} request to {path}")
        
        # CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400'
        }
        
        if http_method == 'OPTIONS':
            return {'statusCode': 200, 'headers': cors_headers, 'body': ''}
        
        if http_method == 'POST' and path == '/process-document':
            return process_document_enhanced(event, cors_headers)
        elif http_method == 'GET' and '/result/' in path:
            path_params = event.get('pathParameters', {})
            if not isinstance(path_params, dict):
                print(f"ERROR: pathParameters is not a dict: {type(path_params)} - {path_params}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Invalid path parameters'})
                }
            doc_id = path_params.get('doc_id', 'unknown')
            return get_processing_result(doc_id, cors_headers)
        elif http_method == 'GET' and '/download-excel/' in path:
            path_params = event.get('pathParameters', {})
            if not isinstance(path_params, dict):
                print(f"ERROR: pathParameters is not a dict: {type(path_params)} - {path_params}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Invalid path parameters'})
                }
            doc_id = path_params.get('doc_id', 'unknown')
            return generate_excel_download(doc_id, cors_headers)
        elif http_method == 'GET' and path == '/supported-types':
            return get_supported_types(cors_headers)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        print(f"CRITICAL ERROR in lambda_handler: {str(e)}")
        print(f"Event type: {type(event)}, Event: {event}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}', 'event_type': str(type(event))})
        }

@xray_recorder.capture('process_document_enhanced')
def process_document_enhanced(event: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Process document using enhanced three-layer pipeline"""
    
    start_time = time.time()
    monitoring = MonitoringService()
    
    try:
        # Parse request body safely
        try:
            body_str = event.get('body', '{}')
            if isinstance(body_str, str):
                body = json.loads(body_str)
            elif isinstance(body_str, dict):
                body = body_str
            else:
                print(f"ERROR: Unexpected body type: {type(body_str)} - {body_str}")
                body = {}
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse JSON body: {str(e)}")
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        filename = body.get('filename', 'unknown')
        file_content = body.get('file_content')
        
        # Add X-Ray metadata
        xray_recorder.put_metadata('request', {
            'filename': filename,
            'processing_start': start_time
        })
        
        if not file_content:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'No file content provided'})
            }
        
        # Decode file
        document_bytes = base64.b64decode(file_content)
        
        # Step 1: Classify document with X-Ray tracing
        with xray_recorder.in_subsegment('document_classification'):
            try:
                classifier = EnhancedClassifier()
                # First get basic text for classification
                textract_client = boto3.client('textract')
                textract_basic = textract_client.detect_document_text(
                    Document={'Bytes': document_bytes}
                )
                
                # Ensure textract response is valid
                if not isinstance(textract_basic, dict):
                    print(f"ERROR: Textract returned {type(textract_basic)}: {textract_basic}")
                    doc_type, confidence = "Other Document", 0.1
                else:
                    classification_result = classifier.classify_document(textract_basic)
                    if isinstance(classification_result, tuple) and len(classification_result) == 2:
                        doc_type, confidence = classification_result
                    else:
                        print(f"ERROR: Classifier returned invalid result: {classification_result}")
                        doc_type, confidence = "Other Document", 0.1
                
                xray_recorder.put_metadata('classification', {
                    'document_type': doc_type,
                    'confidence': confidence
                })
                
            except Exception as e:
                print(f"ERROR: Classification failed: {str(e)}")
                doc_type, confidence = "Other Document", 0.1
                xray_recorder.put_metadata('classification_error', str(e))
        
        # Step 2: Three-layer extraction with X-Ray tracing
        with xray_recorder.in_subsegment('three_layer_extraction'):
            xray_recorder.put_metadata('extraction', {
                'document_type': doc_type,
                'classification_confidence': confidence
            })
            
            try:
                orchestrator = TaxOrchestrator()
                extraction_result = orchestrator.extract_tax_document(document_bytes, doc_type)
                
                # Critical: Ensure we always have a dictionary
                if not isinstance(extraction_result, dict):
                    print(f"ERROR: Orchestrator returned {type(extraction_result)}: {extraction_result}")
                    extraction_result = {
                        'DocumentType': doc_type,
                        'error': f'Invalid extraction result format: {type(extraction_result)} - {str(extraction_result)}',
                        'ExtractionMetadata': {
                            'processing_layers': [],
                            'overall_confidence': 0.0,
                            'needs_review': True,
                            'processing_status': 'failed'
                        },
                        'ExtractedData': {},
                        'QualityMetrics': {'overall_confidence': 0.0}
                    }
                    
            except UnsupportedTaxDocument as e:
                print(f"UNSUPPORTED TAX DOCUMENT: {str(e)}")
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'error': 'Unsupported Document (Tax Edition)',
                        'message': 'Only federal tax forms supported. Email sales@taxflowsai.com',
                        'supported_forms': ['1040', 'W-2', '1099-NEC', '1099-MISC', '1099-DIV', '1099-INT', 'K-1', '941']
                    })
                }
            except Exception as e:
                print(f"ERROR: Orchestrator exception: {str(e)}")
                import traceback
                traceback.print_exc()
                extraction_result = {
                    'DocumentType': doc_type,
                    'error': f'Extraction failed: {str(e)}',
                    'ExtractionMetadata': {
                        'processing_layers': [],
                        'overall_confidence': 0.0,
                        'needs_review': True,
                        'processing_status': 'failed'
                    },
                    'ExtractedData': {},
                    'QualityMetrics': {'overall_confidence': 0.0}
                }
        
        # Step 3: Format result with type safety
        processing_time = time.time() - start_time
        
        # Final safety check - ensure extraction_result is a dict
        if not isinstance(extraction_result, dict):
            print(f"CRITICAL: extraction_result is not a dict: {type(extraction_result)} - {extraction_result}")
            extraction_result = {
                'DocumentType': doc_type,
                'error': f'Critical error: result is {type(extraction_result)} instead of dict',
                'ExtractionMetadata': {'processing_layers': [], 'overall_confidence': 0.0, 'needs_review': True},
                'ExtractedData': {},
                'QualityMetrics': {'overall_confidence': 0.0}
            }
        
        # Determine processing status based on extraction success
        has_error = 'error' in extraction_result
        overall_confidence = extraction_result.get('ExtractionMetadata', {}).get('overall_confidence', 0.0)
        processing_status = "Failed" if has_error or overall_confidence == 0.0 else "Completed"
        
        # Extract the actual field data for frontend compatibility
        extracted_data = extraction_result.get('ExtractedData', {})
        
        # Create W-2 compatible format
        formatted_data = {}
        if doc_type == "W-2":
            # Map to expected W-2 field names
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
            
            for internal_name, display_name in field_mapping.items():
                if internal_name in extracted_data:
                    formatted_data[display_name] = str(extracted_data[internal_name])
            
            # Add additional fields if they exist
            if 'Box15_State' in extracted_data:
                formatted_data['15 State'] = str(extracted_data['Box15_State'])
            if 'Box16_StateWages' in extracted_data:
                formatted_data['16 State wages, tips, etc.'] = str(extracted_data['Box16_StateWages'])
            if 'Box17_StateTaxWithheld' in extracted_data:
                formatted_data['17 State income tax'] = str(extracted_data['Box17_StateTaxWithheld'])
        else:
            # For other document types, use extracted data as-is
            formatted_data = extracted_data
        
        result = {
            "DocumentID": filename,
            "DocumentType": extraction_result.get('DocumentType', doc_type),
            "ClassificationConfidence": confidence,
            "UploadDate": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ProcessingStatus": processing_status,
            "ProcessingTime": processing_time,
            "Data": formatted_data,  # Use formatted data for frontend compatibility
            "S3Location": "",  # Add for compatibility
            "CreatedAt": time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "ExtractionMetadata": extraction_result.get('ExtractionMetadata', {}),
            "QualityMetrics": extraction_result.get('QualityMetrics', {'overall_confidence': overall_confidence})
        }
        
        # Include error information if present
        if has_error:
            result["Error"] = extraction_result.get('error', 'Unknown error')
            result["ErrorType"] = "ExtractionError"
        
        # Step 4: Store results with validation
        try:
            storage = StorageService()
            if isinstance(result, dict):
                storage.save_document_metadata(result)
                print(f"Successfully saved document metadata for {result.get('DocumentID', 'unknown')}")
            else:
                print(f"ERROR: Result is not a dictionary: {type(result)} - {result}")
                # Don't attempt to save invalid results
        except Exception as e:
            print(f"ERROR: Failed to save document metadata: {str(e)}")
            print(f"Result type: {type(result)}, Result: {result}")
            # Continue processing even if storage fails
        
        # Step 5: Log enhanced metrics and cost tracking
        try:
            from services.cloudwatch_metrics import CloudWatchMetrics
            from services.cost_control import CostControlService
            
            metrics = CloudWatchMetrics()
            cost_control = CostControlService()
            
            # Safely extract metadata
            metadata = {}
            if isinstance(extraction_result, dict):
                metadata = extraction_result.get('ExtractionMetadata', {})
            
            # Log metrics
            metrics.put_document_processed(
                doc_type, 
                processing_time, 
                metadata.get('overall_confidence', 0.0)
            )
            metrics.put_layer_usage(
                metadata.get('processing_layers', []), 
                doc_type
            )
            
            # Track costs
            if 'claude' in metadata.get('processing_layers', []):
                # Estimate tokens used (rough calculation)
                tokens_used = len(document_bytes) // 4  # ~4 bytes per token
                cost_control.track_claude_usage(tokens_used, doc_type)
            
            # Track Textract usage
            cost_control.track_textract_usage(1, doc_type, ['QUERIES'])
            
        except Exception as e:
            print(f"ERROR: Failed to log metrics: {str(e)}")
            # Continue processing even if metrics fail
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        print(f"CRITICAL ERROR in process_document_enhanced: {str(e)}")
        import traceback
        traceback.print_exc()
        
        try:
            from services.cloudwatch_metrics import CloudWatchMetrics
            from services.cost_control import CostControlService
            
            metrics = CloudWatchMetrics()
            cost_control = CostControlService()
            
            metrics.put_error_metric(type(e).__name__, 'EnhancedApiFunction')
            
            # Check if we're hitting cost limits
            limits = cost_control.check_daily_limits()
            if limits.get('claude_limit_exceeded', False) or limits.get('textract_limit_exceeded', False):
                print(f"WARNING: Daily cost limits exceeded - Claude: {limits.get('claude_limit_exceeded', False)}, Textract: {limits.get('textract_limit_exceeded', False)}")
        except Exception as metrics_error:
            print(f"ERROR: Failed to log error metrics: {str(metrics_error)}")
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': f'Processing failed: {str(e)}',
                'processing_time': processing_time
            })
        }

def get_processing_result(doc_id: str, cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Get processing result by document ID"""
    
    try:
        storage = StorageService()
        result = storage.get_document_metadata(doc_id)
        
        if result:
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Document not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }

def get_supported_types(cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Return list of supported tax document types only"""
    
    from config.tax_document_config import SUPPORTED_TAX_FORMS
    
    return {
        'statusCode': 200,
        'headers': cors_headers,
        'body': json.dumps({
            'supported_types': list(SUPPORTED_TAX_FORMS),
            'message': 'Tax Edition - Federal tax forms only',
            'contact': 'sales@taxflowsai.com'
        })
    }

def generate_excel_download(doc_id: str, cors_headers: Dict[str, str]) -> Dict[str, Any]:
    """Generate Excel download for document results"""
    
    try:
        storage = StorageService()
        result = storage.get_document_metadata(doc_id)
        
        if not result:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Document not found'})
            }
        
        # Generate presigned URL for Excel download
        s3 = boto3.client('s3')
        bucket = os.environ.get('UPLOAD_BUCKET')
        excel_key = f"excel-exports/{doc_id}.xlsx"
        
        # Create simple Excel content (in production, use openpyxl)
        excel_data = f"Document ID,{doc_id}\nDocument Type,{result.get('DocumentType', 'Unknown')}\n"
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket,
            Key=excel_key,
            Body=excel_data,
            ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Generate presigned URL
        download_url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': excel_key},
            ExpiresIn=3600
        )
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'download_url': download_url})
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }