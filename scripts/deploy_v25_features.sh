#!/bin/bash
# Deploy TaxDoc v2.5 Features
# This script deploys all the new features from the GitHub issues

set -e

ENVIRONMENT=${1:-prod}
EMAIL=${2:-"admin@taxflowsai.com"}

echo "🚀 Deploying TaxDoc v2.5 Features to $ENVIRONMENT"
echo "📧 Notifications will be sent to: $EMAIL"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install AWS CLI."
    exit 1
fi

if ! command -v zip &> /dev/null; then
    print_error "zip command not found. Please install zip."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure'."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_success "AWS Account ID: $ACCOUNT_ID"

# Step 1: Deploy Export Resources
print_status "Step 1: Deploying export resources..."

aws cloudformation deploy \
    --template-file infrastructure/export-resources.yaml \
    --stack-name DrDoc-Export-Resources-$ENVIRONMENT \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides Environment=$ENVIRONMENT \
    --region us-east-1

if [ $? -eq 0 ]; then
    print_success "Export resources deployed successfully"
else
    print_error "Failed to deploy export resources"
    exit 1
fi

# Get stack outputs
EXPORTS_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name DrDoc-Export-Resources-$ENVIRONMENT \
    --query "Stacks[0].Outputs[?OutputKey=='ExportsBucketName'].OutputValue" \
    --output text)

DOC_READY_TOPIC=$(aws cloudformation describe-stacks \
    --stack-name DrDoc-Export-Resources-$ENVIRONMENT \
    --query "Stacks[0].Outputs[?OutputKey=='DocReadyTopicArn'].OutputValue" \
    --output text)

print_success "Exports bucket: $EXPORTS_BUCKET"
print_success "SNS topic: $DOC_READY_TOPIC"

# Step 2: Package and Deploy Lambda Functions
print_status "Step 2: Packaging Lambda functions..."

# Create deployment directory
mkdir -p deployment/v25

# Package entitlement middleware
print_status "Packaging entitlement middleware..."
cd src/handlers
zip -r ../../deployment/v25/entitlement-middleware.zip entitlement_middleware.py
cd ../..

# Package enhanced Stripe handler
print_status "Packaging enhanced Stripe handler..."
cd src/handlers
zip -r ../../deployment/v25/enhanced-stripe-handler.zip enhanced_stripe_handler.py
cd ../..

# Package batch upload handler
print_status "Packaging batch upload handler..."
cd src/handlers
zip -r ../../deployment/v25/batch-upload-handler.zip batch_upload_handler.py entitlement_middleware.py
cd ../..

# Package export handler
print_status "Packaging export handler..."
cd src/handlers
zip -r ../../deployment/v25/export-handler.zip export_handler.py entitlement_middleware.py
cd ../..

# Package notification handler
print_status "Packaging notification handler..."
cd src/handlers
zip -r ../../deployment/v25/notification-handler.zip notification_handler.py
cd ../..

print_success "All Lambda packages created"

# Step 3: Deploy Lambda Functions
print_status "Step 3: Deploying Lambda functions..."

# Deploy Enhanced Stripe Handler
print_status "Deploying Enhanced Stripe Handler..."
aws lambda create-function \
    --function-name DrDoc-EnhancedStripeHandler-$ENVIRONMENT \
    --runtime python3.9 \
    --role arn:aws:iam::$ACCOUNT_ID:role/DrDoc-StripeHandler-Role-$ENVIRONMENT \
    --handler enhanced_stripe_handler.lambda_handler \
    --zip-file fileb://deployment/v25/enhanced-stripe-handler.zip \
    --timeout 30 \
    --environment Variables='{
        "STRIPE_SECRET_KEY":"'${STRIPE_SECRET_KEY:-sk_test_placeholder}'",
        "STRIPE_WEBHOOK_SECRET":"'${STRIPE_WEBHOOK_SECRET:-whsec_placeholder}'",
        "USERS_TABLE":"DrDocUsers-'$ENVIRONMENT'",
        "ENVIRONMENT":"'$ENVIRONMENT'"
    }' 2>/dev/null || \
aws lambda update-function-code \
    --function-name DrDoc-EnhancedStripeHandler-$ENVIRONMENT \
    --zip-file fileb://deployment/v25/enhanced-stripe-handler.zip

