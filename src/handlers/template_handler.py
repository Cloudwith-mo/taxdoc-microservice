"""
Template Handler - API endpoints for template management
"""

import json
import boto3
from typing import Dict, Any
import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.template_service import TemplateService

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Handle template-related API requests"""
    
    try:
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        template_service = TemplateService()
        
        if http_method == 'POST' and path == '/templates':
            return create_template(event, template_service)
        
        elif http_method == 'GET' and path == '/templates':
            return list_templates(event, template_service)
        
        elif http_method == 'GET' and '/templates/' in path:
            template_id = path.split('/')[-1]
            return get_template(template_id, template_service)
        
        elif http_method == 'PUT' and '/templates/' in path:
            template_id = path.split('/')[-1]
            return update_template(event, template_id, template_service)
        
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Endpoint not found',
                    'method': http_method,
                    'path': path
                })
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal server error'
            })
        }

def create_template(event: Dict[str, Any], template_service: TemplateService) -> Dict[str, Any]:
    """Create a new template"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        if not body.get('name'):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Template name is required'
                })
            }
        
        if not body.get('fields'):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Template fields are required'
                })
            }
        
        # Create template
        result = template_service.create_template(body)
        
        status_code = 201 if result['success'] else 400
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }

def list_templates(event: Dict[str, Any], template_service: TemplateService) -> Dict[str, Any]:
    """List all templates"""
    
    query_params = event.get('queryStringParameters') or {}
    organization_id = query_params.get('organization_id', 'default')
    
    templates = template_service.list_templates(organization_id)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'templates': templates,
            'count': len(templates)
        })
    }

def get_template(template_id: str, template_service: TemplateService) -> Dict[str, Any]:
    """Get a specific template"""
    
    template = template_service.get_template(template_id)
    
    if not template:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Template not found'
            })
        }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(template)
    }

def update_template(event: Dict[str, Any], template_id: str, template_service: TemplateService) -> Dict[str, Any]:
    """Update a template (creates new version)"""
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        if not body.get('fields'):
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Updated fields are required'
                })
            }
        
        result = template_service.create_template_version(template_id, body['fields'])
        
        status_code = 200 if result['success'] else 400
        
        return {
            'statusCode': status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }