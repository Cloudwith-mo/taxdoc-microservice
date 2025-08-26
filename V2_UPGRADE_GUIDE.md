# 🚀 TaxDoc Pro v2.0 - Complete Upgrade Guide

## 🎯 Overview

This guide walks you through upgrading from TaxDoc MVP (v1) to the full-featured v2.0 with user accounts, payments, enhanced AI, and premium features.

## ✨ New Features in v2.0

### 1. 📱 Enhanced File Upload (Drag & Drop Photos)
- **Mobile-friendly photo uploads** from camera/gallery
- **Client-side image compression** for faster uploads
- **Drag & drop interface** with visual feedback
- **Preview functionality** for uploaded images
- **Support for HEIC, JPEG, PNG** formats

### 2. 🔐 User Authentication (AWS Cognito)
- **Secure user accounts** with email verification
- **JWT-based authentication** for API access
- **User profile management** with tier tracking
- **Password reset functionality**
- **Social login ready** (can be extended)

### 3. 💳 Payment Integration (Stripe)
- **Subscription management** with multiple tiers
- **Secure payment processing** via Stripe Checkout
- **Webhook handling** for real-time updates
- **Automatic tier upgrades** after successful payment
- **Cancel anytime** with prorated refunds

### 4. 🧠 Enhanced AI Features
- **Sentiment analysis** in chatbot interactions
- **Context-aware responses** based on user mood
- **Premium AI insights** for paid users
- **Enhanced document understanding**
- **Conversation history** storage

### 5. 🎨 Improved UI/UX
- **Better field labeling** with human-readable names
- **Confidence indicators** for extracted data
- **Processing source attribution** (Textract/AI/Regex)
- **Responsive design** for all devices
- **Premium feature highlighting**

## 🏗️ Architecture Changes

### New AWS Services Added:
- **AWS Cognito** - User authentication and management
- **Amazon Comprehend** - Sentiment analysis
- **Additional DynamoDB Tables** - User data and chat history
- **Enhanced Lambda Functions** - Payment and chat handling
- **API Gateway Authorizers** - Secure endpoint protection

### Frontend Enhancements:
- **React Context** for authentication state
- **Stripe.js integration** for payments
- **Enhanced components** with premium features
- **Improved error handling** and user feedback

## 📋 Prerequisites

Before upgrading to v2.0, ensure you have:

1. **Stripe Account** with API keys
2. **AWS Account** with appropriate permissions
3. **Node.js 18+** and npm installed
4. **AWS CLI** configured
5. **Existing v1 deployment** (optional - can start fresh)

## 🚀 Step-by-Step Upgrade Process

### Step 1: Prepare Stripe Integration

```bash
# 1. Create Stripe account at https://stripe.com
# 2. Get your API keys from Stripe Dashboard
# 3. Create webhook endpoint (will be configured after deployment)
# 4. Note down your keys:
#    - Secret Key (sk_test_...)
#    - Publishable Key (pk_test_...)
#    - Webhook Secret (whsec_...)
```

### Step 2: Deploy v2.0 Infrastructure

```bash
# Clone or update your repository
cd microproc

# Run the v2 deployment script
./scripts/deploy_v2.sh prod YOUR_STRIPE_SECRET_KEY YOUR_STRIPE_WEBHOOK_SECRET

# This will:
# - Deploy CloudFormation stack with new resources
# - Create Cognito User Pool
# - Set up DynamoDB tables
# - Deploy Lambda functions
# - Build and deploy frontend
```

### Step 3: Configure Stripe Webhook

```bash
# After deployment, configure your Stripe webhook:
# 1. Go to Stripe Dashboard > Webhooks
# 2. Add endpoint: https://YOUR_API_URL/prod/payment/webhook
# 3. Select events: checkout.session.completed, customer.subscription.deleted
# 4. Update webhook secret in your deployment
```

### Step 4: Update Environment Variables

```bash
# Update web-app/.env.production with your actual Stripe publishable key
cd web-app
nano .env.production

# Update this line:
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_ACTUAL_PUBLISHABLE_KEY
```

### Step 5: Test the Upgrade

```bash
# Test authentication
# 1. Visit your v2 frontend URL
# 2. Click "Sign In / Sign Up"
# 3. Create a test account
# 4. Verify email functionality

# Test payment integration
# 1. Sign in to your test account
# 2. Click "Upgrade" button
# 3. Use Stripe test card: 4242 4242 4242 4242
# 4. Verify tier upgrade

# Test enhanced features
# 1. Upload a document (try drag & drop)
# 2. Use the AI chat feature
# 3. Check sentiment analysis (premium feature)
# 4. Verify field labeling improvements
```

## 🔧 Configuration Options

### User Tiers

```javascript
// Three tiers available:
const tiers = {
  free: {
    documents_per_month: 5,
    features: ['basic_extraction', 'standard_support']
  },
  premium: {
    documents_per_month: 'unlimited',
    features: ['ai_insights', 'sentiment_analysis', 'priority_support', 'excel_export', 'chat']
  },
  enterprise: {
    documents_per_month: 'unlimited',
    features: ['all_premium', 'api_access', 'custom_integrations', 'dedicated_support']
  }
};
```

