#!/usr/bin/env python3

import sys
import os
import json
import base64

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from handlers.enhanced_api_handler import process_document_enhanced

def test_w2_api_format():
    """Test the API response format for W-2 documents"""
    
    # Read the W-2 sample image
    image_path = "images/W2-sample.png"
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    # Encode as base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Create mock API Gateway event
    event = {
        'httpMethod': 'POST',
        'path': '/process-document',
        'body': json.dumps({
            'filename': 'W2-sample.png',
            'file_content': image_base64
        })
    }
    
    # Mock CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    print("Testing W-2 API response format...")
    
    try:
        # Call the API handler
        response = process_document_enhanced(event, cors_headers)
        
        print(f"Status Code: {response['statusCode']}")
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            
            print("\nAPI Response Structure:")
            print(f"DocumentID: {body.get('DocumentID')}")
            print(f"DocumentType: {body.get('DocumentType')}")
            print(f"ProcessingStatus: {body.get('ProcessingStatus')}")
            
            print("\nExtracted Data:")
            data = body.get('Data', {})
            for key, value in data.items():
                if not key.endswith('_source') and not key.endswith('_confidence'):
                    print(f"  {key}: {value}")
            
            print(f"\nTotal fields extracted: {len([k for k in data.keys() if not k.endswith('_source') and not k.endswith('_confidence')])}")
            
            # Check if we have the expected W-2 fields
            expected_fields = [
                '1 Wages, tips, other compensation',
                '2 Federal income tax withheld',
                'a Employee\'s social security number',
                'b Employer identification number (EIN)',
                'c Employer\'s name, address, and ZIP code',
                'e Employee\'s first name and initial'
            ]
            
            found_fields = []
            for field in expected_fields:
                if field in data:
                    found_fields.append(field)
            
            print(f"\nExpected W-2 fields found: {len(found_fields)}/{len(expected_fields)}")
            for field in found_fields:
                print(f"  ✅ {field}")
            
            missing_fields = [f for f in expected_fields if f not in data]
            if missing_fields:
                print("\nMissing fields:")
                for field in missing_fields:
                    print(f"  ❌ {field}")
            
            return True
        else:
            print(f"API call failed with status {response['statusCode']}")
            print(f"Error: {response.get('body')}")
            return False
            
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_w2_api_format()
    if success:
        print("\n✅ API format test PASSED")
    else:
        print("\n❌ API format test FAILED")
        sys.exit(1)