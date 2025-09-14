#!/usr/bin/env python3
"""
Deploy chat-facts Lambda function
"""
import os
import json
import zipfile
import boto3
from pathlib import Path

def create_deployment_package():
    """Create a zip file with the Lambda function code"""
    print("Creating deployment package...")
    
    # Create temp directory for deployment
    deploy_dir = Path("/tmp/chat-facts-deploy")
    deploy_dir.mkdir(exist_ok=True)
    
    # Copy handler file
    handler_src = Path("/workspace/src/handlers/chat_facts_handler.py")
    handler_dst = deploy_dir / "lambda_function.py"
    
    # Read and modify the handler to work as standalone Lambda
    with open(handler_src, 'r') as f:
        content = f.read()
    
    # Fix the import to work in Lambda environment
    content = content.replace(
        "from .facts_publisher import",
        "from facts_publisher import"
    )
    
    with open(handler_dst, 'w') as f:
        f.write(content)
    
    # Copy facts_publisher module
    facts_src = Path("/workspace/src/handlers/facts_publisher.py")
    facts_dst = deploy_dir / "facts_publisher.py"
    
    with open(facts_src, 'r') as f:
        content = f.read()
    
    with open(facts_dst, 'w') as f:
        f.write(content)
    
    # Create zip file
    zip_path = Path("/tmp/chat-facts-function.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in deploy_dir.iterdir():
            zipf.write(file, file.name)
    
    print(f"Deployment package created: {zip_path}")
    return zip_path

def deploy_lambda_function(zip_path):
    """Deploy or update the Lambda function"""
    print("Deploying Lambda function...")
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    function_name = 'parsepilot-chat-facts'
    
    with open(zip_path, 'rb') as f:
        zip_data = f.read()
    
    try:
        # Try to update existing function
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_data
        )
        print(f"Lambda function updated: {function_name}")
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        print(f"Creating new Lambda function: {function_name}")
        
        # First, we need to create an IAM role
        iam_client = boto3.client('iam')
        
        role_name = 'parsepilot-chat-facts-role'
        
        try:
            # Create IAM role
            trust_policy = {
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
            }
            
            role_response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description='Role for ParsePilot chat-facts Lambda function'
            )
            
            role_arn = role_response['Role']['Arn']
            
            # Attach policies
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            # Create inline policy for DynamoDB access
            dynamodb_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:Query",
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:Scan"
                        ],
                        "Resource": "arn:aws:dynamodb:us-east-1:*:table/ParsePilot-Facts*"
                    }
                ]
            }
            
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName='DynamoDBAccess',
                PolicyDocument=json.dumps(dynamodb_policy)
            )
            
            print(f"IAM role created: {role_name}")
            
        except iam_client.exceptions.EntityAlreadyExistsException:
            # Role already exists, get its ARN
            role_response = iam_client.get_role(RoleName=role_name)
            role_arn = role_response['Role']['Arn']
            print(f"Using existing IAM role: {role_name}")
        
        # Wait a bit for role to be available
        import time
        time.sleep(10)
        
        # Create Lambda function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_data},
            Description='Chat facts handler for ParsePilot',
            Timeout=30,
            MemorySize=256,
            Environment={
                'Variables': {
                    'FACTS_TABLE_NAME': 'ParsePilot-Facts'
                }
            }
        )
        print(f"Lambda function created: {function_name}")
    
    return response

def setup_api_gateway_integration():
    """Set up API Gateway integration for the Lambda function"""
    print("Setting up API Gateway integration...")
    
    api_client = boto3.client('apigateway', region_name='us-east-1')
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    api_id = 'iljpaj6ogl'  # Your existing API Gateway ID
    
    # Add permission for API Gateway to invoke Lambda
    try:
        lambda_client.add_permission(
            FunctionName='parsepilot-chat-facts',
            StatementId='apigateway-invoke',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f'arn:aws:execute-api:us-east-1:*:{api_id}/*/*'
        )
        print("Lambda invoke permission added for API Gateway")
    except lambda_client.exceptions.ResourceConflictException:
        print("Lambda invoke permission already exists")
    
    print("API Gateway integration setup complete")
    print(f"Endpoint: https://{api_id}.execute-api.us-east-1.amazonaws.com/prod/chat-facts")

def main():
    """Main deployment function"""
    print("Starting chat-facts Lambda deployment...")
    
    try:
        # Check if AWS credentials are configured
        boto3.client('sts').get_caller_identity()
    except Exception as e:
        print(f"Error: AWS credentials not configured. {e}")
        print("Please configure AWS credentials using 'aws configure' or environment variables")
        return 1
    
    try:
        # Create deployment package
        zip_path = create_deployment_package()
        
        # Deploy Lambda function
        deploy_lambda_function(zip_path)
        
        # Setup API Gateway
        setup_api_gateway_integration()
        
        print("\n✅ Deployment successful!")
        print("\nTest your chatbot at: https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/chat-facts")
        
        # Clean up
        os.remove(zip_path)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())