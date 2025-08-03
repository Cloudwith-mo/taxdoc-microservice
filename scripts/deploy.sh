#!/bin/bash

# TaxDoc Microservice Deployment Script

set -e

ENVIRONMENT=${1:-dev}
STACK_NAME="taxdoc-stack-${ENVIRONMENT}"
TEMPLATE_FILE="infrastructure/template.yaml"

echo "Deploying TaxDoc microservice to ${ENVIRONMENT} environment..."

# Validate template
echo "Validating CloudFormation template..."
aws cloudformation validate-template --template-body file://${TEMPLATE_FILE}

# Package and deploy
echo "Packaging and deploying stack..."
sam build --template-file ${TEMPLATE_FILE}

sam deploy \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides Environment=${ENVIRONMENT} \
    --confirm-changeset

# Get outputs
echo "Deployment complete! Getting stack outputs..."
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs' \
    --output table

echo "TaxDoc microservice deployed successfully to ${ENVIRONMENT}!"