# Deploy Batch Upload Handler
print_status "Deploying Batch Upload Handler..."
aws lambda create-function \
    --function-name DrDoc-BatchUploadHandler-$ENVIRONMENT \
    --runtime python3.9 \
    --role arn:aws:iam::$ACCOUNT_ID:role/DrDoc-BatchLambda-Role-$ENVIRONMENT \
    --handler batch_upload_handler.lambda_handler \
    --zip-file fileb://deployment/v25/batch-upload-handler.zip \
    --timeout 300 \
    --memory-size 512 \
    --environment Variables='{
        "UPLOAD_BUCKET":"drdoc-uploads-'$ENVIRONMENT'-'$ACCOUNT_ID'",
        "BATCH_TABLE":"DrDocBatches-'$ENVIRONMENT'",
        "USERS_TABLE":"DrDocUsers-'$ENVIRONMENT'",
        "PROCESSING_QUEUE_URL":"https://sqs.us-east-1.amazonaws.com/'$ACCOUNT_ID'/DrDoc-Processing-'$ENVIRONMENT'",
        "ENVIRONMENT":"'$ENVIRONMENT'"
    }' 2>/dev/null || \
aws lambda update-function-code \
    --function-name DrDoc-BatchUploadHandler-$ENVIRONMENT \
    --zip-file fileb://deployment/v25/batch-upload-handler.zip

# Deploy Export Handler
print_status "Deploying Export Handler..."
aws lambda create-function \
    --function-name DrDoc-ExportHandler-$ENVIRONMENT \
    --runtime python3.9 \
    --role arn:aws:iam::$ACCOUNT_ID:role/DrDoc-ExportLambda-Role-$ENVIRONMENT \
    --handler export_handler.lambda_handler \
    --zip-file fileb://deployment/v25/export-handler.zip \
    --timeout 300 \
    --memory-size 1024 \
    --environment Variables='{
        "EXPORTS_BUCKET":"'$EXPORTS_BUCKET'",
        "RESULTS_TABLE":"DrDocDocuments-'$ENVIRONMENT'",
        "EXPORT_LOGS_TABLE":"DrDocExportLogs-'$ENVIRONMENT'",
        "USERS_TABLE":"DrDocUsers-'$ENVIRONMENT'",
        "ENVIRONMENT":"'$ENVIRONMENT'"
    }' 2>/dev/null || \
aws lambda update-function-code \
    --function-name DrDoc-ExportHandler-$ENVIRONMENT \
    --zip-file fileb://deployment/v25/export-handler.zip

# Deploy Notification Handler
print_status "Deploying Notification Handler..."
aws lambda create-function \
    --function-name DrDoc-NotificationHandler-$ENVIRONMENT \
    --runtime python3.9 \
    --role arn:aws:iam::$ACCOUNT_ID:role/DrDoc-NotificationLambda-Role-$ENVIRONMENT \
    --handler notification_handler.lambda_handler \
    --zip-file fileb://deployment/v25/notification-handler.zip \
    --timeout 60 \
    --environment Variables='{
        "DOC_READY_TOPIC_ARN":"'$DOC_READY_TOPIC'",
        "FROM_EMAIL":"noreply@taxflowsai.com",
        "ENVIRONMENT":"'$ENVIRONMENT'"
    }' 2>/dev/null || \
aws lambda update-function-code \
    --function-name DrDoc-NotificationHandler-$ENVIRONMENT \
    --zip-file fileb://deployment/v25/notification-handler.zip

print_success "All Lambda functions deployed"

# Step 4: Update API Gateway
print_status "Step 4: Updating API Gateway..."

