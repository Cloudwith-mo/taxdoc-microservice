#!/usr/bin/env python3

import sys
import os
import base64
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.tax_form_processor import TaxFormProcessor

def test_mvp_pipeline():
    """Test the simplified MVP pipeline"""
    
    print("🧪 Testing TaxDoc MVP Pipeline")
    print("=" * 40)
    
    # Test with W-2 sample
    image_path = "../images/W2-sample.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return False
    
    try:
        # Read test document
        with open(image_path, 'rb') as f:
            document_bytes = f.read()
        
        print(f"📄 Testing with: {image_path}")
        print(f"📊 Document size: {len(document_bytes)} bytes")
        
        # Process with MVP pipeline
        processor = TaxFormProcessor()
        result = processor.process_tax_document(document_bytes, "W2-sample.png")
        
        # Display results
        print(f"\n📋 Processing Results:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            print(f"   Form Type: {result.get('form_type')}")
            print(f"   Classification Confidence: {result.get('classification_confidence', 0):.2f}")
            print(f"   Fields Extracted: {result.get('field_count', 0)}")
            
            print(f"\n📝 Extracted Fields:")
            for field, value in result.get('extracted_fields', {}).items():
                print(f"   {field}: {value}")
        else:
            print(f"   Error: {result.get('error')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_api_format():
    """Test API request/response format"""
    
    print(f"\n🌐 Testing API Format")
    print("=" * 25)
    
    image_path = "../images/W2-sample.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return False
    
    try:
        # Read and encode
        with open(image_path, 'rb') as f:
            document_bytes = f.read()
        
        encoded_content = base64.b64encode(document_bytes).decode('utf-8')
        
        # Simulate API request
        api_request = {
            'filename': 'test-w2.png',
            'file_content': encoded_content
        }
        
        print(f"📤 API Request Format:")
        print(f"   Filename: {api_request['filename']}")
        print(f"   Content Size: {len(encoded_content)} chars (base64)")
        
        # Test processing
        decoded_bytes = base64.b64decode(api_request['file_content'])
        processor = TaxFormProcessor()
        result = processor.process_tax_document(decoded_bytes, api_request['filename'])
        
        print(f"\n📥 API Response Format:")
        print(json.dumps(result, indent=2)[:500] + "...")
        
        return True
        
    except Exception as e:
        print(f"❌ API format test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 TaxDoc MVP Test Suite")
    print("=" * 50)
    
    # Test 1: MVP Pipeline
    test1_success = test_mvp_pipeline()
    
    # Test 2: API Format
    test2_success = test_api_format()
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   MVP Pipeline: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"   API Format: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print(f"\n🎉 All tests passed! MVP is ready for deployment.")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some tests failed. Please check the implementation.")
        sys.exit(1)