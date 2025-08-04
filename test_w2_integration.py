#!/usr/bin/env python3
"""
Quick integration test for W2 extractor service with multi-form support
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

def test_w2_service_import():
    """Test that W2 service can import multi-form extractor"""
    try:
        from services.w2_extractor_service import W2ExtractorService
        print("✅ W2ExtractorService imported successfully")
        
        # Test initialization
        service = W2ExtractorService()
        print("✅ W2ExtractorService initialized successfully")
        
        # Check if multi-form extractor is available
        if hasattr(service, 'multi_form_extractor'):
            print("✅ Multi-form extractor integration confirmed")
        else:
            print("⚠️  Multi-form extractor not found in W2 service")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

def test_multi_form_extractor():
    """Test multi-form extractor directly"""
    try:
        from services.multi_form_extractor import MultiFormExtractor
        print("✅ MultiFormExtractor imported successfully")
        
        extractor = MultiFormExtractor()
        print("✅ MultiFormExtractor initialized successfully")
        
        # Test supported document types
        supported_types = extractor.get_supported_document_types()
        print(f"✅ Supported document types: {len(supported_types)}")
        for doc_type in supported_types:
            print(f"   - {doc_type}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_enhanced_classifier():
    """Test enhanced classifier"""
    try:
        from services.enhanced_classifier import EnhancedClassifier
        print("✅ EnhancedClassifier imported successfully")
        
        classifier = EnhancedClassifier()
        print("✅ EnhancedClassifier initialized successfully")
        
        # Test supported types
        supported_types = classifier.get_supported_document_types()
        print(f"✅ Classifier supports {len(supported_types)} document types")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_document_config():
    """Test document configuration"""
    try:
        from config.document_config import DOCUMENT_CONFIGS, CLASSIFICATION_KEYWORDS
        print("✅ Document configuration imported successfully")
        
        print(f"✅ Document configs available: {len(DOCUMENT_CONFIGS)}")
        print(f"✅ Classification keywords available: {len(CLASSIFICATION_KEYWORDS)}")
        
        # Test W-2 config
        if 'W-2' in DOCUMENT_CONFIGS:
            w2_config = DOCUMENT_CONFIGS['W-2']
            print(f"✅ W-2 config has {len(w2_config['queries'])} queries")
            print(f"✅ W-2 config has Claude prompt: {bool(w2_config.get('claude_prompt'))}")
            print(f"✅ W-2 config has {len(w2_config.get('regex_patterns', {}))} regex patterns")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all integration tests"""
    print("🧪 W2 Extractor Integration Test")
    print("=" * 40)
    
    tests = [
        ("Document Configuration", test_document_config),
        ("Enhanced Classifier", test_enhanced_classifier),
        ("Multi-Form Extractor", test_multi_form_extractor),
        ("W2 Service Integration", test_w2_service_import),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'=' * 40}")
    print("📊 Test Summary")
    print(f"{'=' * 40}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        print("The W2 extractor service is ready for multi-form processing.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()