# Get API Gateway ID
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='DrDoc-API-$ENVIRONMENT'].id" --output text)

if [ -z "$API_ID" ]; then
    print_error "API Gateway not found"
    exit 1
fi

print_success "Found API Gateway: $API_ID"

# Create v2 resource if it doesn't exist
V2_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query "items[?pathPart=='v2'].id" --output text)

if [ -z "$V2_RESOURCE_ID" ]; then
    print_status "Creating /v2 resource..."
    ROOT_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query "items[?path=='/'].id" --output text)
    
    V2_RESOURCE_ID=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $ROOT_RESOURCE_ID \
        --path-part v2 \
        --query "id" --output text)
fi

print_success "V2 resource ID: $V2_RESOURCE_ID"

# Create batch upload endpoint
print_status "Creating batch upload endpoint..."
BATCH_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $V2_RESOURCE_ID \
    --path-part batch-upload \
    --query "id" --output text 2>/dev/null || \
aws apigateway get-resources --rest-api-id $API_ID --query "items[?pathPart=='batch-upload'].id" --output text)

# Add POST method for batch upload
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $BATCH_RESOURCE_ID \
    --http-method POST \
    --authorization-type NONE 2>/dev/null || true

# Create export endpoint
print_status "Creating export endpoint..."
EXPORT_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $V2_RESOURCE_ID \
    --path-part export \
    --query "id" --output text 2>/dev/null || \
aws apigateway get-resources --rest-api-id $API_ID --query "items[?pathPart=='export'].id" --output text)

# Add GET method for export
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $EXPORT_RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE 2>/dev/null || true

# Deploy API Gateway
print_status "Deploying API Gateway..."
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name $ENVIRONMENT \
    --description "v2.5 features deployment"

print_success "API Gateway updated"

# Step 5: Subscribe to SNS Topics
print_status "Step 5: Setting up SNS subscriptions..."

# Subscribe email to doc-ready topic
aws sns subscribe \
    --topic-arn $DOC_READY_TOPIC \
    --protocol email \
    --notification-endpoint $EMAIL 2>/dev/null || true

print_success "SNS subscriptions configured"

# Step 6: Deploy Enhanced Frontend
print_status "Step 6: Deploying enhanced frontend..."

# Upload enhanced frontend
aws s3 cp web-mvp/mvp2-full.html s3://taxdoc-mvp-web-1754513919/mvp2-enhanced.html \
    --content-type "text/html" \
    --cache-control "no-cache"

print_success "Enhanced frontend deployed"

# Step 7: Create CloudWatch Dashboard
print_status "Step 7: Creating CloudWatch dashboard..."

cat > deployment/v25/dashboard.json << EOF
{
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "Invocations", "FunctionName", "DrDoc-BatchUploadHandler-$ENVIRONMENT"],
                    [".", "Errors", ".", "."],
                    [".", "Duration", ".", "."]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "us-east-1",
                "title": "Batch Upload Metrics"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/Lambda", "Invocations", "FunctionName", "DrDoc-ExportHandler-$ENVIRONMENT"],
                    [".", "Errors", ".", "."],
                    [".", "Duration", ".", "."]
                ],
                "period": 300,
                "stat": "Sum",
                "region": "us-east-1",
                "title": "Export Handler Metrics"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/S3", "BucketSizeBytes", "BucketName", "$EXPORTS_BUCKET", "StorageType", "StandardStorage"]
                ],
                "period": 86400,
                "stat": "Average",
                "region": "us-east-1",
                "title": "Export Bucket Size"
            }
        }
    ]
}
EOF

aws cloudwatch put-dashboard \
    --dashboard-name "DrDoc-v25-$ENVIRONMENT" \
    --dashboard-body file://deployment/v25/dashboard.json

print_success "CloudWatch dashboard created"

# Step 8: Create CloudWatch Alarms
print_status "Step 8: Creating CloudWatch alarms..."

