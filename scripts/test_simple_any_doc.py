#!/usr/bin/env python3
"""
Simple test for Any-Doc processor without libmagic dependency
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_with_existing_extractor():
    """Test using the existing multi-form extractor"""
    
    from services.multi_form_extractor import MultiFormExtractor
    
    extractor = MultiFormExtractor()
    images_dir = Path(__file__).parent.parent / 'images'
    
    test_files = [
        ('W2-sample.png', 'W-2'),
        ('1099-sample.png', '1099-NEC'),
        ('sample-walmart-receipt.webp', 'Receipt'),
        ('sample-invoive.jpeg', 'Invoice')
    ]
    
    print("🚀 Testing Multi-Form Extractor with Any-Doc approach")
    print("=" * 60)
    
    for filename, doc_type in test_files:
        file_path = images_dir / filename
        
        if not file_path.exists():
            print(f"⚠️  File not found: {filename}")
            continue
        
        print(f"\n📄 Processing: {filename} as {doc_type}")
        print("-" * 40)
        
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Test extraction
            result = extractor.extract_document_fields(file_bytes, doc_type)
            
            print(f"✅ Document Type: {result.get('DocumentType', 'Unknown')}")
            
            # Show metadata
            metadata = result.get('ExtractionMetadata', {})
            print(f"📊 Total Fields: {metadata.get('total_fields', 0)}")
            print(f"🎯 Overall Confidence: {metadata.get('overall_confidence', 0):.2f}")
            print(f"👁️  Needs Review: {metadata.get('needs_review', False)}")
            
            # Show some extracted data
            extracted_count = 0
            for key, value in result.items():
                if key not in ['DocumentType', 'ExtractionMetadata'] and value is not None:
                    print(f"   • {key}: {value}")
                    extracted_count += 1
                    if extracted_count >= 3:  # Show first 3 fields
                        break
            
            if extracted_count == 0:
                print("   No data extracted")
            elif len([k for k in result.keys() if k not in ['DocumentType', 'ExtractionMetadata']]) > 3:
                remaining = len([k for k in result.keys() if k not in ['DocumentType', 'ExtractionMetadata']]) - 3
                print(f"   ... and {remaining} more fields")
                
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 Multi-Form Extractor Test Complete")

if __name__ == "__main__":
    test_with_existing_extractor()