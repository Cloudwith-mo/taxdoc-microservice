# 🚀 Execute TaxDoc Pro v2.0 Deployment

## Prerequisites Check
```bash
# Verify AWS CLI is configured
aws sts get-caller-identity

# Verify you're in the right directory
pwd
# Should show: /Users/muhammadadeyemi/Documents/microproc
```

## Step 1: Get Stripe Keys
1. Go to https://stripe.com and create account
2. Navigate to **Developers > API keys**
3. Copy your test keys:
   - Secret key: `sk_test_xxxxx`
   - Publishable key: `pk_test_xxxxx`

## Step 2: Create Stripe Webhook (Temporary)
```bash
# For now, use a placeholder webhook secret
STRIPE_WEBHOOK_SECRET="whsec_placeholder"
```

## Step 3: Deploy v2.0 Infrastructure
```bash
# Replace with your actual Stripe secret key
STRIPE_SECRET_KEY="sk_test_YOUR_ACTUAL_KEY_HERE"
STRIPE_WEBHOOK_SECRET="whsec_placeholder"

# Deploy v2.0
./scripts/quick_deploy_v2.sh $STRIPE_SECRET_KEY $STRIPE_WEBHOOK_SECRET
```

## Step 4: Configure Real Stripe Webhook
After deployment, you'll get an API URL. Then:

1. Go to Stripe Dashboard > **Webhooks**
2. Click **Add endpoint**
3. URL: `https://YOUR_API_URL/prod/payment/webhook`
4. Events: Select `checkout.session.completed`
5. Copy the webhook secret: `whsec_xxxxx`

## Step 5: Update Webhook Secret
```bash
# Update the Lambda function with real webhook secret
aws lambda update-function-configuration \
  --function-name DrDoc-StripeHandler-prod \
  --environment Variables='{
    "STRIPE_SECRET_KEY":"'$STRIPE_SECRET_KEY'",
    "STRIPE_WEBHOOK_SECRET":"whsec_YOUR_REAL_SECRET",
    "USERS_TABLE":"DrDocUsers-prod",
    "ENVIRONMENT":"prod"
  }'
```

## Step 6: Deploy Frontend
```bash
cd web-app

# Install v2 dependencies
npm install @stripe/stripe-js browser-image-compression

# Create production environment file
cat > .env.production << 'EOF'
REACT_APP_USER_POOL_ID=YOUR_POOL_ID_FROM_DEPLOYMENT
REACT_APP_USER_POOL_CLIENT_ID=YOUR_CLIENT_ID_FROM_DEPLOYMENT
REACT_APP_AWS_REGION=us-east-1
REACT_APP_API_BASE_URL=YOUR_API_URL_FROM_DEPLOYMENT
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_PUBLISHABLE_KEY
REACT_APP_ENABLE_PAYMENTS=true
REACT_APP_ENABLE_SENTIMENT_ANALYSIS=true
REACT_APP_ENABLE_PREMIUM_FEATURES=true
EOF

# Build and deploy
npm run build

# Deploy to S3
BUCKET_NAME="taxdoc-web-app-v2-prod"
aws s3 mb s3://$BUCKET_NAME --region us-east-1
aws s3 website s3://$BUCKET_NAME --index-document index.html
aws s3 sync build/ s3://$BUCKET_NAME --delete

# Set public read policy
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow", 
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::'$BUCKET_NAME'/*"
  }]
}'
```

## Step 7: Test Deployment
```bash
# Test authentication endpoint
curl -X POST "YOUR_API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
# Should return 401 Unauthorized (good!)

# Visit your frontend
echo "🌐 Frontend URL: http://$BUCKET_NAME.s3-website-us-east-1.amazonaws.com"
```

## Step 8: Setup Monitoring
```bash
# Create monitoring dashboard
python3 scripts/setup_v2_monitoring.py
```

## Step 9: Test All Features
Use the testing checklist:
```bash
cat V2_TESTING_CHECKLIST.md
```

## 🎉 Success!
Your TaxDoc Pro v2.0 should now be live with:
- ✅ User authentication (Cognito)
- ✅ Payment processing (Stripe) 
- ✅ Enhanced drag & drop upload
- ✅ Sentiment-aware AI chat
- ✅ Improved field labeling
- ✅ Premium feature tiers

## 🔧 Troubleshooting
If something fails:
```bash
# Check CloudFormation stack
aws cloudformation describe-stack-events --stack-name DrDoc-v2-prod

# Check Lambda logs
aws logs filter-log-events --log-group-name "/aws/lambda/DrDoc-StripeHandler-prod"

# Rollback if needed
aws cloudformation delete-stack --stack-name DrDoc-v2-prod
```