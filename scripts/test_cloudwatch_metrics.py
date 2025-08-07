#!/usr/bin/env python3
"""
Test CloudWatch Metrics Integration
"""
import requests
import base64
import json
import time
import os

API_ENDPOINT = "https://abfum9qn84.execute-api.us-east-1.amazonaws.com/mvp"

def test_document(filename, file_path):
    """Test document processing and return metrics"""
    print(f"\n🔄 Testing {filename}...")
    
    try:
        with open(file_path, 'rb') as f:
            file_content = base64.b64encode(f.read()).decode('utf-8')
        
        response = requests.post(
            f"{API_ENDPOINT}/process-document",
            headers={'Content-Type': 'application/json'},
            json={
                'filename': filename,
                'file_content': file_content
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Success: {data['document_type']}")
                print(f"⏱️  Processing time: {data['processing_info']['processing_time']:.2f}s")
                print(f"🔧 Layers used: {', '.join(data['processing_info']['layers_used'])}")
                return True
            else:
                print(f"❌ Failed: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def main():
    print("🚀 Testing CloudWatch Metrics Integration")
    print("=" * 50)
    
    # Test documents
    test_files = [
        ("W2-sample.png", "images/W2-sample.png"),
        ("1099-sample.png", "images/1099-sample.png"),
        ("sample-walmart-receipt.webp", "images/sample-walmart-receipt.webp")
    ]
    
    success_count = 0
    
    for filename, filepath in test_files:
        if os.path.exists(filepath):
            if test_document(filename, filepath):
                success_count += 1
            time.sleep(2)  # Brief pause between requests
        else:
            print(f"⚠️  File not found: {filepath}")
    
    print(f"\n📊 Results: {success_count}/{len(test_files)} documents processed successfully")
    print("\n🌐 View CloudWatch Dashboard:")
    print("https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=TaxDoc-Processing-Metrics")
    
    print("\n📈 Key Metrics Available:")
    print("- DocumentsProcessed (by FormType)")
    print("- ProcessingTime (average seconds)")
    print("- ExtractionConfidence (percentage)")
    print("- FieldsExtracted (count)")
    print("- TextractUsage, ClaudeUsage, RegexUsage")

if __name__ == "__main__":
    main()