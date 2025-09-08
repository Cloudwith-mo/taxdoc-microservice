#!/usr/bin/env python3
"""Day-0 Smoke Tests for AWS IDP Pipeline"""

import requests
import json
import base64

API_BASE = "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod"

def test_s3_upload_flow():
    """Test S3 presigned URL upload flow"""
    print("🧪 Testing S3 Upload Flow...")
    
    # Test presigned URL generation
    response = requests.get(f"{API_BASE}/upload-url", params={
        "filename": "test-w2.png",
        "contentType": "image/png"
    })
    
    if response.status_code != 200:
        print(f"❌ Upload URL failed: {response.status_code}")
        return False
    
    print("✅ S3 Upload Flow test completed")
    return True

def test_document_processing():
    """Test document processing with S3 key"""
    print("🧪 Testing Document Processing with S3 key...")
    
    # Test with S3 key (should exist from previous uploads)
    response = requests.post(f"{API_BASE}/process", 
                           headers={"Content-Type": "application/json"},
                           json={
                               "s3Key": "uploads/3ddfe8d6-5f48-4a05-b185-9ce0d06cb005_W2-sample.png",
                               "filename": "W2-sample.png"
                           })
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Document type: {result.get('docType', 'Unknown')}")
        print(f"Confidence: {result.get('docTypeConfidence', 0)}")
        print(f"Fields extracted: {len(result.get('fields', {}))}")
        return True
    else:
        print(f"❌ Processing failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def run_smoke_tests():
    """Run all smoke tests"""
    print("🚀 AWS IDP Pipeline Smoke Tests\n")
    
    tests = [
        ("S3 Upload Flow", test_s3_upload_flow),
        ("Document Processing", test_document_processing)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASS' if result else 'FAIL'}\n")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}\n")
            results.append((test_name, False))
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"📊 Results: {passed}/{total} passed")
    return passed == total

if __name__ == "__main__":
    run_smoke_tests()