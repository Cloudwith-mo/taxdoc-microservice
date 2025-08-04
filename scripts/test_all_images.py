#!/usr/bin/env python3

import os
import requests
import time
from pathlib import Path

# Configuration
API_ENDPOINT = "https://n82datyqse.execute-api.us-east-1.amazonaws.com/prod"
UPLOAD_BUCKET = "taxdoc-uploads-prod-995805900737"
IMAGES_DIR = "/Users/muhammadadeyemi/Documents/microproc/images"

def upload_and_test_image(image_path):
    """Upload image to S3 and test processing"""
    print(f"\n🧪 Testing: {os.path.basename(image_path)}")
    
    try:
        # Upload to S3
        import boto3
        s3_client = boto3.client('s3')
        
        key = f"test-{int(time.time())}-{os.path.basename(image_path)}"
        
        with open(image_path, 'rb') as f:
            s3_client.upload_fileobj(f, UPLOAD_BUCKET, key)
        
        print(f"✅ Uploaded to S3: s3://{UPLOAD_BUCKET}/{key}")
        
        # Wait for processing
        time.sleep(5)
        
        # Check result via API
        doc_id = os.path.splitext(key)[0]
        result_url = f"{API_ENDPOINT}/result/{doc_id}"
        
        response = requests.get(result_url)
        if response.status_code == 200:
            result = response.json()
            doc_type = result.get('DocumentType', 'Unknown')
            data_fields = len(result.get('Data', {}))
            
            print(f"📋 Document Type: {doc_type}")
            print(f"📊 Fields Extracted: {data_fields}")
            
            # Show W-2 specific results
            if doc_type == "W-2 Tax Form":
                data = result.get('Data', {})
                validation = data.get('_validation', {})
                completeness = validation.get('completeness_score', 0)
                conflicts = validation.get('conflicts_detected', 0)
                
                print(f"🎯 Completeness: {completeness:.1%}")
                print(f"⚠️  Conflicts: {conflicts}")
                
                # Show key fields
                key_fields = ['EmployeeName', 'Box1_Wages', 'Box2_FederalTaxWithheld', 'TaxYear']
                for field in key_fields:
                    if field in data:
                        print(f"   {field}: {data[field]}")
            
            return True
        else:
            print(f"❌ API Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test all images in the images directory"""
    print("🚀 Testing All Images in Production Environment")
    print(f"📁 Images Directory: {IMAGES_DIR}")
    print(f"🔗 API Endpoint: {API_ENDPOINT}")
    
    # Get all image files
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif'}
    image_files = []
    
    for file_path in Path(IMAGES_DIR).iterdir():
        if file_path.suffix.lower() in image_extensions:
            image_files.append(str(file_path))
    
    print(f"📊 Found {len(image_files)} image files to test")
    
    # Test each image
    results = {}
    for image_path in sorted(image_files):
        success = upload_and_test_image(image_path)
        results[os.path.basename(image_path)] = success
        time.sleep(2)  # Rate limiting
    
    # Summary
    print("\n" + "="*50)
    print("📋 TEST SUMMARY")
    print("="*50)
    
    successful = sum(results.values())
    total = len(results)
    
    for filename, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {filename}")
    
    print(f"\n🎯 Success Rate: {successful}/{total} ({successful/total:.1%})")
    
    if successful == total:
        print("🎉 All images processed successfully!")
    else:
        print("⚠️  Some images failed processing - check logs above")

if __name__ == "__main__":
    main()