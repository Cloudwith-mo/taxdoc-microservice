#!/bin/bash

# Deploy W-2 AI Enhancement to Production
set -e

echo "🚀 Deploying W-2 AI Enhancement to Production..."

# Build and deploy backend
echo "📦 Building SAM application..."
cd /Users/muhammadadeyemi/Documents/microproc
sam build -t infrastructure/template.yaml

echo "🔧 Deploying to production..."
sam deploy \
  --stack-name taxdoc-stack-prod \
  --parameter-overrides Environment=prod \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --no-confirm-changeset

# Get API endpoint
API_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name taxdoc-stack-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)

echo "✅ Backend deployed successfully!"
echo "🔗 API Endpoint: $API_ENDPOINT"

# Test W-2 processing with sample document
echo "🧪 Testing W-2 AI extraction..."

# Create test W-2 document (mock data)
cat > /tmp/test_w2.txt << EOF
W-2 Wage and Tax Statement
Tax Year: 2023

Employee Information:
Name: John Doe
SSN: 123-45-6789

Employer Information:
Name: ABC Corporation
EIN: 12-3456789

Box 1: Wages, tips, other compensation: $75,000.00
Box 2: Federal income tax withheld: $12,500.00
Box 3: Social security wages: $75,000.00
Box 4: Social security tax withheld: $4,650.00
Box 5: Medicare wages and tips: $75,000.00
Box 6: Medicare tax withheld: $1,087.50
Box 15: State: CA
Box 16: State wages, tips, etc.: $75,000.00
Box 17: State income tax: $3,750.00
EOF

# Upload test document to S3
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name taxdoc-stack-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`UploadBucket`].OutputValue' \
  --output text)

echo "📤 Uploading test W-2 to S3..."
aws s3 cp /tmp/test_w2.txt s3://$BUCKET_NAME/test-w2-$(date +%s).txt

echo "⏳ Waiting for processing (check CloudWatch logs for results)..."
echo "📊 Monitor processing at: https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups"

# Clean up
rm /tmp/test_w2.txt

echo "🎉 W-2 AI Enhancement deployment completed!"
echo ""
echo "📋 Key Features Added:"
echo "  ✓ AI-powered field extraction using Claude"
echo "  ✓ Comprehensive W-2 field coverage (all boxes)"
echo "  ✓ Cross-validation between AI and rule-based methods"
echo "  ✓ Confidence scoring and conflict detection"
echo "  ✓ Completeness scoring for data quality"
echo ""
echo "🔍 Next Steps:"
echo "  1. Monitor CloudWatch logs for processing results"
echo "  2. Test with real W-2 documents"
echo "  3. Review validation metrics in DynamoDB"
echo "  4. Adjust confidence thresholds if needed"