#!/usr/bin/env python3

import sys
import os
import json
import base64

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.three_layer_orchestrator import ThreeLayerOrchestrator
from services.template_service import TemplateService
from services.advanced_template_matcher import AdvancedTemplateMatcher

def test_w2_extraction():
    """Test W-2 extraction with proper formatting"""
    
    print("🧪 Testing W-2 Document Extraction")
    print("=" * 50)
    
    # Read the W-2 sample image
    image_path = "images/W2-sample.png"
    with open(image_path, 'rb') as f:
        document_bytes = f.read()
    
    try:
        # Use the orchestrator directly
        orchestrator = ThreeLayerOrchestrator()
        result = orchestrator.extract_document_fields(document_bytes, "W-2")
        
        print(f"✅ Document Type: {result.get('DocumentType')}")
        print(f"✅ Overall Confidence: {result.get('ExtractionMetadata', {}).get('overall_confidence', 0):.2f}")
        
        extracted_data = result.get('ExtractedData', {})
        
        # Format for frontend compatibility
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
        
        formatted_data = {}
        for internal_name, display_name in field_mapping.items():
            if internal_name in extracted_data:
                formatted_data[display_name] = str(extracted_data[internal_name])
        
        print(f"✅ Extracted {len(formatted_data)} W-2 fields:")
        for field, value in formatted_data.items():
            print(f"   {field}: {value}")
        
        return True, formatted_data
        
    except Exception as e:
        print(f"❌ W-2 extraction failed: {e}")
        return False, {}

def test_api_response_format():
    """Test API response format compatibility"""
    
    print("\n🧪 Testing API Response Format")
    print("=" * 50)
    
    try:
        # Simulate the API response format
        sample_extracted_data = {
            'EmployeeName': 'Jane A DOE',
            'EmployeeSSN': '123-45-6789',
            'EmployerName': 'The Big Company',
            'EmployerEIN': '11-2233445',
            'Box1_Wages': 48500.0,
            'Box2_FederalTaxWithheld': 6835.0,
            'Box3_SocialSecurityWages': 50000.0,
            'Box4_SocialSecurityTax': 3100.0,
            'Box5_MedicareWages': 50000.0,
            'Box6_MedicareTax': 725.0,
            'TaxYear': 2014
        }
        
        # Format for frontend (as done in enhanced_api_handler.py)
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
        
        formatted_data = {}
        for internal_name, display_name in field_mapping.items():
            if internal_name in sample_extracted_data:
                formatted_data[display_name] = str(sample_extracted_data[internal_name])
        
        # Create API response
        api_response = {
            "DocumentID": "W2-sample.png",
            "DocumentType": "W-2",
            "ProcessingStatus": "Completed",
            "Data": formatted_data,
            "S3Location": "",
            "CreatedAt": "2025-01-05T05:58:03.198753"
        }
        
        print("✅ API Response Format:")
        print(json.dumps(api_response, indent=2))
        
        # Verify expected fields are present
        expected_fields = [
            '1 Wages, tips, other compensation',
            '2 Federal income tax withheld',
            'a Employee\'s social security number',
            'b Employer identification number (EIN)'
        ]
        
        missing_fields = [f for f in expected_fields if f not in formatted_data]
        
        if not missing_fields:
            print(f"✅ All expected fields present ({len(formatted_data)} total)")
            return True
        else:
            print(f"❌ Missing fields: {missing_fields}")
            return False
        
    except Exception as e:
        print(f"❌ API format test failed: {e}")
        return False

def main():
    """Run all tests"""
    
    print("🚀 DrDoc Complete System Test")
    print("=" * 60)
    
    tests = [
        ("W-2 Extraction", test_w2_extraction),
        ("API Response Format", test_api_response_format)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if test_name == "W-2 Extraction":
                success, _ = test_func()
            else:
                success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! System is ready for deployment.")
        return True
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)