# 🎯 Complete Remaining Tasks - Step by Step Guide

## Task 1: Set Up Real Stripe Webhook

### Step 1.1: Install Stripe CLI
```bash
# On macOS
brew install stripe/stripe-cli/stripe

# Or download from: https://github.com/stripe/stripe-cli/releases
```

### Step 1.2: Login to Stripe
```bash
stripe login
# Follow prompts to authenticate with your Stripe account
```

### Step 1.3: Start Webhook Forwarding
```bash
# Forward webhooks to your API (keep this running in terminal)
stripe listen --forward-to https://svea4ri2tk.execute-api.us-east-1.amazonaws.com/prod/v2/webhooks/stripe
```
**Expected Output:**
```
> Ready! Your webhook signing secret is whsec_1234567890abcdef...
```

### Step 1.4: Copy the Real Webhook Secret
```bash
# Copy the webhook secret from the output above (starts with whsec_)
REAL_WEBHOOK_SECRET="whsec_1234567890abcdef..."  # Replace with actual secret
```

### Step 1.5: Update Lambda Environment
```bash
aws lambda update-function-configuration \
  --function-name DrDoc-StripeHandler-prod \
  --environment Variables='{
    "STRIPE_SECRET_KEY":"sk_test_PLACEHOLDER_KEY",
    "STRIPE_WEBHOOK_SECRET":"'$REAL_WEBHOOK_SECRET'",
    "USERS_TABLE":"DrDocUsers-prod",
    "ENVIRONMENT":"prod"
  }'
```

### Step 1.6: Test Stripe Webhook
```bash
# In another terminal, trigger a test event
stripe trigger checkout.session.completed

# Check Lambda logs
aws logs filter-log-events --log-group-name /aws/lambda/DrDoc-StripeHandler-prod --limit 10
```

---

## Task 2: Deploy Export Resources

### Step 2.1: Deploy CloudFormation Stack
```bash
cd /Users/muhammadadeyemi/Documents/microproc

aws cloudformation deploy \
  --template-file export-resources.yaml \
  --stack-name DrDoc-Export-Resources-prod \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Environment=prod
```

### Step 2.2: Verify Deployment
```bash
# Check stack status
aws cloudformation describe-stacks --stack-name DrDoc-Export-Resources-prod --query "Stacks[0].StackStatus"

# Get outputs
aws cloudformation describe-stacks --stack-name DrDoc-Export-Resources-prod --query "Stacks[0].Outputs"
```

### Step 2.3: Test Export Bucket
```bash
# Verify bucket exists and has lifecycle policy
aws s3api get-bucket-lifecycle-configuration --bucket drdoc-exports-prod-995805900737

# Test bucket access
aws s3 ls s3://drdoc-exports-prod-995805900737/
```

---

## Task 3: Test with Real Cognito JWT

### Step 3.1: Create Test User
```bash
# Create a test user in Cognito
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_rDOfQbvrT \
  --username testuser@example.com \
  --user-attributes Name=email,Value=testuser@example.com \
  --temporary-password TempPass123! \
  --message-action SUPPRESS
```

### Step 3.2: Set Permanent Password
```bash
# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_rDOfQbvrT \
  --username testuser@example.com \
  --password MySecurePass123! \
  --permanent
```

### Step 3.3: Get Cognito Client ID
```bash
# Get the client ID
CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id us-east-1_rDOfQbvrT --query "UserPoolClients[0].ClientId" --output text)
echo "Client ID: $CLIENT_ID"
```

### Step 3.4: Authenticate and Get JWT
```bash
# Authenticate user and get JWT token
AUTH_RESPONSE=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id us-east-1_rDOfQbvrT \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=testuser@example.com,PASSWORD=MySecurePass123!)

# Extract JWT token
JWT_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.AccessToken')
echo "JWT Token: ${JWT_TOKEN:0:50}..."
```

### Step 3.5: Test Protected Endpoint with JWT
```bash
# Test protected endpoint with valid JWT
curl -i -H "Authorization: Bearer $JWT_TOKEN" \
  https://svea4ri2tk.execute-api.us-east-1.amazonaws.com/prod/v2/me
```
**Expected**: HTTP 200 with user info

---

## Task 4: Test Full Upload → Process → Export Flow

### Step 4.1: Get Presigned Upload URL
```bash
# Request presigned upload URL
UPLOAD_RESPONSE=$(curl -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename":"test-w2.png","contentType":"image/png"}' \
  https://svea4ri2tk.execute-api.us-east-1.amazonaws.com/prod/v2/upload)

echo $UPLOAD_RESPONSE | jq '.'
```

### Step 4.2: Upload Test Document
```bash
# Extract upload URL and document ID
UPLOAD_URL=$(echo $UPLOAD_RESPONSE | jq -r '.uploadUrl')
DOC_ID=$(echo $UPLOAD_RESPONSE | jq -r '.documentId')

# Upload a test image (replace with actual file)
curl -X PUT "$UPLOAD_URL" \
  -H "Content-Type: image/png" \
  --data-binary @images/sample_w2.png
```

### Step 4.3: Check Processing Status
```bash
# Wait for processing and check status
sleep 10
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://svea4ri2tk.execute-api.us-east-1.amazonaws.com/prod/v2/documents/$DOC_ID
```

