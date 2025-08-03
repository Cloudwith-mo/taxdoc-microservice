#!/usr/bin/env python3

import boto3
import sys
import json
from pathlib import Path

def upload_test_document(file_path: str, bucket_name: str = None):
    """Upload a test document to S3 for processing"""
    
    if not bucket_name:
        bucket_name = 'taxdoc-uploads-dev'  # Default dev bucket
    
    s3_client = boto3.client('s3')
    
    try:
        # Upload file to incoming/ prefix to trigger processing
        file_name = Path(file_path).name
        s3_key = f'incoming/{file_name}'
        
        print(f"Uploading {file_path} to s3://{bucket_name}/{s3_key}")
        
        s3_client.upload_file(file_path, bucket_name, s3_key)
        
        print(f"Upload successful! Document will be processed automatically.")
        print(f"S3 Location: s3://{bucket_name}/{s3_key}")
        
        return s3_key
        
    except Exception as e:
        print(f"Upload failed: {str(e)}")
        return None

def check_processing_result(doc_id: str):
    """Check processing result in DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('TaxDocuments-dev')
    
    try:
        response = table.get_item(Key={'DocumentID': doc_id})
        
        if 'Item' in response:
            item = response['Item']
            print(f"\nProcessing Result for {doc_id}:")
            print(f"Status: {item.get('ProcessingStatus', 'Unknown')}")
            print(f"Document Type: {item.get('DocumentType', 'Unknown')}")
            
            if 'Data' in item:
                data = json.loads(item['Data'])
                print(f"Extracted Data: {json.dumps(data, indent=2)}")
        else:
            print(f"No result found for document {doc_id}")
            
    except Exception as e:
        print(f"Error checking result: {str(e)}")

if __name__ == "__main__":
    # If --check flag is used
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        if len(sys.argv) < 3:
            print("Usage: python test_upload.py --check <document_id>")
            sys.exit(1)
        doc_id = sys.argv[2]
        check_processing_result(doc_id)
    else:
        if len(sys.argv) < 2:
            print("Usage: python test_upload.py <file_path> [bucket_name]")
            sys.exit(1)
        
        file_path = sys.argv[1]
        bucket_name = sys.argv[2] if len(sys.argv) > 2 else None
        
        # Upload document
        s3_key = upload_test_document(file_path, bucket_name)
        
        if s3_key:
            doc_id = Path(s3_key).name
            print(f"\nWait a few seconds for processing, then check result with:")
            print(f"python scripts/test_upload.py --check {doc_id}")