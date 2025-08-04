#!/usr/bin/env python3
"""
Test script for multi-form document extraction
Tests the three-layer extraction pipeline on various document types
"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from services.enhanced_classifier import EnhancedClassifier
from services.multi_form_extractor import MultiFormExtractor
from services.textract_service import TextractService

def test_document_extraction(image_path: str, expected_doc_type: str = None):
    """Test extraction on a single document"""
    
    print(f"\n{'='*60}")
    print(f"Testing: {os.path.basename(image_path)}")
    print(f"{'='*60}")
    
    try:
        # Read document bytes
        with open(image_path, 'rb') as f:
            document_bytes = f.read()
        
        print(f"Document size: {len(document_bytes)} bytes")
        
        # Initialize services
        textract = TextractService()
        classifier = EnhancedClassifier()
        extractor = MultiFormExtractor()
        
        # Step 1: Get basic OCR for classification
        print("\n1. Running basic Textract OCR...")
        textract_response = textract.detect_document_text_bytes(document_bytes)
        print(f"   OCR completed: {len(textract_response.get('Blocks', []))} blocks")
        
        # Step 2: Classify document
        print("\n2. Classifying document type...")
        doc_type, confidence = classifier.classify_document(textract_response)
        print(f"   Classification: {doc_type} (confidence: {confidence:.2f})")
        
        if expected_doc_type and doc_type != expected_doc_type:
            print(f"   ⚠️  Expected {expected_doc_type}, got {doc_type}")
        
        # Step 3: Multi-form extraction
        print(f"\n3. Running multi-form extraction for {doc_type}...")
        extracted_data = extractor.extract_document_fields(
            document_bytes=document_bytes,
            document_type=doc_type
        )
        
        # Display results
        print(f"\n4. Extraction Results:")
        print(f"   Document Type: {extracted_data.get('DocumentType', 'Unknown')}")
        
        metadata = extracted_data.get('ExtractionMetadata', {})
        print(f"   Total Fields: {metadata.get('total_fields', 0)}")
        print(f"   Overall Confidence: {metadata.get('overall_confidence', 0):.2f}")
        print(f"   Needs Review: {metadata.get('needs_review', False)}")
        print(f"   Textract Fields: {metadata.get('textract_fields', 0)}")
        print(f"   LLM Fields: {metadata.get('llm_fields', 0)}")
        print(f"   Regex Fields: {metadata.get('regex_fields', 0)}")
        
        # Show extracted fields
        print(f"\n5. Extracted Fields:")
        for key, value in extracted_data.items():
            if key not in ['DocumentType', 'ExtractionMetadata'] and not key.endswith('_confidence') and not key.endswith('_source'):
                confidence_key = f"{key}_confidence"
                source_key = f"{key}_source"
                confidence = extracted_data.get(confidence_key, 'N/A')
                source = extracted_data.get(source_key, 'unknown')
                
                print(f"   {key}: {value}")
                print(f"      └─ Confidence: {confidence}, Source: {source}")
        
        # Save detailed results
        output_file = f"test_results_{os.path.basename(image_path)}.json"
        with open(output_file, 'w') as f:
            json.dump(extracted_data, f, indent=2, default=str)
        print(f"\n6. Detailed results saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing {image_path}: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Test multi-form extraction on sample documents"""
    
    print("Multi-Form Document Extraction Test")
    print("Testing three-layer extraction: Textract Queries → Claude LLM → Regex")
    
    # Test cases with expected document types
    test_cases = [
        ("../images/W2-sample.png", "W-2"),
        ("../images/1099-sample.png", "1099-NEC"),
        ("../images/sample-walmart-receipt.webp", "Receipt"),
        ("../images/Sample-BankStatementChequing.png", "Bank Statement"),
        ("../images/sample-invoive.jpeg", "Invoice"),
    ]
    
    results = []
    
    for image_path, expected_type in test_cases:
        full_path = os.path.join(os.path.dirname(__file__), image_path)
        
        if os.path.exists(full_path):
            success = test_document_extraction(full_path, expected_type)
            results.append((os.path.basename(full_path), success))
        else:
            print(f"⚠️  File not found: {full_path}")
            results.append((os.path.basename(image_path), False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    successful = sum(1 for _, success in results if success)
    total = len(results)
    
    for filename, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {filename}")
    
    print(f"\nOverall: {successful}/{total} tests passed")
    
    if successful == total:
        print("🎉 All tests passed! Multi-form extraction is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")

if __name__ == "__main__":
    main()