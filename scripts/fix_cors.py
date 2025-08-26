#!/usr/bin/env python3

import boto3
import json

def fix_cors():
    """Add CORS headers to v2 API Gateway"""
    
    client = boto3.client('apigateway')
    api_id = 'svea4ri2tk'
    
    try:
        # Get all resources
        resources = client.get_resources(restApiId=api_id)
        
        for resource in resources['items']:
            resource_id = resource['id']
            
            # Add OPTIONS method for CORS preflight
            try:
                client.put_method(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    authorizationType='NONE'
                )
                
                # Add method response
                client.put_method_response(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    statusCode='200',
                    responseParameters={
                        'method.response.header.Access-Control-Allow-Headers': False,
                        'method.response.header.Access-Control-Allow-Methods': False,
                        'method.response.header.Access-Control-Allow-Origin': False
                    }
                )
                
                # Add integration
                client.put_integration(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    type='MOCK',
                    requestTemplates={
                        'application/json': '{"statusCode": 200}'
                    }
                )
                
                # Add integration response
                client.put_integration_response(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod='OPTIONS',
                    statusCode='200',
                    responseParameters={
                        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
                
                print(f"✅ Added CORS to resource: {resource.get('pathPart', 'root')}")
                
            except Exception as e:
                if 'ConflictException' not in str(e):
                    print(f"⚠️ Error adding CORS to {resource.get('pathPart', 'root')}: {e}")
        
        # Deploy the changes
        client.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )
        
        print("🚀 CORS configuration deployed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_cors()