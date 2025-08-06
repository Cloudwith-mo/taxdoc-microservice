#!/usr/bin/env python3
"""
Test script for TaxDoc V1 MVP
Tests the tax document extraction pipeline locally
"""

import sys
import os
import base64
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from services.tax_classifier import TaxClassifier
from services.tax_extractor import TaxExtractor

def test_classifier():
    """Test the tax document classifier"""
    print("🧪 Testing Tax Document Classifier...")
    
    classifier = TaxClassifier()
    
    # Test W-2 classification
    w2_textract_response = {
        'Blocks': [
            {'BlockType': 'LINE', 'Text': 'W-2 Wage and Tax Statement'},
            {'BlockType': 'LINE', 'Text': 'Employee Social Security Number'},
            {'BlockType': 'LINE', 'Text': 'Wages, tips, other compensation'}
        ]
    }
    
    result = classifier.classify_tax_document(w2_textract_response)
    print(f"  W-2 Classification: {result}")
    assert result == "W-2", f"Expected W-2, got {result}"
    
    # Test 1099-NEC classification
    nec_textract_response = {
        'Blocks': [
            {'BlockType': 'LINE', 'Text': '1099-NEC'},
            {'BlockType': 'LINE', 'Text': 'Nonemployee Compensation'},
            {'BlockType': 'LINE', 'Text': 'Payer federal identification'}
        ]
    }
    
    result = classifier.classify_tax_document(nec_textract_response)
    print(f"  1099-NEC Classification: {result}")
    assert result == "1099-NEC", f"Expected 1099-NEC, got {result}"
    
    # Test unsupported document
    unsupported_response = {
        'Blocks': [
            {'BlockType': 'LINE', 'Text': 'Some random document'},
            {'BlockType': 'LINE', 'Text': 'Not a tax form'}
        ]
    }
    
    result = classifier.classify_tax_document(unsupported_response)
    print(f"  Unsupported Classification: {result}")
    assert result == "Unsupported", f"Expected Unsupported, got {result}"
    
    print("✅ Classifier tests passed!")

def test_extractor():
    """Test the tax data extractor"""
    print("\n🧪 Testing Tax Data Extractor...")
    
    extractor = TaxExtractor()
    
    # Mock W-2 textract response
    w2_textract_response = {
        'Blocks': [
            {'BlockType': 'LINE', 'Text': 'W-2 Wage and Tax Statement'},
            {'BlockType': 'LINE', 'Text': 'Employee SSN: 123-45-6789'},
            {'BlockType': 'LINE', 'Text': 'Employer EIN: 12-3456789'},
            {'BlockType': 'LINE', 'Text': 'Box 1 Wages: $50,000.00'},
            {'BlockType': 'LINE', 'Text': 'Box 2 Federal tax withheld: $7,500.00'},
            {'BlockType': 'LINE', 'Text': 'Box 3 Social Security wages: $50,000.00'},
            {'BlockType': 'LINE', 'Text': 'Box 5 Medicare wages: $50,000.00'}
        ]
    }
    
    # Test extraction (will use fallback since no Claude API key in test)
    result = extractor.extract_tax_data(w2_textract_response, "W-2")
    print(f"  W-2 Extraction Result: {json.dumps(result, indent=2)}")
    
    # Verify some basic fields were extracted
    assert 'employee_ssn' in result, "Missing employee_ssn field"
    assert 'employer_ein' in result, "Missing employer_ein field"
    
    print("✅ Extractor tests passed!")

def test_with_sample_image():
    """Test with actual sample image if available"""
    print("\n🧪 Testing with Sample Image...")
    
    # Look for sample images
    images_dir = Path(__file__).parent.parent / 'images'
    sample_files = ['W2-sample.png', '1099-sample.png']
    
    for sample_file in sample_files:
        sample_path = images_dir / sample_file
        if sample_path.exists():
            print(f"  Found sample: {sample_file}")
            
            # Read and encode file
            with open(sample_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode('utf-8')
            
            # This would normally call the Lambda handler
            print(f"  File size: {len(file_content)} characters (base64)")
            print(f"  Ready for processing: {sample_file}")
        else:
            print(f"  Sample not found: {sample_file}")

def main():
    """Run all tests"""
    print("🚀 TaxDoc V1 MVP Test Suite")
    print("=" * 40)
    
    try:
        test_classifier()
        test_extractor()
        test_with_sample_image()
        
        print("\n🎉 All tests passed!")
        print("\n📋 Next Steps:")
        print("1. Deploy with: ./scripts/deploy_v1_mvp.sh")
        print("2. Test with real documents")
        print("3. Monitor performance and accuracy")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()