#!/usr/bin/env python3

import requests
import base64
import json
import time
from pathlib import Path

API_BASE = "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod"

def test_api_endpoint():
    """Test basic API connectivity"""
    try:
        response = requests.get(f"{API_BASE}/result/test")
        print(f"✅ API is accessible: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def process_document(file_path):
    """Process a document using the live API"""
    try:
        # Read and encode file
        with open(file_path, 'rb') as f:
            file_content = base64.b64encode(f.read()).decode('utf-8')
        
        # Prepare request
        payload = {
            "filename": Path(file_path).name,
            "file_content": file_content
        }
        
        print(f"🚀 Processing {file_path}...")
        
        # Send request
        response = requests.post(
            f"{API_BASE}/process-document",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            doc_id = result.get('DocumentID')
            print(f"✅ Document submitted successfully!")
            print(f"Document ID: {doc_id}")
            
            # Poll for results
            return poll_for_results(doc_id)
        else:
            print(f"❌ Processing failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        return None

def poll_for_results(doc_id, max_attempts=30):
    """Poll for processing results"""
    print(f"⏳ Polling for results (max {max_attempts} attempts)...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_BASE}/result/{doc_id}")
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('ProcessingStatus')
                
                if status == 'Completed':
                    print(f"✅ Processing completed!")
                    return result
                elif status == 'Failed':
                    print(f"❌ Processing failed: {result.get('Error', 'Unknown error')}")
                    return result
                else:
                    print(f"⏳ Status: {status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(5)
            else:
                print(f"❌ Error checking status: {response.status_code}")
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Error polling results: {e}")
            time.sleep(5)
    
    print(f"⏰ Timeout waiting for results")
    return None

def display_results(result):
    """Display extraction results"""
    if not result:
        return
    
    print(f"\n📋 EXTRACTION RESULTS")
    print(f"=" * 50)
    print(f"Document Type: {result.get('DocumentType', 'Unknown')}")
    print(f"Processing Status: {result.get('ProcessingStatus', 'Unknown')}")
    print(f"Confidence Score: {result.get('ConfidenceScore', 'N/A')}")
    
    if 'ExtractedData' in result:
        print(f"\n📊 Extracted Data:")
        data = result['ExtractedData']
        for key, value in data.items():
            if isinstance(value, dict) and 'value' in value:
                confidence = value.get('confidence', 'N/A')
                source = value.get('source', 'N/A')
                print(f"  {key}: {value['value']} (confidence: {confidence}, source: {source})")
            else:
                print(f"  {key}: {value}")
    
    if 'ProcessingLayers' in result:
        print(f"\n🔍 Processing Layers Used:")
        for layer in result['ProcessingLayers']:
            print(f"  - {layer}")

def test_sample_documents():
    """Test with sample documents"""
    sample_files = [
        "images/W2-sample.png",
        "images/1099-sample.png",
        "images/Sample-BankStatementChequing.png"
    ]
    
    results = []
    
    for file_path in sample_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"\n{'='*60}")
            print(f"Testing: {file_path}")
            print(f"{'='*60}")
            
            result = process_document(str(full_path))
            if result:
                display_results(result)
                results.append(result)
            
            print(f"\n⏸️  Waiting 10 seconds before next test...")
            time.sleep(10)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    return results

if __name__ == "__main__":
    print("🧪 Testing Live Dr.Doc API")
    print(f"API Base: {API_BASE}")
    print("=" * 60)
    
    # Test API connectivity
    if not test_api_endpoint():
        exit(1)
    
    # Test with sample documents
    results = test_sample_documents()
    
    print(f"\n🎯 SUMMARY")
    print(f"=" * 30)
    print(f"Total tests: {len([f for f in ['images/W2-sample.png', 'images/1099-sample.png', 'images/Sample-BankStatementChequing.png'] if Path(f).exists()])}")
    print(f"Successful: {len([r for r in results if r and r.get('ProcessingStatus') == 'Completed'])}")
    print(f"Failed: {len([r for r in results if r and r.get('ProcessingStatus') == 'Failed'])}")
    
    print(f"\n🌐 Frontend URL: http://taxdoc-web-app-prod-1754284862.s3-website-us-east-1.amazonaws.com/")
    print(f"🔗 API URL: {API_BASE}")