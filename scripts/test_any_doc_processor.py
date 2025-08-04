#!/usr/bin/env python3
"""
Test script for the Any-Doc processor
Tests the complete pipeline with various document types
"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.any_doc_processor import AnyDocProcessor

def test_any_doc_processor():
    """Test the Any-Doc processor with sample documents"""
    
    processor = AnyDocProcessor()
    
    # Test images directory
    images_dir = Path(__file__).parent.parent / 'images'
    
    if not images_dir.exists():
        print(f"❌ Images directory not found: {images_dir}")
        return
    
    # Test files
    test_files = [
        'W2-sample.png',
        '1099-sample.png',
        'Sample-BankStatementChequing.png',
        'sample-invoive.jpeg',
        'sample-walmart-receipt.webp'
    ]
    
    print("🚀 Testing Any-Doc Processor")
    print("=" * 50)
    
    for filename in test_files:
        file_path = images_dir / filename
        
        if not file_path.exists():
            print(f"⚠️  File not found: {filename}")
            continue
        
        print(f"\n📄 Processing: {filename}")
        print("-" * 30)
        
        try:
            # Read file
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
            
            # Process document
            result = processor.process_document(file_bytes, filename)
            
            # Display results
            print(f"✅ Document Type: {result.get('DocumentType', 'Unknown')}")
            print(f"📊 Overall Confidence: {result.get('QualityMetrics', {}).get('overall_confidence', 0):.2f}")
            print(f"🔍 File Type: {result.get('ProcessingMetadata', {}).get('file_type', 'Unknown')}")
            print(f"🎯 Template Match: {result.get('ProcessingMetadata', {}).get('template_match', 'None')}")
            print(f"⚙️  Extraction Strategy: {result.get('ProcessingMetadata', {}).get('extraction_strategy', 'Unknown')}")
            
            # Show extracted data count
            extracted_data = result.get('ExtractedData', {})
            if extracted_data:
                print(f"📋 Extracted Fields: {len(extracted_data)}")
                for key, value in list(extracted_data.items())[:3]:  # Show first 3 fields
                    print(f"   • {key}: {value}")
                if len(extracted_data) > 3:
                    print(f"   ... and {len(extracted_data) - 3} more fields")
            else:
                print("📋 No structured data extracted")
            
            # Review recommendation
            needs_review = result.get('QualityMetrics', {}).get('needs_human_review', False)
            print(f"👁️  Needs Review: {'Yes' if needs_review else 'No'}")
            
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 Any-Doc Processor Test Complete")

def test_supported_types():
    """Test supported file types endpoint"""
    
    print("\n🔍 Testing Supported File Types")
    print("-" * 30)
    
    try:
        processor = AnyDocProcessor()
        supported_types = processor.get_supported_file_types()
        
        print(f"✅ Total supported types: {len(supported_types)}")
        for mime_type in supported_types:
            print(f"   • {mime_type}")
            
    except Exception as e:
        print(f"❌ Failed to get supported types: {str(e)}")

def test_batch_processing():
    """Test batch processing functionality"""
    
    print("\n📦 Testing Batch Processing")
    print("-" * 30)
    
    processor = AnyDocProcessor()
    images_dir = Path(__file__).parent.parent / 'images'
    
    # Prepare batch files
    batch_files = []
    test_files = ['W2-sample.png', '1099-sample.png']
    
    for i, filename in enumerate(test_files):
        file_path = images_dir / filename
        if file_path.exists():
            with open(file_path, 'rb') as f:
                batch_files.append({
                    'id': f'batch_{i}',
                    'filename': filename,
                    'bytes': f.read()
                })
    
    if not batch_files:
        print("⚠️  No files available for batch testing")
        return
    
    try:
        results = processor.process_batch(batch_files)
        
        print(f"✅ Batch processed {len(results)} documents")
        for i, result in enumerate(results):
            doc_type = result.get('DocumentType', 'Unknown')
            confidence = result.get('QualityMetrics', {}).get('overall_confidence', 0)
            print(f"   {i+1}. {doc_type} (confidence: {confidence:.2f})")
            
    except Exception as e:
        print(f"❌ Batch processing failed: {str(e)}")

if __name__ == "__main__":
    test_any_doc_processor()
    test_supported_types()
    test_batch_processing()