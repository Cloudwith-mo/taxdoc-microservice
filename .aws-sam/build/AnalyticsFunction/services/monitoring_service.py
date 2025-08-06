import boto3
from typing import Dict, Any, List

class MonitoringService:
    """CloudWatch monitoring and alerting service"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
    
    def put_custom_metric(self, metric_name: str, value: float, unit: str = 'Count', dimensions: Dict[str, str] = None):
        """Put custom metric to CloudWatch"""
        
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace='DrDoc/Processing',
                MetricData=[metric_data]
            )
            
        except Exception as e:
            print(f"Failed to put metric {metric_name}: {e}")
    
    def log_processing_metrics(self, document_type: str, processing_time: float, confidence: float, layers_used: List[str]):
        """Log processing metrics for monitoring"""
        
        # Processing time metric
        self.put_custom_metric(
            'ProcessingTime',
            processing_time,
            'Seconds',
            {'DocumentType': document_type}
        )
        
        # Confidence score metric
        self.put_custom_metric(
            'ConfidenceScore',
            confidence,
            'None',
            {'DocumentType': document_type}
        )
        
        # Layer usage metrics
        for layer in layers_used:
            self.put_custom_metric(
                'LayerUsage',
                1,
                'Count',
                {'Layer': layer, 'DocumentType': document_type}
            )
    
    def log_error_metric(self, error_type: str, document_type: str = 'Unknown'):
        """Log error metrics"""
        
        self.put_custom_metric(
            'ProcessingErrors',
            1,
            'Count',
            {'ErrorType': error_type, 'DocumentType': document_type}
        )