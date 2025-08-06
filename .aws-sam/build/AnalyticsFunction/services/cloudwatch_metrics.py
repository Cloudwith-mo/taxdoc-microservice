import boto3
import time
from typing import Dict, Any, List

class CloudWatchMetrics:
    """Enhanced CloudWatch metrics service for Dr.Doc monitoring"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = 'DrDoc/Processing'
    
    def put_document_processed(self, document_type: str, processing_time: float, confidence: float):
        """Record document processing metrics"""
        
        metrics = [
            {
                'MetricName': 'DocumentsProcessed',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'DocumentType', 'Value': document_type}
                ]
            },
            {
                'MetricName': 'ProcessingTime',
                'Value': processing_time,
                'Unit': 'Seconds',
                'Dimensions': [
                    {'Name': 'DocumentType', 'Value': document_type}
                ]
            },
            {
                'MetricName': 'ConfidenceScore',
                'Value': confidence,
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'DocumentType', 'Value': document_type}
                ]
            }
        ]
        
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=metrics
        )
    
    def put_layer_usage(self, layers_used: List[str], document_type: str):
        """Record which extraction layers were used"""
        
        for layer in layers_used:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[{
                    'MetricName': 'LayerUsage',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Layer', 'Value': layer},
                        {'Name': 'DocumentType', 'Value': document_type}
                    ]
                }]
            )
    
    def put_error_metric(self, error_type: str, function_name: str):
        """Record processing errors"""
        
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'ProcessingErrors',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'ErrorType', 'Value': error_type},
                    {'Name': 'Function', 'Value': function_name}
                ]
            }]
        )
    
    def put_cost_metric(self, service: str, cost: float):
        """Record service costs for monitoring"""
        
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[{
                'MetricName': 'ServiceCost',
                'Value': cost,
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'Service', 'Value': service}
                ]
            }]
        )