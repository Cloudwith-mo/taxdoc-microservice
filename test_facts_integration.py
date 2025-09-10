#!/usr/bin/env python3
"""Test script to verify facts integration end-to-end"""

import json
import boto3
from src.handlers.facts_publisher import publish_facts

def test_facts_integration():
    """Test the complete facts integration flow"""
    
    # Sample processed document data
    sample_doc = {
        'docId': 'test-doc-123',
        'docType': 'W-2',
        'filename': 'test-w2.pdf',
        'fields': {
            'Employee Name': 'John Doe',
            'Employer EIN': '12-3456789',
            'Box 1 - Wages': '$50,000.00',
            'Box 2 - Federal Tax': '$7,500.00'
        },
        'docTypeConfidence': 0.95
    }
    
    # Test 1: Publish facts
    print("Testing facts publishing...")
    try:
        facts_count = publish_facts('test-user', 'test-doc-123', sample_doc)
        print(f"✅ Published {facts_count} facts successfully")
    except Exception as e:
        print(f"❌ Facts publishing failed: {e}")
        return
    
    # Test 2: Query facts via Lambda
    print("\nTesting chat facts handler...")
    lambda_client = boto3.client('lambda')
    
    test_payload = {
        'body': json.dumps({
            'user_id': 'test-user',
            'message': 'employee name'
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='parsepilot-chat-facts',
            Payload=json.dumps(test_payload)
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result['body'])
        print(f"✅ Chat response: {body['response']}")
        
    except Exception as e:
        print(f"❌ Chat query failed: {e}")
    
    # Test 3: Stats query
    print("\nTesting stats query...")
    stats_payload = {
        'body': json.dumps({
            'user_id': 'test-user', 
            'message': 'stats'
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='parsepilot-chat-facts',
            Payload=json.dumps(stats_payload)
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result['body'])
        print(f"✅ Stats response: {body['response']}")
        
    except Exception as e:
        print(f"❌ Stats query failed: {e}")

if __name__ == '__main__':
    test_facts_integration()