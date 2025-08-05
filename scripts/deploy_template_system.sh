#!/bin/bash

# Deploy Template System for DrDoc
# This script deploys the DynamoDB table, API endpoints, and Lambda functions for template management

set -e

ENVIRONMENT=${1:-prod}
AWS_REGION=${2:-us-east-1}

echo "🚀 Deploying DrDoc Template System to $ENVIRONMENT environment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

print_status "AWS CLI configured successfully"

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Step 1: Deploy DynamoDB Templates Table
print_status "Step 1: Deploying DynamoDB Templates Table..."

aws cloudformation deploy \
    --template-file "$PROJECT_ROOT/infrastructure/dynamodb-templates.yaml" \
    --stack-name "DrDoc-Templates-$ENVIRONMENT" \
    --parameter-overrides Environment=$ENVIRONMENT \
    --region $AWS_REGION \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    print_status "✅ DynamoDB Templates Table deployed successfully"
else
    print_error "❌ Failed to deploy DynamoDB Templates Table"
    exit 1
fi

# Step 2: Package and deploy template handler Lambda
print_status "Step 2: Packaging Template Handler Lambda..."

# Create deployment package
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/template-handler"
mkdir -p "$PACKAGE_DIR"

# Copy source files
cp -r "$PROJECT_ROOT/src/handlers/template_handler.py" "$PACKAGE_DIR/"
cp -r "$PROJECT_ROOT/src/services/template_service.py" "$PACKAGE_DIR/"
cp -r "$PROJECT_ROOT/src/services/advanced_template_matcher.py" "$PACKAGE_DIR/"

# Install dependencies
pip install boto3 scikit-learn numpy -t "$PACKAGE_DIR/"

# Create ZIP file
cd "$PACKAGE_DIR"
zip -r "../template-handler.zip" .
cd - > /dev/null

print_status "Template Handler package created: $TEMP_DIR/template-handler.zip"

# Step 3: Deploy Lambda function
print_status "Step 3: Deploying Template Handler Lambda..."

# Check if function exists
FUNCTION_NAME="DrDoc-TemplateHandler-$ENVIRONMENT"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region $AWS_REGION > /dev/null 2>&1; then
    print_status "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$TEMP_DIR/template-handler.zip" \
        --region $AWS_REGION > /dev/null
else
    print_status "Creating new Lambda function..."
    
    # Get the IAM role ARN (assuming it exists from main deployment)
    ROLE_ARN=$(aws iam get-role --role-name "DrDoc-LambdaExecutionRole-$ENVIRONMENT" --query 'Role.Arn' --output text 2>/dev/null || echo "")
    
    if [ -z "$ROLE_ARN" ]; then
        print_warning "Lambda execution role not found. Creating basic role..."
        
        # Create basic execution role
        TRUST_POLICY='{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }'
        
        aws iam create-role \
            --role-name "DrDoc-TemplateHandler-Role-$ENVIRONMENT" \
            --assume-role-policy-document "$TRUST_POLICY" \
            --region $AWS_REGION > /dev/null
        
        # Attach basic execution policy
        aws iam attach-role-policy \
            --role-name "DrDoc-TemplateHandler-Role-$ENVIRONMENT" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
            --region $AWS_REGION
        
        # Create DynamoDB access policy
        DYNAMODB_POLICY='{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan"
                    ],
                    "Resource": "arn:aws:dynamodb:'$AWS_REGION':*:table/DrDocTemplates-'$ENVIRONMENT'*"
                }
            ]
        }'
        
        aws iam put-role-policy \
            --role-name "DrDoc-TemplateHandler-Role-$ENVIRONMENT" \
            --policy-name "DynamoDBAccess" \
            --policy-document "$DYNAMODB_POLICY" \
            --region $AWS_REGION
        
        ROLE_ARN="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/DrDoc-TemplateHandler-Role-$ENVIRONMENT"
        
        print_status "Waiting for IAM role to propagate..."
        sleep 10
    fi
    
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.9 \
        --role "$ROLE_ARN" \
        --handler template_handler.lambda_handler \
        --zip-file "fileb://$TEMP_DIR/template-handler.zip" \
        --environment Variables="{TEMPLATES_TABLE=DrDocTemplates-$ENVIRONMENT}" \
        --timeout 30 \
        --memory-size 256 \
        --region $AWS_REGION > /dev/null
fi

print_status "✅ Template Handler Lambda deployed successfully"

# Step 4: Get existing API Gateway ID
print_status "Step 4: Finding existing API Gateway..."

API_ID=$(aws apigateway get-rest-apis --query "items[?name=='DrDoc-API-$ENVIRONMENT'].id" --output text --region $AWS_REGION)

if [ -z "$API_ID" ] || [ "$API_ID" = "None" ]; then
    print_error "❌ Existing API Gateway not found. Please deploy the main system first."
    exit 1
fi

print_status "Found API Gateway: $API_ID"

# Step 5: Add template endpoints to existing API
print_status "Step 5: Adding template endpoints to API Gateway..."

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources --rest-api-id "$API_ID" --query "items[?path=='/'].id" --output text --region $AWS_REGION)

