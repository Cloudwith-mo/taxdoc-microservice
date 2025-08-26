#!/usr/bin/env python3
"""
Test script for Stripe webhook functionality
Tests webhook endpoint, payment processing, and subscription management
"""

import json
import requests
import time
import hashlib
import hmac
from datetime import datetime

# Configuration
API_BASE = "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod"
WEBHOOK_ENDPOINT = f"{API_BASE}/stripe-webhook"
WEBHOOK_SECRET = "whsec_test_secret"  # Test webhook secret

def create_stripe_signature(payload, secret):
    """Create a test Stripe signature"""
    timestamp = str(int(time.time()))
    signed_payload = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"

def test_webhook_endpoint():
    """Test the Stripe webhook endpoint"""
    print("🧪 Testing Stripe Webhook Endpoint...")
    
    # Test payment success webhook
    payment_payload = {
        "id": "evt_test_webhook",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test123456",
                "amount": 2900,  # $29.00
                "currency": "usd",
                "customer": "cus_test123",
                "metadata": {
                    "user_email": "test@example.com",
                    "plan": "starter"
                }
            }
        },
        "created": int(time.time())
    }
    
    payload_str = json.dumps(payment_payload)
    signature = create_stripe_signature(payload_str, WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": signature,
        "User-Agent": "Stripe/1.0 (+https://stripe.com/docs/webhooks)"
    }
    
    try:
        response = requests.post(
            WEBHOOK_ENDPOINT,
            data=payload_str,
            headers=headers,
            timeout=10
        )
        
        print(f"✅ Webhook Response: {response.status_code}")
        print(f"📄 Response Body: {response.text}")
        
        if response.status_code == 200:
            print("🎉 Webhook test successful!")
            return True
        else:
            print(f"❌ Webhook test failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Webhook request failed: {e}")
        return False

def test_subscription_webhook():
    """Test subscription-related webhooks"""
    print("\n🧪 Testing Subscription Webhooks...")
    
    # Test subscription created
    sub_payload = {
        "id": "evt_sub_test",
        "object": "event",
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_test123",
                "customer": "cus_test123",
                "status": "active",
                "items": {
                    "data": [{
                        "price": {
                            "id": "price_starter",
                            "unit_amount": 2900,
                            "metadata": {
                                "plan": "starter",
                                "documents_limit": "100"
                            }
                        }
                    }]
                },
                "metadata": {
                    "user_email": "test@example.com"
                }
            }
        }
    }
    
    payload_str = json.dumps(sub_payload)
    signature = create_stripe_signature(payload_str, WEBHOOK_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": signature
    }
    
    try:
        response = requests.post(
            WEBHOOK_ENDPOINT,
            data=payload_str,
            headers=headers,
            timeout=10
        )
        
        print(f"✅ Subscription Webhook: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Subscription webhook failed: {e}")
        return False

def test_api_endpoints():
    """Test related API endpoints"""
    print("\n🧪 Testing API Endpoints...")
    
    # Test main API
    try:
        response = requests.get(f"{API_BASE}/", timeout=5)
        print(f"✅ Main API: {response.status_code}")
    except:
        print("❌ Main API not accessible")
    
    # Test process-document endpoint
    try:
        test_payload = {
            "filename": "test.pdf",
            "file_content": "dGVzdA=="  # base64 "test"
        }
        response = requests.post(
            f"{API_BASE}/process-document",
            json=test_payload,
            timeout=10
        )
        print(f"✅ Process Document API: {response.status_code}")
    except Exception as e:
        print(f"❌ Process Document API failed: {e}")

def main():
    """Run all webhook tests"""
    print("🚀 Starting Stripe Webhook Tests")
    print("=" * 50)
    
    results = []
    
    # Test webhook endpoint
    results.append(test_webhook_endpoint())
    
    # Test subscription webhooks
    results.append(test_subscription_webhook())
    
    # Test API endpoints
    test_api_endpoints()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}/{len(results)} tests")
    
    if all(results):
        print("🎉 All webhook tests passed!")
    else:
        print("⚠️  Some tests failed - check configuration")
    
    print("\n💡 Next Steps:")
    print("1. Configure Stripe webhook endpoint in dashboard")
    print("2. Set webhook secret in Lambda environment")
    print("3. Test with real Stripe events")
    print("4. Monitor CloudWatch logs for webhook activity")

if __name__ == "__main__":
    main()