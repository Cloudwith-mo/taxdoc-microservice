#!/usr/bin/env python3
"""
Test script for tax-focused document processing system
"""
import base64
import requests
import json

def test_tax_system():
    """Test the tax-focused API"""
    
    # Test data - simple text that should be classified as W-2
    test_content = """
    W-2 Wage and Tax Statement
    Employee: John Doe
    SSN: 123-45-6789
    Employer: ABC Company
    EIN: 12-3456789
    Wages: $50,000
    Federal Tax Withheld: $5,000
    """
    
    # Encode as base64
    encoded_content = base64.b64encode(test_content.encode()).decode()
    
    # API endpoint
    api_url = "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod"
    
    print("🧪 Testing Tax Edition API...")
    
    # Test 1: Supported types
    print("\n1. Testing supported types endpoint...")
    try:
        response = requests.get(f"{api_url}/supported-types")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Supported types: {data}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Process tax document
    print("\n2. Testing document processing...")
    try:
        payload = {
            "filename": "test-w2.txt",
            "file_content": encoded_content
        }
        
        response = requests.post(
            f"{api_url}/process-document",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Document Type: {result.get('DocumentType', 'Unknown')}")
            print(f"Processing Status: {result.get('ProcessingStatus', 'Unknown')}")
            print(f"Data Fields: {len(result.get('Data', {}))}")
        elif response.status_code == 400:
            error_data = response.json()
            if error_data.get('error') == 'Unsupported Document (Tax Edition)':
                print("✅ Tax-only validation working!")
                print(f"Message: {error_data.get('message')}")
                print(f"Supported forms: {error_data.get('supported_forms')}")
            else:
                print(f"Error: {error_data}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 3: Test with unsupported document
    print("\n3. Testing unsupported document rejection...")
    try:
        unsupported_content = """
        INVOICE
        Invoice #: 12345
        Date: 2024-01-01
        Amount: $100.00
        """
        
        encoded_unsupported = base64.b64encode(unsupported_content.encode()).decode()
        
        payload = {
            "filename": "invoice.txt",
            "file_content": encoded_unsupported
        }
        
        response = requests.post(
            f"{api_url}/process-document",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            error_data = response.json()
            if error_data.get('error') == 'Unsupported Document (Tax Edition)':
                print("✅ Successfully rejected non-tax document!")
                print(f"Message: {error_data.get('message')}")
            else:
                print(f"Unexpected error: {error_data}")
        else:
            print(f"Unexpected success: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_tax_system()