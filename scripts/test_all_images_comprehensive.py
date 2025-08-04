#!/usr/bin/env python3
"""
Comprehensive Image Testing Script
Tests all images in the images directory and compares with expected results
"""

import boto3
import json
import time
import os
import sys
from typing import Dict, Any, List

class ImageTester:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        self.bucket = "taxdoc-uploads-dev-995805900737"
        self.table = self.dynamodb.Table("TaxDocuments-dev")
        
        # Expected results for each image
        self.expected_results = {
            "W2-sample.png": {
                "document_type": "W-2",
                "key_fields": ["EmployeeName", "EmployeeSSN", "EmployerName", "Box1_Wages", "Box2_FederalTaxWithheld"],
                "min_confidence": 0.7,
                "min_completeness": 0.6
            },
            "w2.gif": {
                "document_type": "W-2", 
                "key_fields": ["EmployeeName", "EmployerName", "Box1_Wages"],
                "min_confidence": 0.6,
                "min_completeness": 0.5
            },
            "1099-sample.png": {
                "document_type": "1099-NEC",
                "key_fields": ["PayerName", "RecipientName", "Box1_NonemployeeComp"],
                "min_confidence": 0.7,
                "min_completeness": 0.6
            },
            "sample-1099.avif": {
                "document_type": "1099-NEC",
                "key_fields": ["PayerName", "RecipientName"],
                "min_confidence": 0.6,
                "min_completeness": 0.4
            },
            "Sample-BankStatementChequing.png": {
                "document_type": "Bank Statement",
                "key_fields": ["AccountHolder", "BeginningBalance", "EndingBalance"],
                "min_confidence": 0.6,
                "min_completeness": 0.5
            },
            "IC-Basic-Receipt-Template.png": {
                "document_type": "Receipt",
                "key_fields": ["MerchantName", "TotalAmount"],
                "min_confidence": 0.6,
                "min_completeness": 0.4
            },
            "sample-repair-receipt.jpg": {
                "document_type": "Receipt",
                "key_fields": ["MerchantName", "TotalAmount"],
                "min_confidence": 0.5,
                "min_completeness": 0.3
            },
            "sample-walmart-receipt.webp": {
                "document_type": "Receipt", 
                "key_fields": ["MerchantName", "TotalAmount"],
                "min_confidence": 0.5,
                "min_completeness": 0.3
            },
            "sample-invoive.jpeg": {
                "document_type": "Invoice",
                "key_fields": ["VendorName", "TotalAmount"],
                "min_confidence": 0.6,
                "min_completeness": 0.4
            }
        }
    
    def test_all_images(self):
        """Test all images and compare with expected results"""
        print("🧪 Testing All Images in /images Directory")
        print("=" * 60)
        
        results = {}
        images_dir = "/Users/muhammadadeyemi/Documents/microproc/images"
        
        for filename in os.listdir(images_dir):
            if filename.startswith('.'):
                continue
                
            filepath = os.path.join(images_dir, filename)
            print(f"\n📄 Testing: {filename}")
            
            try:
                result = self.test_single_image(filepath, filename)
                results[filename] = result
                self.print_result_summary(filename, result)
            except Exception as e:
                print(f"❌ Error testing {filename}: {e}")
                results[filename] = {"error": str(e)}
        
        # Overall summary
        self.print_overall_summary(results)
        return results
    
    def test_single_image(self, filepath: str, filename: str) -> Dict[str, Any]:
        """Test a single image"""
        # Upload to S3 with correct prefix for trigger
        s3_key = f"incoming/{filename}_{int(time.time())}"
        self.s3_client.upload_file(filepath, self.bucket, s3_key)
        
        # Wait for processing
        time.sleep(15)
        
        # Get results from DynamoDB
        doc_id = s3_key.split('/')[-1]
        response = self.table.get_item(Key={'DocumentID': doc_id})
        
        if 'Item' not in response:
            return {"status": "not_processed", "doc_id": doc_id}
        
        item = response['Item']
        
        # Extract key metrics
        result = {
            "doc_id": doc_id,
            "status": item.get('ProcessingStatus', 'Unknown'),
            "document_type": item.get('DocumentType', 'Unknown'),
            "classification_confidence": float(item.get('ClassificationConfidence', 0)),
            "data": item.get('Data', {}),
            "extraction_metadata": item.get('ExtractionMetadata', {})
        }
        
        # Cleanup
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=s3_key)
        except:
            pass
            
        return result
    
    def print_result_summary(self, filename: str, result: Dict[str, Any]):
        """Print summary for a single result"""
        if "error" in result:
            print(f"   ❌ ERROR: {result['error']}")
            return
            
        if result["status"] != "Completed":
            print(f"   ⚠️  Status: {result['status']}")
            return
        
        expected = self.expected_results.get(filename, {})
        
        # Check document type
        actual_type = result["document_type"]
        expected_type = expected.get("document_type", "Unknown")
        type_match = actual_type == expected_type
        
        print(f"   📋 Document Type: {actual_type} {'✅' if type_match else '❌'} (expected: {expected_type})")
        print(f"   🎯 Classification Confidence: {result['classification_confidence']:.2f}")
        
        # Check field extraction
        data = result["data"]
        metadata = result.get("extraction_metadata", {})
        
        if expected.get("key_fields"):
            found_fields = sum(1 for field in expected["key_fields"] if field in data and data[field])
            total_fields = len(expected["key_fields"])
            completeness = found_fields / total_fields if total_fields > 0 else 0
            
            print(f"   📊 Key Fields Found: {found_fields}/{total_fields} ({completeness:.1%})")
            
            # Show which fields were found/missing
            for field in expected["key_fields"]:
                if field in data and data[field]:
                    confidence = metadata.get("confidence_scores", {}).get(field, 0)
                    source = metadata.get("field_sources", {}).get(field, "unknown")
                    print(f"      ✅ {field}: {data[field]} (conf: {confidence:.2f}, src: {source})")
                else:
                    print(f"      ❌ {field}: Missing")
        
        # Overall assessment
        avg_confidence = metadata.get("average_confidence", 0)
        completeness_score = metadata.get("completeness_score", 0)
        needs_review = metadata.get("needs_review", False)
        
        print(f"   📈 Avg Confidence: {avg_confidence:.2f}")
        print(f"   📋 Completeness: {completeness_score:.1%}")
        print(f"   🔍 Needs Review: {'Yes' if needs_review else 'No'}")
        
        # Pass/Fail assessment
        min_conf = expected.get("min_confidence", 0.5)
        min_comp = expected.get("min_completeness", 0.3)
        
        passed = (
            type_match and 
            avg_confidence >= min_conf and 
            completeness_score >= min_comp
        )
        
        print(f"   🎯 Overall: {'✅ PASS' if passed else '❌ FAIL'}")
    
    def print_overall_summary(self, results: Dict[str, Any]):
        """Print overall test summary"""
        print("\n" + "=" * 60)
        print("📊 OVERALL TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results.values() if r.get("status") == "Completed")
        
        print(f"Total Images Tested: {total_tests}")
        print(f"Successfully Processed: {successful_tests}")
        print(f"Success Rate: {successful_tests/total_tests:.1%}")
        
        # Document type accuracy
        correct_classifications = 0
        for filename, result in results.items():
            if result.get("status") == "Completed":
                expected_type = self.expected_results.get(filename, {}).get("document_type")
                actual_type = result.get("document_type")
                if expected_type == actual_type:
                    correct_classifications += 1
        
        if successful_tests > 0:
            classification_accuracy = correct_classifications / successful_tests
            print(f"Classification Accuracy: {classification_accuracy:.1%}")
        
        # Identify gaps
        print("\n🔍 IDENTIFIED GAPS:")
        gaps = []
        
        for filename, result in results.items():
            if "error" in result:
                gaps.append(f"❌ {filename}: Processing error - {result['error']}")
            elif result.get("status") != "Completed":
                gaps.append(f"⚠️  {filename}: Not processed - {result.get('status', 'Unknown')}")
            else:
                expected = self.expected_results.get(filename, {})
                actual_type = result.get("document_type")
                expected_type = expected.get("document_type")
                
                if actual_type != expected_type:
                    gaps.append(f"🔄 {filename}: Wrong classification - got {actual_type}, expected {expected_type}")
                
                metadata = result.get("extraction_metadata", {})
                avg_conf = metadata.get("average_confidence", 0)
                completeness = metadata.get("completeness_score", 0)
                
                if avg_conf < expected.get("min_confidence", 0.5):
                    gaps.append(f"📉 {filename}: Low confidence - {avg_conf:.2f}")
                
                if completeness < expected.get("min_completeness", 0.3):
                    gaps.append(f"📊 {filename}: Low completeness - {completeness:.1%}")
        
        if gaps:
            for gap in gaps:
                print(f"   {gap}")
        else:
            print("   🎉 No significant gaps identified!")
        
        return len(gaps) == 0

if __name__ == "__main__":
    tester = ImageTester()
    results = tester.test_all_images()
    
    # Exit with error if tests failed
    if not all(r.get("status") == "Completed" for r in results.values()):
        sys.exit(1)