import boto3
from typing import Dict, Any, List

class TextractOptimizer:
    """Optimized Textract service with cost and performance improvements"""
    
    def __init__(self):
        self.client = boto3.client('textract')
        self.max_sync_size = 1024 * 1024  # 1MB limit for sync processing
    
    def analyze_document_optimized(self, document_bytes: bytes, document_type: str) -> Dict[str, Any]:
        """Optimized document analysis with minimal feature usage"""
        
        # Determine required features based on document type
        features = self._get_required_features(document_type, len(document_bytes))
        
        if len(document_bytes) <= self.max_sync_size:
            # Use synchronous API for small documents
            return self.client.analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=features
            )
        else:
            # Use asynchronous API for larger documents
            raise ValueError("Document too large for synchronous processing")
    
    def start_async_analysis_optimized(self, bucket: str, key: str, document_type: str, sns_topic: str, role_arn: str) -> str:
        """Start optimized async analysis with minimal features"""
        
        features = self._get_required_features(document_type)
        
        response = self.client.start_document_analysis(
            DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}},
            FeatureTypes=features,
            NotificationChannel={
                'SNSTopicArn': sns_topic,
                'RoleArn': role_arn
            },
            JobTag=f'DrDoc-{document_type}'
        )
        
        return response['JobId']
    
    def _get_required_features(self, document_type: str, file_size: int = 0) -> List[str]:
        """Determine minimal required features based on document type"""
        
        # Base features for all documents
        features = []
        
        # Only add TABLES if document type likely contains tables
        table_types = ['bank_statement', 'invoice', '1099', 'w2']
        if any(t in document_type.lower() for t in table_types):
            features.append('TABLES')
        
        # Only add FORMS for structured forms
        form_types = ['w2', '1099', 'tax_form']
        if any(t in document_type.lower() for t in form_types):
            features.append('FORMS')
        
        # Default to basic text extraction if no specific features needed
        if not features:
            return []  # Basic text detection only
        
        return features
    
    def batch_small_documents(self, documents: List[Dict]) -> List[Dict]:
        """Batch process multiple small documents efficiently"""
        
        results = []
        for doc in documents:
            if doc['size'] <= self.max_sync_size:
                try:
                    result = self.analyze_document_optimized(
                        doc['bytes'], 
                        doc['type']
                    )
                    results.append({
                        'document_id': doc['id'],
                        'result': result,
                        'status': 'success'
                    })
                except Exception as e:
                    results.append({
                        'document_id': doc['id'],
                        'error': str(e),
                        'status': 'failed'
                    })
            else:
                results.append({
                    'document_id': doc['id'],
                    'error': 'Document too large for batch processing',
                    'status': 'failed'
                })
        
        return results