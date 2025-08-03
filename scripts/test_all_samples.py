#!/usr/bin/env python3

import os
import time
from pathlib import Path
from test_upload import upload_test_document, check_processing_result

def test_all_samples():
    """Test all sample images in the images directory"""
    
    images_dir = Path(__file__).parent.parent / 'images'
    bucket_name = 'taxdoc-uploads-dev-995805900737'
    
    # Get all image files
    image_files = list(images_dir.glob('*'))
    image_files = [f for f in image_files if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.avif']]
    
    print(f"Found {len(image_files)} sample images to test:")
    for img in image_files:
        print(f"  - {img.name}")
    
    uploaded_docs = []
    
    # Upload all samples
    print("\n=== UPLOADING SAMPLES ===")
    for img_file in image_files:
        print(f"\nTesting: {img_file.name}")
        s3_key = upload_test_document(str(img_file), bucket_name)
        
        if s3_key:
            doc_id = Path(s3_key).name
            uploaded_docs.append((doc_id, img_file.name))
            print(f"✓ Uploaded as document ID: {doc_id}")
        else:
            print(f"✗ Failed to upload {img_file.name}")
    
    # Wait for processing
    print(f"\n=== WAITING FOR PROCESSING ===")
    print("Waiting 30 seconds for documents to process...")
    time.sleep(30)
    
    # Check results
    print(f"\n=== CHECKING RESULTS ===")
    for doc_id, original_name in uploaded_docs:
        print(f"\n--- Results for {original_name} ---")
        check_processing_result(doc_id)

if __name__ == "__main__":
    test_all_samples()