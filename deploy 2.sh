#!/bin/bash

# Deploy authentication and payment infrastructure
aws cloudformation deploy \
  --template-file infrastructure/auth-payment-stack.yaml \
  --stack-name taxdoc-auth-payment-prod \
  --parameter-overrides \
    Environment=prod \
    StripeSecretKey=$STRIPE_SECRET_KEY \
    StripeWebhookSecret=$STRIPE_WEBHOOK_SECRET \
  --capabilities CAPABILITY_IAM

# Package and deploy Lambda functions
cd src/handlers
zip -r stripe-payment.zip stripe_payment_handler.py
zip -r cognito-auth.zip cognito_auth_handler.py

aws lambda create-function \
  --function-name stripe-payment-prod \
  --runtime python3.9 \
  --role arn:aws:iam::995805900737:role/lambda-execution-role \
  --handler stripe_payment_handler.lambda_handler \
  --zip-file fileb://stripe-payment.zip \
  --environment Variables="{STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY,STRIPE_WEBHOOK_SECRET=$STRIPE_WEBHOOK_SECRET}"

aws lambda create-function \
  --function-name cognito-auth-prod \
  --runtime python3.9 \
  --role arn:aws:iam::995805900737:role/lambda-execution-role \
  --handler cognito_auth_handler.lambda_handler \
  --zip-file fileb://cognito-auth.zip \
  --environment Variables="{COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID,COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID,COGNITO_CLIENT_SECRET=$COGNITO_CLIENT_SECRET}"

echo "Deployment complete"