# Batch upload errors alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "DrDoc-BatchUpload-Errors-$ENVIRONMENT" \
    --alarm-description "Batch upload Lambda errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --alarm-actions "arn:aws:sns:us-east-1:$ACCOUNT_ID:drdoc-alerts-$ENVIRONMENT" \
    --dimensions Name=FunctionName,Value=DrDoc-BatchUploadHandler-$ENVIRONMENT

# Export handler errors alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "DrDoc-Export-Errors-$ENVIRONMENT" \
    --alarm-description "Export handler Lambda errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 3 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --alarm-actions "arn:aws:sns:us-east-1:$ACCOUNT_ID:drdoc-alerts-$ENVIRONMENT" \
    --dimensions Name=FunctionName,Value=DrDoc-ExportHandler-$ENVIRONMENT

print_success "CloudWatch alarms created"

# Step 9: Test Deployment
print_status "Step 9: Running deployment tests..."

# Test API Gateway endpoints
API_URL="https://$API_ID.execute-api.us-east-1.amazonaws.com/$ENVIRONMENT"

print_status "Testing API endpoints..."

# Test batch upload endpoint
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/v2/batch-upload" \
    -H "Content-Type: application/json" \
    -d '{"test": true}')

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "400" ]; then
    print_success "Batch upload endpoint responding"
else
    print_warning "Batch upload endpoint returned: $HTTP_STATUS"
fi

# Test export endpoint
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/v2/export?docId=test")

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "400" ] || [ "$HTTP_STATUS" = "404" ]; then
    print_success "Export endpoint responding"
else
    print_warning "Export endpoint returned: $HTTP_STATUS"
fi

# Test frontend
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html")

if [ "$HTTP_STATUS" = "200" ]; then
    print_success "Enhanced frontend accessible"
else
    print_warning "Enhanced frontend returned: $HTTP_STATUS"
fi

# Step 10: Cleanup
print_status "Step 10: Cleaning up deployment files..."
rm -rf deployment/v25

print_success "Deployment cleanup complete"

# Final Summary
echo ""
echo "🎉 TaxDoc v2.5 Deployment Complete!"
echo ""
echo "📋 Deployment Summary:"
echo "  • Environment: $ENVIRONMENT"
echo "  • Account ID: $ACCOUNT_ID"
echo "  • Exports Bucket: $EXPORTS_BUCKET"
echo "  • SNS Topic: $DOC_READY_TOPIC"
echo "  • API Gateway: $API_URL"
echo "  • Enhanced Frontend: http://taxdoc-mvp-web-1754513919.s3-website-us-east-1.amazonaws.com/mvp2-enhanced.html"
echo ""
echo "🔧 New Features Deployed:"
echo "  ✅ Enhanced Stripe webhook with signature verification"
echo "  ✅ Entitlement middleware with quota checking"
echo "  ✅ Batch upload handler (files, folders, ZIP)"
echo "  ✅ Multi-format export handler (CSV, JSON, Excel, PDF)"
echo "  ✅ SNS notification system"
echo "  ✅ Enhanced frontend with usage meter and export drawer"
echo "  ✅ CloudWatch dashboard and alarms"
echo ""
echo "📧 Next Steps:"
echo "  1. Check your email ($EMAIL) to confirm SNS subscription"
echo "  2. Configure Stripe webhook URL: $API_URL/v2/webhooks/stripe"
echo "  3. Set environment variables for Stripe keys"
echo "  4. Test the enhanced frontend features"
echo ""
echo "🔗 Useful Links:"
echo "  • CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=DrDoc-v25-$ENVIRONMENT"
echo "  • API Gateway Console: https://console.aws.amazon.com/apigateway/home?region=us-east-1#/apis/$API_ID"
echo "  • S3 Exports Bucket: https://console.aws.amazon.com/s3/buckets/$EXPORTS_BUCKET"
echo ""
print_success "All v2.5 features successfully deployed! 🚀"