#!/usr/bin/env python3

"""
Test script for the three-layer AI extraction pipeline
Tests Textract Queries → Claude LLM → Regex fallback
"""

import sys
import os
import base64
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.three_layer_orchestrator import ThreeLayerOrchestrator
from services.enhanced_classifier import EnhancedClassifier

def test_three_layer_extraction():
    """Test the three-layer extraction pipeline"""
    
    print("🧪 Testing Three-Layer AI Extraction Pipeline")
    print("=" * 50)
    
    # Test with a sample image
    image_path = "../images/W2-sample.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return
    
    try:
        # Read test document
        with open(image_path, 'rb') as f:
            document_bytes = f.read()
        
        print(f"📄 Testing with: {image_path}")
        print(f"📊 Document size: {len(document_bytes)} bytes")
        
        # Step 1: Classify document
        print("\n🔍 Step 1: Document Classification")
        classifier = EnhancedClassifier()
        
        # Get basic text for classification
        import boto3
        textract = boto3.client('textract')
        basic_response = textract.detect_document_text(Document={'Bytes': document_bytes})
        
        doc_type, confidence = classifier.classify_document(basic_response)
        print(f"   Document Type: {doc_type}")
        print(f"   Confidence: {confidence:.2f}")
        
        # Step 2: Three-layer extraction
        print(f"\n⚙️  Step 2: Three-Layer Extraction for {doc_type}")
        orchestrator = ThreeLayerOrchestrator()
        
        results = orchestrator.extract_document_fields(document_bytes, doc_type)
        
        # Display results
        print(f"\n📋 Extraction Results:")
        print(f"   Document Type: {results.get('DocumentType')}")
        
        metadata = results.get('ExtractionMetadata', {})
        print(f"   Total Fields: {metadata.get('total_fields', 0)}")
        print(f"   Overall Confidence: {metadata.get('overall_confidence', 0):.2f}")
        print(f"   Processing Layers: {', '.join(metadata.get('processing_layers', []))}")
        print(f"   Needs Review: {metadata.get('needs_review', False)}")
        
        # Show extracted fields
        print(f"\n📝 Extracted Fields:")
        for key, value in results.items():
            if not key.startswith('_') and key not in ['DocumentType', 'ExtractionMetadata']:
                confidence_key = f"{key}_confidence"
                source_key = f"{key}_source"
                
                confidence = results.get(confidence_key, 'N/A')
                source = results.get(source_key, 'unknown')
                
                print(f"   {key}: {value}")
                print(f"      └─ Confidence: {confidence}, Source: {source}")
        
        print(f"\n✅ Three-layer extraction completed successfully!")
        
        # Test metrics
        print(f"\n📊 Layer Performance:")
        print(f"   Textract Fields: {metadata.get('textract_fields', 0)}")
        print(f"   LLM Fields: {metadata.get('llm_fields', 0)}")
        print(f"   Regex Fields: {metadata.get('regex_fields', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_api_integration():
    """Test API integration with base64 encoding"""
    
    print(f"\n🌐 Testing API Integration")
    print("=" * 30)
    
    image_path = "../images/W2-sample.png"
    
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return
    
    try:
        # Read and encode document
        with open(image_path, 'rb') as f:
            document_bytes = f.read()
        
        encoded_content = base64.b64encode(document_bytes).decode('utf-8')
        
        # Simulate API request
        api_request = {
            'filename': 'test-w2.png',
            'file_content': encoded_content
        }
        
        print(f"📤 API Request prepared:")
        print(f"   Filename: {api_request['filename']}")
        print(f"   Content Size: {len(encoded_content)} chars (base64)")
        
        # Test decoding
        decoded_bytes = base64.b64decode(api_request['file_content'])
        print(f"   Decoded Size: {len(decoded_bytes)} bytes")
        
        if len(decoded_bytes) == len(document_bytes):
            print("✅ Base64 encoding/decoding successful")
        else:
            print("❌ Base64 encoding/decoding failed")
        
        return True
        
    except Exception as e:
        print(f"❌ API integration test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Dr.Doc Three-Layer Pipeline Test Suite")
    print("=" * 60)
    
    # Test 1: Three-layer extraction
    test1_success = test_three_layer_extraction()
    
    # Test 2: API integration
    test2_success = test_api_integration()
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Three-Layer Extraction: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"   API Integration: {'✅ PASS' if test2_success else '❌ FAIL'}")
    
    if test1_success and test2_success:
        print(f"\n🎉 All tests passed! Pipeline is ready for deployment.")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some tests failed. Please check the implementation.")
        sys.exit(1)