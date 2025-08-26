# 🔐 Stripe Setup Guide for TaxDoc Pro v2.0

## 1. Create Stripe Account
1. Go to https://stripe.com
2. Click "Start now" and create account
3. Complete business verification
4. Switch to Test mode for initial setup

## 2. Get API Keys
Navigate to: **Developers > API keys**

### Test Keys (for development):
- **Publishable key**: `pk_test_...` (starts with pk_test)
- **Secret key**: `sk_test_...` (starts with sk_test)

### Live Keys (for production):
- **Publishable key**: `pk_live_...` (starts with pk_live)  
- **Secret key**: `sk_live_...` (starts with sk_live)

## 3. Create Products and Prices
Navigate to: **Products > Add product**

### Premium Plan
- Name: "TaxDoc Pro Premium"
- Price: $29/month
- Copy the Price ID: `price_xxxxx`

### Enterprise Plan  
- Name: "TaxDoc Pro Enterprise"
- Price: $99/month
- Copy the Price ID: `price_xxxxx`

## 4. Test Cards
Use these for testing:
- **Success**: 4242 4242 4242 4242
- **Decline**: 4000 0000 0000 0002
- **3D Secure**: 4000 0025 0000 3155

## 5. Save Your Keys
```bash
# Test Environment
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx
PREMIUM_PRICE_ID=price_xxxxx
ENTERPRISE_PRICE_ID=price_xxxxx

# Production Environment (when ready)
STRIPE_SECRET_KEY=sk_live_xxxxx  
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
```

**⚠️ Keep secret keys secure - never commit to git!**