### Step 4.4: Request Export
```bash
# Request CSV export
EXPORT_RESPONSE=$(curl -H "Authorization: Bearer $JWT_TOKEN" \
  "https://svea4ri2tk.execute-api.us-east-1.amazonaws.com/prod/v2/export_data?docId=$DOC_ID&format=csv")

echo $EXPORT_RESPONSE | jq '.'
```

### Step 4.5: Verify Export Job
```bash
# Get export job ID
EXPORT_JOB_ID=$(echo $EXPORT_RESPONSE | jq -r '.jobId')

# Check export job status
aws dynamodb get-item \
  --table-name DrDocExportJobs-prod \
  --key '{"jobId":{"S":"'$EXPORT_JOB_ID'"}}'
```

---

## Task 5: Operational & Security Checks

### Step 5.1: Set S3 Bucket Encryption
```bash
# Enable encryption on export bucket
aws s3api put-bucket-encryption \
  --bucket drdoc-exports-prod-995805900737 \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### Step 5.2: Verify Presigned URL TTL
```bash
# Check Lambda code for presigned URL expiry (should be <= 3600s)
aws lambda get-function --function-name DrDoc-ProcessDocument-prod --query "Code.Location"
```

### Step 5.3: Check IAM Permissions
```bash
# Verify export Lambda has minimal permissions
aws iam get-role-policy \
  --role-name DrDoc-ExportLambda-Role-prod \
  --policy-name ExportPolicy
```

---

## Task 6: Enable Monitoring & Budgets

### Step 6.1: Create Budget Alarm for Textract/Bedrock
```bash
# Create budget for AI services
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget '{
    "BudgetName": "DrDoc-AI-Services-Budget",
    "BudgetLimit": {
      "Amount": "20.00",
      "Unit": "USD"
    },
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "Service": ["Amazon Textract", "Amazon Bedrock"]
    }
  }'
```

### Step 6.2: Verify CloudWatch Alarms
```bash
# Check all DrDoc alarms
aws cloudwatch describe-alarms \
  --query "MetricAlarms[?contains(AlarmName,'DrDoc')].[AlarmName,StateValue,StateReason]" \
  --output table
```

---

## Task 7: Run End-to-End Tests

### Step 7.1: Run Automated Smoke Test
```bash
cd /Users/muhammadadeyemi/Documents/microproc
bash immediate_validation.sh
```

### Step 7.2: Manual QA Test
```bash
# Open enhanced frontend
open http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html

# Test workflow:
# 1. Upload W-2 document
# 2. Wait for processing
# 3. Edit any incorrect fields
# 4. Download CSV, Excel, JSON
# 5. Test AI chat with document questions
# 6. Test generic tax questions
```

---

## Task 8: Document & Rollback Plan

### Step 8.1: Create Rollback Script
```bash
cat > rollback_v2.sh << 'EOF'
#!/bin/bash
# Rollback V2 to V1
echo "Rolling back to V1..."

# Disable V2 feature flag (if using feature flags)
# aws ssm put-parameter --name "/drdoc/feature-flags/v2-enabled" --value "false" --overwrite

# Route traffic back to V1 API
# aws apigateway update-stage --rest-api-id YOUR_API_ID --stage-name prod --patch-ops op=replace,path=/variables/version,value=v1

echo "Rollback complete"
EOF

chmod +x rollback_v2.sh
```

### Step 8.2: Document V1 Deprecation
```bash
cat > V1_DEPRECATION_SCHEDULE.md << 'EOF'
# V1 Deprecation Schedule

## Timeline
- **Week 1-2**: V2 beta testing with 5% of users
- **Week 3-4**: Gradual rollout to 25% of users
- **Week 5-6**: Full rollout to 100% of users
- **Week 7-8**: V1 deprecation warnings
- **Week 9**: V1 shutdown

## Rollback Triggers
- Error rate > 5%
- User complaints > 10/day
- Processing accuracy < 85%
- System downtime > 1 hour

## Monitoring
- CloudWatch dashboards
- User feedback tracking
- Performance metrics
- Cost analysis
EOF
```

---

## 🎯 Quick Execution Summary

```bash
# 1. Stripe webhook (run in separate terminal)
stripe listen --forward-to https://svea4ri2tk.execute-api.us-east-1.amazonaws.com/prod/v2/webhooks/stripe

# 2. Deploy export resources
aws cloudformation deploy --template-file export-resources.yaml --stack-name DrDoc-Export-Resources-prod --capabilities CAPABILITY_NAMED_IAM

# 3. Create test user and get JWT
aws cognito-idp admin-create-user --user-pool-id us-east-1_rDOfQbvrT --username test@example.com --user-attributes Name=email,Value=test@example.com --temporary-password TempPass123! --message-action SUPPRESS

# 4. Run validation
bash immediate_validation.sh

# 5. Test frontend
open http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html
```

## ✅ Success Criteria

- ✅ Stripe webhook receives events and processes them
- ✅ JWT authentication works for protected endpoints  
- ✅ Export functionality creates files in S3
- ✅ CloudWatch alarms are active
- ✅ Budget alerts are configured
- ✅ End-to-end workflow completes successfully
- ✅ AI chat answers both document and generic questions

**All tasks completed = Production ready V2 system! 🚀**