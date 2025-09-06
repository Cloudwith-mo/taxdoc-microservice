# Infrastructure Deployment Guide

## Prerequisites

### 1. Set Environment Variables
```bash
export STRIPE_SECRET_KEY="sk_live_..." # or sk_test_...
export STRIPE_WEBHOOK_SECRET="whsec_..."
```

### 2. Create IAM Role
```bash
aws iam create-role --role-name lambda-execution-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}'

aws iam attach-role-policy --role-name lambda-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam put-role-policy --role-name lambda-execution-role --policy-name CognitoAccess --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["cognito-idp:*"],
      "Resource": "*"
    }
  ]
}'
```

## Deployment Steps

### 1. Deploy Infrastructure
```bash
./deploy.sh
```

### 2. Get Cognito Details
```bash
aws cognito-idp list-user-pools --max-items 10
aws cognito-idp list-user-pool-clients --user-pool-id YOUR_POOL_ID
```

### 3. Update Environment Variables
```bash
export COGNITO_USER_POOL_ID="us-east-1_..."
export COGNITO_CLIENT_ID="..."
export COGNITO_CLIENT_SECRET="..." # Get from describe-user-pool-client
```

### 4. Update Lambda Functions
```bash
aws lambda update-function-configuration --function-name cognito-auth-prod --environment Variables="{COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID,COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID,COGNITO_CLIENT_SECRET=$COGNITO_CLIENT_SECRET}"
```

### 5. Deploy Frontend
```bash
cd web-app
npm install
npm run build
aws s3 sync build/ s3://taxdoc-mvp-web-1754513919
```

## Verification
- Test authentication: Login/register on frontend
- Test payments: Subscribe to plan
- Test document processing: Upload sample document