#!/usr/bin/env python3
"""
Test the chatbot functionality locally
"""
import json
import sys
import os

# Set AWS region for boto3
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Add src/handlers to path
sys.path.insert(0, '/workspace/src/handlers')

def test_chat_facts_handler():
    """Test the chat_facts_handler locally"""
    print("Testing chat_facts_handler...")
    
    # Import the handler
    try:
        from chat_facts_handler import lambda_handler
        print("✓ Handler imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import handler: {e}")
        return False
    
    # Test with a simple message
    test_event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'user_id': 'test_user',
            'message': 'What are my wages?'
        })
    }
    
    try:
        response = lambda_handler(test_event, {})
        print(f"✓ Handler executed successfully")
        print(f"  Response status: {response['statusCode']}")
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            print(f"  Response message: {body.get('response', 'No response')[:100]}...")
            return True
        else:
            print(f"  Error response: {response['body']}")
            return False
            
    except Exception as e:
        print(f"✗ Handler execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chatbot_service():
    """Test the chatbot service directly"""
    print("\nTesting chatbot_service...")
    
    try:
        from chatbot_service import ChatbotService
        print("✓ ChatbotService imported successfully")
        
        # Create service instance
        service = ChatbotService()
        
        # Test simple Q&A
        test_questions = [
            "What is a W-2 form?",
            "How accurate is the extraction?",
            "What should I do next?"
        ]
        
        for question in test_questions:
            print(f"\n  Q: {question}")
            try:
                response = service.chat(question)
                answer = response.get('answer', 'No answer')
                print(f"  A: {answer[:100]}...")
                print(f"  Confidence: {response.get('confidence', 0)}")
            except Exception as e:
                print(f"  Error: {e}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import ChatbotService: {e}")
        return False
    except Exception as e:
        print(f"✗ ChatbotService test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("CHATBOT FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Change to handlers directory
    os.chdir('/workspace/src/handlers')
    
    # Test chat_facts_handler
    chat_facts_ok = test_chat_facts_handler()
    
    # Test chatbot_service
    os.chdir('/workspace/src/services')
    chatbot_service_ok = test_chatbot_service()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"chat_facts_handler: {'✓ PASS' if chat_facts_ok else '✗ FAIL'}")
    print(f"chatbot_service: {'✓ PASS' if chatbot_service_ok else '✗ FAIL'}")
    
    if chat_facts_ok and chatbot_service_ok:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())