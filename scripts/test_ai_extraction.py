#!/usr/bin/env python3
"""
Test AI Extraction for TaxDoc MVP
Verifies that Claude AI is properly extracting comprehensive W-2 data
"""

import json
import base64
import requests
import sys
import os

def test_ai_extraction():
    """Test AI extraction with a sample W-2 image"""
    
    # Get API endpoint from CloudFormation
    import boto3
    
    try:
        cf = boto3.client('cloudformation', region_name='us-east-1')
        response = cf.describe_stacks(StackName='TaxDoc-MVP')
        
        api_endpoint = None
        for output in response['Stacks'][0]['Outputs']:
            if output['OutputKey'] == 'ApiEndpoint':
                api_endpoint = output['OutputValue']
                break
        
        if not api_endpoint:
            print("❌ Could not find API endpoint")
            return False
            
    except Exception as e:
        print(f"❌ Error getting API endpoint: {e}")
        return False
    
    # Test with sample W-2 image
    sample_image_path = "images/w2_sample.png"
    
    if not os.path.exists(sample_image_path):
        print(f"❌ Sample image not found: {sample_image_path}")
        print("Please ensure you have a W-2 sample image for testing")
        return False
    
    # Read and encode image
    try:
        with open(sample_image_path, 'rb') as f:
            image_data = f.read()
        
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
    except Exception as e:
        print(f"❌ Error reading image: {e}")
        return False
    
    # Make API request
    print("🧪 Testing AI extraction...")
    print(f"API Endpoint: {api_endpoint}")
    
    payload = {
        "filename": "test_w2.png",
        "file_content": encoded_image
    }
    
    try:
        response = requests.post(
            f"{api_endpoint}/process-document",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ API request successful")
            print(f"Document Type: {result.get('document_type', 'Unknown')}")
            
            extracted_data = result.get('extracted_data', {})
            
            # Check if we got comprehensive W-2 data (not just fallback)
            expected_fields = [
                'employee_ssn', 'employer_ein', 'wages_income', 
                'federal_withheld', 'social_security_wages', 'medicare_wages',
                'employee_first_name', 'employee_last_name', 'employer_name'
            ]
            
            found_fields = [field for field in expected_fields if extracted_data.get(field)]
            extraction_method = extracted_data.get('extraction_method', 'unknown')
            
            print(f"\n📊 Extraction Results:")
            print(f"Method: {extraction_method}")
            print(f"Fields extracted: {len(found_fields)}/{len(expected_fields)}")
            
            if extraction_method == 'fallback_regex':
                print("⚠️  WARNING: Using fallback regex extraction (AI disabled)")
                print("This means Claude API key is not working properly")
                return False
            elif len(found_fields) >= 6:
                print("✅ AI extraction working - comprehensive data extracted")
                print("\nSample extracted fields:")
                for field in found_fields[:5]:
                    value = extracted_data.get(field)
                    print(f"  {field}: {value}")
                return True
            else:
                print("⚠️  Limited data extracted - possible AI issue")
                return False
                
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error making API request: {e}")
        return False

if __name__ == "__main__":
    print("🤖 TaxDoc AI Extraction Test")
    print("============================")
    
    success = test_ai_extraction()
    
    if success:
        print("\n🎉 AI extraction is working properly!")
        print("Your system is ready for comprehensive document processing.")
    else:
        print("\n❌ AI extraction needs attention")
        print("Please check:")
        print("1. Claude API key is valid and set")
        print("2. Lambda function has the API key in environment variables")
        print("3. No API rate limits or errors")
        
    sys.exit(0 if success else 1)