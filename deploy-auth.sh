#!/bin/bash

echo "Deploying TaxDoc AI Authentication Service..."

# Create deployment package
cd src/handlers
zip -r auth_handler.zip auth_handler.py

# Deploy Lambda function
aws lambda create-function \
    --function-name DrDoc-Auth-prod \
    --runtime python3.9 \
    --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
    --handler auth_handler.lambda_handler \
    --zip-file fileb://auth_handler.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment Variables='{"DYNAMODB_TABLE":"TaxDoc-Users"}' \
    --description "TaxDoc AI Authentication Service" || \
aws lambda update-function-code \
    --function-name DrDoc-Auth-prod \
    --zip-file fileb://auth_handler.zip

# Update function configuration
aws lambda update-function-configuration \
    --function-name DrDoc-Auth-prod \
    --environment Variables='{"DYNAMODB_TABLE":"TaxDoc-Users"}'

# Create DynamoDB table for users
aws dynamodb create-table \
    --table-name TaxDoc-Users \
    --attribute-definitions \
        AttributeName=email,AttributeType=S \
    --key-schema \
        AttributeName=email,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1 || echo "Table already exists"

# Add API Gateway routes
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='DrDoc-EnhancedApi-prod'].id" --output text)

if [ "$API_ID" != "" ]; then
    echo "Adding auth routes to API Gateway: $API_ID"
    
    # Get root resource ID
    ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query "items[?path=='/'].id" --output text)
    
    # Create /auth resource
    AUTH_RESOURCE_ID=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $ROOT_ID \
        --path-part auth \
        --query 'id' --output text 2>/dev/null || \
        aws apigateway get-resources --rest-api-id $API_ID --query "items[?pathPart=='auth'].id" --output text)
    
    # Create auth endpoints
    for endpoint in register login logout profile; do
        # Create resource
        RESOURCE_ID=$(aws apigateway create-resource \
            --rest-api-id $API_ID \
            --parent-id $AUTH_RESOURCE_ID \
            --path-part $endpoint \
            --query 'id' --output text 2>/dev/null || \
            aws apigateway get-resources --rest-api-id $API_ID --query "items[?pathPart=='$endpoint'].id" --output text)
        
        # Create POST method
        aws apigateway put-method \
            --rest-api-id $API_ID \
            --resource-id $RESOURCE_ID \
            --http-method POST \
            --authorization-type NONE 2>/dev/null || echo "Method exists"
        
        # Set up integration
        aws apigateway put-integration \
            --rest-api-id $API_ID \
            --resource-id $RESOURCE_ID \
            --http-method POST \
            --type AWS_PROXY \
            --integration-http-method POST \
            --uri "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:$(aws sts get-caller-identity --query Account --output text):function:DrDoc-Auth-prod/invocations" 2>/dev/null || echo "Integration exists"
        
        # Add Lambda permission
        aws lambda add-permission \
            --function-name DrDoc-Auth-prod \
            --statement-id "apigateway-auth-$endpoint-$(date +%s)" \
            --action lambda:InvokeFunction \
            --principal apigateway.amazonaws.com \
            --source-arn "arn:aws:execute-api:us-east-1:$(aws sts get-caller-identity --query Account --output text):$API_ID/*/*" 2>/dev/null || echo "Permission exists"
    done
    
    # Deploy API
    aws apigateway create-deployment \
        --rest-api-id $API_ID \
        --stage-name prod \
        --description "Deploy auth endpoints"
    
    echo "Auth service deployed successfully!"
    echo "API Endpoint: https://$API_ID.execute-api.us-east-1.amazonaws.com/prod"
else
    echo "API Gateway not found. Please create the API first."
fi

# Clean up
rm -f auth_handler.zip

echo "Authentication service deployment complete!"