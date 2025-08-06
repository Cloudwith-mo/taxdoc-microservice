import json
import boto3
import time
from typing import Dict, Any, List, Optional
from decimal import Decimal

class TemplateService:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('DrDocTemplates-prod')
    
    def create_template(self, document_type: str, template_data: Dict[str, Any], created_by: str = "system") -> str:
        """Create new template with version 1"""
        template_id = f"{document_type}_{int(time.time())}"
        
        template = {
            'TemplateID': template_id,
            'DocumentType': document_type,
            'Version': 1,
            'TemplateData': template_data,
            'CreatedBy': created_by,
            'CreatedAt': int(time.time()),
            'IsActive': True,
            'Status': 'active'
        }
        
        self.table.put_item(Item=template)
        return template_id
    
    def update_template(self, template_id: str, template_data: Dict[str, Any], updated_by: str = "system") -> int:
        """Create new version of existing template"""
        # Get current template
        current = self.get_template(template_id)
        if not current:
            raise ValueError(f"Template {template_id} not found")
        
        new_version = current['Version'] + 1
        
        # Create new version
        new_template = {
            'TemplateID': template_id,
            'DocumentType': current['DocumentType'],
            'Version': new_version,
            'TemplateData': template_data,
            'UpdatedBy': updated_by,
            'UpdatedAt': int(time.time()),
            'PreviousVersion': current['Version'],
            'IsActive': True,
            'Status': 'active'
        }
        
        # Deactivate old version
        self.table.update_item(
            Key={'TemplateID': template_id},
            UpdateExpression='SET IsActive = :false, Status = :inactive',
            ExpressionAttributeValues={':false': False, ':inactive': 'inactive'}
        )
        
        # Add new version
        self.table.put_item(Item=new_template)
        return new_version
    
    def get_template(self, template_id: str, version: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get template by ID and optional version"""
        if version:
            response = self.table.query(
                IndexName='DocumentType-Version-Index',
                KeyConditionExpression='TemplateID = :tid AND Version = :ver',
                ExpressionAttributeValues={':tid': template_id, ':ver': version}
            )
        else:
            response = self.table.get_item(Key={'TemplateID': template_id})
            return response.get('Item')
        
        items = response.get('Items', [])
        return items[0] if items else None
    
    def rollback_template(self, template_id: str, target_version: int) -> bool:
        """Rollback template to specific version"""
        # Get target version
        target = self.get_template(template_id, target_version)
        if not target:
            raise ValueError(f"Version {target_version} not found")
        
        # Create new version based on target
        return self.update_template(
            template_id, 
            target['TemplateData'], 
            f"rollback_to_v{target_version}"
        )
    
    def list_templates(self, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all active templates"""
        if document_type:
            response = self.table.query(
                IndexName='DocumentType-Version-Index',
                KeyConditionExpression='DocumentType = :dt',
                FilterExpression='IsActive = :true',
                ExpressionAttributeValues={':dt': document_type, ':true': True}
            )
        else:
            response = self.table.scan(
                FilterExpression='IsActive = :true',
                ExpressionAttributeValues={':true': True}
            )
        
        return response.get('Items', [])
    
    def get_template_history(self, template_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a template"""
        response = self.table.query(
            KeyConditionExpression='TemplateID = :tid',
            ExpressionAttributeValues={':tid': template_id},
            ScanIndexForward=False  # Latest first
        )
        
        return response.get('Items', [])