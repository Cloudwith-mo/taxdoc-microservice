#!/usr/bin/env python3

import sys
import os
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.three_layer_orchestrator import ThreeLayerOrchestrator

def test_w2_format():
    """Test the W-2 extraction format"""
    
    # Read the W-2 sample image
    image_path = "images/W2-sample.png"
    with open(image_path, 'rb') as f:
        document_bytes = f.read()
    
    print("Testing W-2 extraction format...")
    
    try:
        # Use the orchestrator directly
        orchestrator = ThreeLayerOrchestrator()
        result = orchestrator.extract_document_fields(document_bytes, "W-2")
        
        print(f"Document Type: {result.get('DocumentType')}")
        
        extracted_data = result.get('ExtractedData', {})
        print(f"\nExtracted Data ({len(extracted_data)} fields):")
        
        # Show the raw extracted data
        for key, value in extracted_data.items():
            if not key.endswith('_source') and not key.endswith('_confidence'):
                print(f"  {key}: {value}")
        
        # Now show how it would be formatted for frontend
        print("\n" + "="*50)
        print("FRONTEND FORMAT MAPPING:")
        print("="*50)
        
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
                print(f"  {internal_name} → {display_name}: {extracted_data[internal_name]}")
        
        print(f"\nFormatted data has {len(formatted_data)} fields")
        
        # Show what the API would return
        print("\n" + "="*50)
        print("API RESPONSE FORMAT:")
        print("="*50)
        
        api_response = {
            "DocumentID": "W2-sample.png",
            "DocumentType": "W-2",
            "ProcessingStatus": "Completed",
            "Data": formatted_data,
            "S3Location": "",
            "CreatedAt": "2025-01-05T05:58:03.198753"
        }
        
        print(json.dumps(api_response, indent=2))
        
        return True
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_w2_format()
    if success:
        print("\n✅ Format test PASSED")
    else:
        print("\n❌ Format test FAILED")
        sys.exit(1)