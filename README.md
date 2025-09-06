# TaxDoc AI - Document Processing Platform

Production-ready AWS serverless platform for AI-powered document extraction with authentication and payments.

## 🚀 Live Platform
- **Frontend**: http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html
- **API**: https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod

## 🏗️ Architecture
- **Frontend**: React with authentication and pricing modals
- **Backend**: AWS Lambda functions for processing, auth, and payments
- **Storage**: S3 for documents, DynamoDB for metadata
- **AI**: Textract + Claude LLM + Regex fallback pipeline
- **Auth**: Cognito user pools with JWT tokens
- **Payments**: Stripe subscriptions with webhooks

## 📁 Structure
```
├── src/
│   ├── handlers/          # Lambda functions
│   ├── services/          # Business logic
│   └── config/            # Document configurations
├── web-app/               # React frontend
├── infrastructure/        # CloudFormation templates
└── scripts/               # Deployment scripts
```

## 🚀 Deployment

### Prerequisites
```bash
export STRIPE_SECRET_KEY="sk_test_..."
export STRIPE_WEBHOOK_SECRET="whsec_..."
export COGNITO_USER_POOL_ID="us-east-1_..."
export COGNITO_CLIENT_ID="..."
export COGNITO_CLIENT_SECRET="..."
```

### Deploy Infrastructure
```bash
chmod +x deploy.sh
./deploy.sh
```

### Deploy Frontend
```bash
cd web-app
npm install
npm run build
aws s3 sync build/ s3://your-bucket-name
```

## 🔧 Configuration

**Environment Variables:**
- `STRIPE_SECRET_KEY` - Stripe API secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook endpoint secret
- `COGNITO_USER_POOL_ID` - Cognito user pool identifier
- `COGNITO_CLIENT_ID` - Cognito app client ID
- `COGNITO_CLIENT_SECRET` - Cognito app client secret

**IAM Role Required:**
- Lambda execution role with permissions for:
  - Cognito user pool management
  - DynamoDB read/write
  - S3 object access
  - CloudWatch logging

## 📊 Features
- ✅ User authentication (Cognito)
- ✅ Subscription payments (Stripe)
- ✅ AI document extraction
- ✅ Batch processing
- ✅ Multiple export formats
- ✅ Real-time analytics
- ✅ SNS notifications

## 🔐 Security
- JWT token authentication
- Encrypted environment variables
- Private S3 buckets
- HTTPS/TLS communications
- Secrets excluded from repository