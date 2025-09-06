#!/bin/bash
aws cloudformation deploy --template-file infrastructure/auth-payment-stack.yaml --stack-name taxdoc-auth-payment-prod --parameter-overrides Environment=prod StripeSecretKey=$STRIPE_SECRET_KEY StripeWebhookSecret=$STRIPE_WEBHOOK_SECRET --capabilities CAPABILITY_IAM
echo "Deployment complete"
