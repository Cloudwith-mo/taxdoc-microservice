"""
Schema Designer Service
Generates and validates JSON schemas for document extraction
"""

from typing import Dict, Any, List, Optional

class SchemaDesigner:
    def __init__(self):
        self.default_schemas = self._load_default_schemas()
    
    def create_schema(self, document_type: str, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create JSON schema from field definitions"""
        
        properties = {}
        required_fields = []
        
        for field in fields:
            field_name = field['name']
            field_type = field.get('type', 'string')
            is_required = field.get('required', False)
            
            # Create property definition
            property_def = {
                'type': self._map_field_type(field_type),
                'description': field.get('description', f'{field_name} field')
            }
            
            # Add validation rules
            if field_type == 'number':
                if 'min' in field:
                    property_def['minimum'] = field['min']
                if 'max' in field:
                    property_def['maximum'] = field['max']
            
            elif field_type == 'string':
                if 'pattern' in field:
                    property_def['pattern'] = field['pattern']
                if 'format' in field:
                    property_def['format'] = field['format']
            
            properties[field_name] = property_def
            
            if is_required:
                required_fields.append(field_name)
        
        schema = {
            'type': 'object',
            'properties': properties,
            'required': required_fields,
            'additionalProperties': False,
            'title': f'{document_type} Schema',
            'description': f'JSON schema for {document_type} document extraction'
        }
        
        return schema
    
    def get_default_schema(self, document_type: str) -> Optional[Dict[str, Any]]:
        """Get default schema for known document types"""
        return self.default_schemas.get(document_type)
    
    def validate_extraction_against_schema(self, extracted_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted data against schema"""
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'field_validations': {}
        }
        
        properties = schema.get('properties', {})
        required_fields = schema.get('required', [])
        
        # Check required fields
        for field in required_fields:
            if field not in extracted_data:
                validation_result['errors'].append(f'Required field "{field}" is missing')
                validation_result['is_valid'] = False
        
        # Validate each field
        for field_name, field_value in extracted_data.items():
            if field_name in properties:
                field_validation = self._validate_field(field_name, field_value, properties[field_name])
                validation_result['field_validations'][field_name] = field_validation
                
                if not field_validation['is_valid']:
                    validation_result['is_valid'] = False
                    validation_result['errors'].extend(field_validation['errors'])
        
        return validation_result
    
    def _validate_field(self, field_name: str, value: Any, field_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual field against its schema"""
        
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        expected_type = field_schema.get('type', 'string')
        
        # Type validation
        if value is not None:
            if expected_type == 'number' and not isinstance(value, (int, float)):
                try:
                    float(str(value))
                except ValueError:
                    result['errors'].append(f'{field_name}: Expected number, got {type(value).__name__}')
                    result['is_valid'] = False
            
            elif expected_type == 'string' and not isinstance(value, str):
                result['warnings'].append(f'{field_name}: Expected string, got {type(value).__name__}')
            
            # Pattern validation for strings
            if expected_type == 'string' and 'pattern' in field_schema:
                import re
                if not re.match(field_schema['pattern'], str(value)):
                    result['errors'].append(f'{field_name}: Value does not match required pattern')
                    result['is_valid'] = False
            
            # Range validation for numbers
            if expected_type == 'number':
                try:
                    num_value = float(str(value))
                    if 'minimum' in field_schema and num_value < field_schema['minimum']:
                        result['errors'].append(f'{field_name}: Value below minimum {field_schema["minimum"]}')
                        result['is_valid'] = False
                    
                    if 'maximum' in field_schema and num_value > field_schema['maximum']:
                        result['errors'].append(f'{field_name}: Value above maximum {field_schema["maximum"]}')
                        result['is_valid'] = False
                except ValueError:
                    pass  # Already handled in type validation
        
        return result
    
    def _map_field_type(self, field_type: str) -> str:
        """Map field type to JSON schema type"""
        
        type_mapping = {
            'text': 'string',
            'number': 'number',
            'integer': 'integer',
            'date': 'string',
            'email': 'string',
            'phone': 'string',
            'currency': 'number',
            'percentage': 'number',
            'boolean': 'boolean'
        }
        
        return type_mapping.get(field_type, 'string')
    
    def _load_default_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load default schemas for common document types"""
        
        return {
            'W-2': {
                'type': 'object',
                'properties': {
                    'EmployeeName': {'type': 'string', 'description': 'Employee full name'},
                    'EmployeeSSN': {'type': 'string', 'pattern': r'^\d{3}-\d{2}-\d{4}$', 'description': 'Employee SSN'},
                    'EmployerName': {'type': 'string', 'description': 'Employer name'},
                    'EmployerEIN': {'type': 'string', 'pattern': r'^\d{2}-\d{7}$', 'description': 'Employer EIN'},
                    'Box1_Wages': {'type': 'number', 'minimum': 0, 'description': 'Wages, tips, other compensation'},
                    'Box2_FederalTaxWithheld': {'type': 'number', 'minimum': 0, 'description': 'Federal income tax withheld'},
                    'TaxYear': {'type': 'integer', 'minimum': 2000, 'maximum': 2030, 'description': 'Tax year'}
                },
                'required': ['EmployeeName', 'EmployeeSSN', 'EmployerName', 'Box1_Wages', 'TaxYear']
            },
            
            'Invoice': {
                'type': 'object',
                'properties': {
                    'InvoiceNumber': {'type': 'string', 'description': 'Invoice number'},
                    'InvoiceDate': {'type': 'string', 'format': 'date', 'description': 'Invoice date'},
                    'VendorName': {'type': 'string', 'description': 'Vendor/supplier name'},
                    'TotalAmount': {'type': 'number', 'minimum': 0, 'description': 'Total invoice amount'},
                    'DueDate': {'type': 'string', 'format': 'date', 'description': 'Payment due date'}
                },
                'required': ['InvoiceNumber', 'VendorName', 'TotalAmount']
            },
            
            'Receipt': {
                'type': 'object',
                'properties': {
                    'MerchantName': {'type': 'string', 'description': 'Merchant name'},
                    'PurchaseDate': {'type': 'string', 'format': 'date', 'description': 'Purchase date'},
                    'TotalAmount': {'type': 'number', 'minimum': 0, 'description': 'Total amount paid'},
                    'SalesTax': {'type': 'number', 'minimum': 0, 'description': 'Sales tax amount'}
                },
                'required': ['MerchantName', 'TotalAmount']
            }
        }
    
    def generate_sample_data(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate sample data based on schema"""
        
        sample = {}
        properties = schema.get('properties', {})
        
        for field_name, field_schema in properties.items():
            field_type = field_schema.get('type', 'string')
            
            if field_type == 'string':
                if 'pattern' in field_schema:
                    if 'ssn' in field_name.lower():
                        sample[field_name] = '123-45-6789'
                    elif 'ein' in field_name.lower():
                        sample[field_name] = '12-3456789'
                    else:
                        sample[field_name] = 'Sample Text'
                else:
                    sample[field_name] = 'Sample Text'
            
            elif field_type == 'number':
                sample[field_name] = 1000.00
            
            elif field_type == 'integer':
                sample[field_name] = 2024
            
            elif field_type == 'boolean':
                sample[field_name] = True
        
        return sample