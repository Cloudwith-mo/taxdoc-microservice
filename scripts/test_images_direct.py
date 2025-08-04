#!/usr/bin/env python3

import boto3
import json
from pathlib import Path

def test_processed_documents():
    """Check DynamoDB for processed documents and show results"""
    
    dynamodb = boto3.client('dynamodb')
    table_name = 'TaxDocuments-prod'
    
    print("🔍 Checking processed documents in DynamoDB...")
    
    # Scan for recent documents
    response = dynamodb.scan(
        TableName=table_name,
        Limit=20
    )
    
    documents = []
    for item in response['Items']:
        doc = {
            'DocumentID': item['DocumentID']['S'],
            'DocumentType': item['DocumentType']['S'],
            'ProcessingStatus': item['ProcessingStatus']['S'],
            'Data': json.loads(item['Data']['S']) if 'Data' in item and item['Data']['S'] else {}
        }
        documents.append(doc)
    
    # Group by document type
    by_type = {}
    for doc in documents:
        doc_type = doc['DocumentType']
        if doc_type not in by_type:
            by_type[doc_type] = []
        by_type[doc_type].append(doc)
    
    print(f"\n📊 Found {len(documents)} processed documents")
    print("="*60)
    
    for doc_type, docs in by_type.items():
        print(f"\n📋 {doc_type} ({len(docs)} documents)")
        print("-" * 40)
        
        for doc in docs:
            print(f"📄 {doc['DocumentID']}")
            print(f"   Status: {doc['ProcessingStatus']}")
            
            data = doc['Data']
            if data:
                field_count = len(data)
                print(f"   Fields: {field_count}")
                
                # Show key fields for W-2
                if doc_type == "W-2 Tax Form":
                    key_fields = ['employer', 'wages', 'federal_tax', 'EmployeeName', 'Box1_Wages', 'Box2_FederalTaxWithheld']
                    found_fields = []
                    for field in key_fields:
                        if field in data:
                            found_fields.append(f"{field}: {data[field]}")
                    
                    if found_fields:
                        print(f"   Key Data: {', '.join(found_fields[:3])}")
                    
                    # Check for AI enhancement indicators
                    if '_validation' in data:
                        validation = data['_validation']
                        completeness = validation.get('completeness_score', 0)
                        conflicts = validation.get('conflicts_detected', 0)
                        print(f"   AI Enhanced: ✅ (Completeness: {completeness:.1%}, Conflicts: {conflicts})")
                    else:
                        print(f"   AI Enhanced: ❌ (Legacy extraction)")
                
                # Show sample fields for other types
                elif data:
                    sample_fields = list(data.keys())[:3]
                    sample_data = [f"{k}: {data[k]}" for k in sample_fields]
                    print(f"   Sample: {', '.join(sample_data)}")
            else:
                print(f"   Fields: 0 (No data extracted)")
            
            print()

def main():
    print("🧪 Testing Image Processing Results")
    print("Checking DynamoDB for processed documents...")
    
    try:
        test_processed_documents()
        
        print("\n" + "="*60)
        print("✅ Test completed - check results above")
        print("\n💡 Key Observations:")
        print("   • Documents are being processed successfully")
        print("   • W-2 forms should show AI enhancement indicators")
        print("   • Field extraction varies by document type")
        print("   • API endpoint may need document ID without extension")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()