# Create /templates resource
TEMPLATES_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$ROOT_ID" \
    --path-part "templates" \
    --query 'id' \
    --output text \
    --region $AWS_REGION 2>/dev/null || \
    aws apigateway get-resources \
        --rest-api-id "$API_ID" \
        --query "items[?pathPart=='templates'].id" \
        --output text \
        --region $AWS_REGION)

print_status "Templates resource ID: $TEMPLATES_RESOURCE_ID"

# Create {template_id} resource under /templates
TEMPLATE_ID_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id "$API_ID" \
    --parent-id "$TEMPLATES_RESOURCE_ID" \
    --path-part "{template_id}" \
    --query 'id' \
    --output text \
    --region $AWS_REGION 2>/dev/null || \
    aws apigateway get-resources \
        --rest-api-id "$API_ID" \
        --query "items[?pathPart=='{template_id}'].id" \
        --output text \
        --region $AWS_REGION)

# Get Lambda function ARN
LAMBDA_ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --query 'Configuration.FunctionArn' --output text --region $AWS_REGION)

# Add methods to /templates resource
for METHOD in GET POST; do
    print_status "Adding $METHOD method to /templates..."
    
    aws apigateway put-method \
        --rest-api-id "$API_ID" \
        --resource-id "$TEMPLATES_RESOURCE_ID" \
        --http-method "$METHOD" \
        --authorization-type NONE \
        --region $AWS_REGION > /dev/null 2>&1 || true
    
    aws apigateway put-integration \
        --rest-api-id "$API_ID" \
        --resource-id "$TEMPLATES_RESOURCE_ID" \
        --http-method "$METHOD" \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
        --region $AWS_REGION > /dev/null 2>&1 || true
done

# Add methods to /templates/{template_id} resource
for METHOD in GET PUT; do
    print_status "Adding $METHOD method to /templates/{template_id}..."
    
    aws apigateway put-method \
        --rest-api-id "$API_ID" \
        --resource-id "$TEMPLATE_ID_RESOURCE_ID" \
        --http-method "$METHOD" \
        --authorization-type NONE \
        --region $AWS_REGION > /dev/null 2>&1 || true
    
    aws apigateway put-integration \
        --rest-api-id "$API_ID" \
        --resource-id "$TEMPLATE_ID_RESOURCE_ID" \
        --http-method "$METHOD" \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:$AWS_REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
        --region $AWS_REGION > /dev/null 2>&1 || true\ndone\n\n# Add Lambda permissions for API Gateway\nprint_status \"Adding Lambda permissions for API Gateway...\"\n\naws lambda add-permission \\\n    --function-name \"$FUNCTION_NAME\" \\\n    --statement-id \"api-gateway-templates-$(date +%s)\" \\\n    --action lambda:InvokeFunction \\\n    --principal apigateway.amazonaws.com \\\n    --source-arn \"arn:aws:apigateway:$AWS_REGION::/restapis/$API_ID/*/*\" \\\n    --region $AWS_REGION > /dev/null 2>&1 || true\n\n# Deploy API changes\nprint_status \"Deploying API Gateway changes...\"\n\naws apigateway create-deployment \\\n    --rest-api-id \"$API_ID\" \\\n    --stage-name \"$ENVIRONMENT\" \\\n    --region $AWS_REGION > /dev/null\n\nprint_status \"✅ API Gateway endpoints deployed successfully\"\n\n# Step 6: Clean up temporary files\nrm -rf \"$TEMP_DIR\"\n\n# Step 7: Display deployment summary\nprint_status \"🎉 Template System Deployment Complete!\"\necho \"\"\necho \"📋 Deployment Summary:\"\necho \"   Environment: $ENVIRONMENT\"\necho \"   Region: $AWS_REGION\"\necho \"   DynamoDB Table: DrDocTemplates-$ENVIRONMENT\"\necho \"   Lambda Function: $FUNCTION_NAME\"\necho \"   API Gateway ID: $API_ID\"\necho \"\"\necho \"🔗 Template API Endpoints:\"\necho \"   GET    https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/$ENVIRONMENT/templates\"\necho \"   POST   https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/$ENVIRONMENT/templates\"\necho \"   GET    https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/$ENVIRONMENT/templates/{id}\"\necho \"   PUT    https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/$ENVIRONMENT/templates/{id}\"\necho \"\"\necho \"📖 Usage Examples:\"\necho \"   # List templates\"\necho \"   curl https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/$ENVIRONMENT/templates\"\necho \"\"\necho \"   # Create template\"\necho \"   curl -X POST https://$API_ID.execute-api.$AWS_REGION.amazonaws.com/$ENVIRONMENT/templates \\\\\"\necho \"        -H 'Content-Type: application/json' \\\\\"\necho \"        -d '{\\\"document_type\\\": \\\"W-2\\\", \\\"template_data\\\": {...}}'\"\necho \"\"\nprint_status \"Template system is ready for use! 🚀\""