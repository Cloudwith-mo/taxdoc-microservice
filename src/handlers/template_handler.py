import json
import boto3
from typing import Dict, Any
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.template_service import TemplateService
from services.advanced_template_matcher import AdvancedTemplateMatcher

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Template management API handler"""
    
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    try:
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        path_params = event.get('pathParameters') or {}
        
        if http_method == 'OPTIONS':
            return {'statusCode': 200, 'headers': cors_headers, 'body': ''}
        
        template_service = TemplateService()
        
        if http_method == 'GET' and path == '/templates':
            return list_templates(template_service, event, cors_headers)
        elif http_method == 'POST' and path == '/templates':
            return create_template(template_service, event, cors_headers)
        elif http_method == 'GET' and 'template_id' in path_params:
            return get_template(template_service, path_params['template_id'], event, cors_headers)
        elif http_method == 'PUT' and 'template_id' in path_params:
            return update_template(template_service, path_params['template_id'], event, cors_headers)
        elif http_method == 'POST' and '/rollback' in path:
            return rollback_template(template_service, path_params['template_id'], event, cors_headers)
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }

def list_templates(service: TemplateService, event: Dict, headers: Dict) -> Dict:
    """List all templates"""
    query_params = event.get('queryStringParameters') or {}
    document_type = query_params.get('document_type')
    
    templates = service.list_templates(document_type)
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'templates': templates,
            'count': len(templates)
        })
    }

def create_template(service: TemplateService, event: Dict, headers: Dict) -> Dict:
    """Create new template"""
    try:
        body = json.loads(event.get('body', '{}'))
        document_type = body.get('document_type')
        template_data = body.get('template_data')
        created_by = body.get('created_by', 'api')
        
        if not document_type or not template_data:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'document_type and template_data required'})
            }
        
        template_id = service.create_template(document_type, template_data, created_by)
        
        return {
            'statusCode': 201,
            'headers': headers,
            'body': json.dumps({
                'template_id': template_id,
                'message': 'Template created successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }

def get_template(service: TemplateService, template_id: str, event: Dict, headers: Dict) -> Dict:
    """Get specific template"""
    query_params = event.get('queryStringParameters') or {}
    version = query_params.get('version')
    
    if version:
        try:
            version = int(version)
        except ValueError:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid version number'})
            }
    
    template = service.get_template(template_id, version)
    
    if template:
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(template)
        }
    else:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'Template not found'})
        }

def update_template(service: TemplateService, template_id: str, event: Dict, headers: Dict) -> Dict:
    """Update template (creates new version)"""
    try:
        body = json.loads(event.get('body', '{}'))
        template_data = body.get('template_data')
        updated_by = body.get('updated_by', 'api')
        
        if not template_data:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'template_data required'})
            }
        
        new_version = service.update_template(template_id, template_data, updated_by)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'template_id': template_id,
                'new_version': new_version,
                'message': 'Template updated successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except ValueError as e:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }

def rollback_template(service: TemplateService, template_id: str, event: Dict, headers: Dict) -> Dict:
    """Rollback template to previous version"""
    try:
        body = json.loads(event.get('body', '{}'))
        target_version = body.get('target_version')
        
        if not target_version:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'target_version required'})
            }
        
        new_version = service.rollback_template(template_id, int(target_version))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'template_id': template_id,
                'rolled_back_to': target_version,
                'new_version': new_version,
                'message': 'Template rolled back successfully'
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except ValueError as e:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }