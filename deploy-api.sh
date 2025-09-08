#!/bin/bash
aws cloudformation deploy \
  --template-file infrastructure/main-api-stack.yaml \
  --stack-name taxdoc-main-api-prod \
  --parameter-overrides Environment=prod \
  --capabilities CAPABILITY_IAM

echo "API Gateway with CORS deployed successfully"