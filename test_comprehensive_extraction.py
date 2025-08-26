#!/usr/bin/env python3
"""
Test comprehensive W-2 extraction directly
"""
import sys
import os
sys.path.append('src')

from services.enhanced_tax_extractor import EnhancedTaxExtractor
from services.tax_classifier import TaxClassifier
import boto3
import json

def test_comprehensive_extraction():
    """Test the comprehensive extraction pipeline"""
    
    # Mock Textract response with comprehensive W-2 data
    mock_textract_response = {
        'Blocks': [
            {'BlockType': 'LINE', 'Text': 'W-2 Wage and Tax Statement'},
            {'BlockType': 'LINE', 'Text': 'Employee Social Security Number: 123-45-6789'},
            {'BlockType': 'LINE', 'Text': 'Employer identification number: 11-2233445'},
            {'BlockType': 'LINE', 'Text': 'Control number: C12345'},
            {'BlockType': 'LINE', 'Text': 'Employee name: John A. Smith'},
            {'BlockType': 'LINE', 'Text': 'Employee address: 123 Main St, Anytown, ST 12345'},
            {'BlockType': 'LINE', 'Text': 'Employer name: ABC Corporation'},
            {'BlockType': 'LINE', 'Text': 'Employer address: 456 Business Ave, Corporate City, ST 67890'},
            {'BlockType': 'LINE', 'Text': 'Box 1 Wages, tips, other compensation: 75,000.00'},
            {'BlockType': 'LINE', 'Text': 'Box 2 Federal income tax withheld: 12,500.00'},
            {'BlockType': 'LINE', 'Text': 'Box 3 Social security wages: 75,000.00'},
            {'BlockType': 'LINE', 'Text': 'Box 4 Social security tax withheld: 4,650.00'},
            {'BlockType': 'LINE', 'Text': 'Box 5 Medicare wages and tips: 75,000.00'},
            {'BlockType': 'LINE', 'Text': 'Box 6 Medicare tax withheld: 1,087.50'},
            {'BlockType': 'LINE', 'Text': 'Box 15 State: CA'},
            {'BlockType': 'LINE', 'Text': 'Box 16 State wages, tips, etc.: 75,000.00'},
            {'BlockType': 'LINE', 'Text': 'Box 17 State income tax: 3,750.00'},
            {'BlockType': 'LINE', 'Text': 'Box 18 Local wages, tips, etc.: 75,000.00'},
            {'BlockType': 'LINE', 'Text': 'Box 19 Local income tax: 750.00'},
            {'BlockType': 'LINE', 'Text': 'Box 20 Locality name: San Francisco'},
            {'BlockType': 'LINE', 'Text': 'Box 12a Code: D Amount: 2,500.00'},
            {'BlockType': 'LINE', 'Text': 'Box 12b Code: W Amount: 1,200.00'},
        ]
    }
    
    print("=== TESTING COMPREHENSIVE W-2 EXTRACTION ===")
    
    # Step 1: Test classification
    classifier = TaxClassifier()
    doc_type = classifier.classify_tax_document(mock_textract_response)
    print(f"Document Type: {doc_type}")
    
    # Step 2: Test extraction
    extractor = EnhancedTaxExtractor()
    
    try:
        extracted_data = extractor.extract_with_three_layers(mock_textract_response, doc_type)
        
        print(f"\nTotal Fields Extracted: {extracted_data.get('total_fields_extracted', 0)}")
        print(f"Layers Used: {extracted_data.get('layers_used', [])}")
        
        print("\n=== EXTRACTED FIELDS ===")
        field_count = 0
        for key, value in extracted_data.items():
            if key not in ['layers_used', 'confidence_scores', 'extraction_method', 'total_fields_extracted']:
                print(f"{key}: {value}")
                field_count += 1
        
        print(f"\n=== RESULTS ===")
        print(f"Actual fields extracted: {field_count}")
        print(f"Expected comprehensive fields: 20+")
        
        if 'bedrock_claude' in extracted_data.get('layers_used', []):
            print("✅ SUCCESS - Claude layer activated!")
            if field_count >= 15:
                print("🎯 COMPREHENSIVE EXTRACTION ACHIEVED!")
            else:
                print(f"⚠️  Claude activated but only {field_count} fields extracted")
        else:
            print(f"⚠️  Only Textract used - {field_count} fields extracted")
            
        return extracted_data
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_comprehensive_extraction()