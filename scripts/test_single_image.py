#!/usr/bin/env python3

import sys
from pathlib import Path
from test_upload import upload_test_document, check_processing_result
import time

def test_single_image(image_name):
    """Test a single image from the images directory"""
    
    images_dir = Path(__file__).parent.parent / 'images'
    image_path = images_dir / image_name
    
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        print("Available images:")
        for img in images_dir.glob('*'):
            if img.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.avif']:
                print(f"  - {img.name}")
        return
    
    bucket_name = 'taxdoc-uploads-dev-995805900737'
    
    print(f"Testing image: {image_name}")
    s3_key = upload_test_document(str(image_path), bucket_name)
    
    if s3_key:
        doc_id = Path(s3_key).name
        print(f"Document ID: {doc_id}")
        
        # Wait and check result
        print("Waiting 15 seconds for processing...")
        time.sleep(15)
        
        print("\nChecking result:")
        check_processing_result(doc_id)
    else:
        print("Upload failed")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_single_image.py <image_name>")
        print("Example: python test_single_image.py W2-sample.png")
        sys.exit(1)
    
    image_name = sys.argv[1]
    test_single_image(image_name)