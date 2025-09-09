#!/bin/bash

echo "Fixing API Gateway Lambda function..."

# Create deployment package
cd src/handlers
zip -r api_handler.zip api_handler.py

# Update Lambda function
aws lambda update-function-code \
    --function-name taxdoc-process-prod \
    --zip-file fileb://api_handler.zip \
    --region us-east-1

echo "Lambda function updated successfully!"

# Clean up
rm api_handler.zip

echo "Testing the endpoint..."
curl -X POST https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/process \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.txt","contentBase64":"VGVzdCBkb2N1bWVudA=="}'