### Feature Flags

```bash
# Control feature availability via environment variables:
REACT_APP_ENABLE_PAYMENTS=true
REACT_APP_ENABLE_SENTIMENT_ANALYSIS=true
REACT_APP_ENABLE_PREMIUM_FEATURES=true
```

## 📊 Migration from v1 to v2

### Data Migration
- **No user data to migrate** (v1 was anonymous)
- **Document processing remains compatible**
- **API endpoints maintain backward compatibility**
- **New features are additive**

### Frontend Migration
- **v1 components remain functional**
- **New v2 components add enhanced features**
- **Gradual migration possible**
- **Can run both versions simultaneously**

## 🔍 Testing Checklist

### Authentication Testing
- [ ] User registration with email verification
- [ ] User login/logout functionality
- [ ] JWT token handling in API calls
- [ ] Protected route access control

### Payment Testing
- [ ] Stripe checkout session creation
- [ ] Test payment processing (use test cards)
- [ ] Webhook event handling
- [ ] Tier upgrade after payment
- [ ] Subscription cancellation

### Enhanced Features Testing
- [ ] Drag & drop file upload
- [ ] Photo upload from mobile devices
- [ ] Image compression functionality
- [ ] Sentiment analysis in chat
- [ ] Enhanced field labeling
- [ ] Premium feature restrictions

### API Testing
- [ ] Authenticated endpoints work correctly
- [ ] Unauthenticated access properly blocked
- [ ] Error handling for expired tokens
- [ ] Rate limiting for free tier users

## 🚨 Troubleshooting

### Common Issues

**1. Cognito Authentication Errors**
```bash
# Check User Pool configuration
aws cognito-idp describe-user-pool --user-pool-id YOUR_POOL_ID

# Verify client configuration
aws cognito-idp describe-user-pool-client --user-pool-id YOUR_POOL_ID --client-id YOUR_CLIENT_ID
```

**2. Stripe Payment Issues**
```bash
# Check webhook configuration
curl -X GET https://api.stripe.com/v1/webhook_endpoints \
  -H "Authorization: Bearer YOUR_SECRET_KEY"

# Test webhook endpoint
curl -X POST YOUR_API_URL/prod/payment/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

**3. Lambda Function Errors**
```bash
# Check function logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/DrDoc"

# View recent logs
aws logs filter-log-events --log-group-name "/aws/lambda/DrDoc-StripeHandler-prod"
```

### Performance Optimization

**1. Image Compression Settings**
```javascript
// Adjust compression settings in EnhancedUploader.js
const compressImage = (file) => {
  // Modify maxWidth, maxHeight, and quality as needed
  const maxWidth = 1920;  // Reduce for smaller files
  const maxHeight = 1080; // Reduce for smaller files
  const quality = 0.8;    // Reduce for more compression
};
```

**2. API Rate Limiting**
```yaml
# Add to API Gateway configuration
ThrottleSettings:
  BurstLimit: 100
  RateLimit: 20
```

## 📈 Monitoring and Analytics

### CloudWatch Metrics
- **User registration rates**
- **Payment conversion rates**
- **API usage by tier**
- **Sentiment analysis trends**
- **Error rates and performance**

### Custom Dashboards
```bash
# Create monitoring dashboard
aws cloudwatch put-dashboard --dashboard-name "DrDoc-v2-Metrics" --dashboard-body file://monitoring-dashboard.json
```

## 🔄 Rollback Plan

If issues arise, you can rollback:

```bash
# 1. Revert to v1 frontend
aws s3 sync v1-backup/ s3://your-frontend-bucket --delete

# 2. Route traffic back to v1 API
# Update DNS or load balancer configuration

# 3. Keep v2 infrastructure for debugging
# Don't delete CloudFormation stack immediately
```

## 🎉 Success Metrics

After successful v2 deployment, you should see:

- ✅ **User registration** working smoothly
- ✅ **Payment processing** completing successfully
- ✅ **Enhanced UI** providing better user experience
- ✅ **AI features** delivering premium value
- ✅ **Mobile compatibility** working across devices
- ✅ **Performance** maintained or improved

## 📞 Support

For deployment issues or questions:

1. **Check CloudWatch logs** for error details
2. **Review CloudFormation events** for deployment issues
3. **Test with Stripe test mode** before going live
4. **Verify Cognito configuration** for auth issues
5. **Contact support** at support@taxflowsai.com

## 🗺️ Future Enhancements

v2.0 sets the foundation for:
- **Multi-language support**
- **Advanced analytics dashboard**
- **API marketplace integration**
- **Mobile app development**
- **Enterprise SSO integration**

---

**🎯 Congratulations! You've successfully upgraded to TaxDoc Pro v2.0 with enhanced user experience, secure payments, and premium AI features!**