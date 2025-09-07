import boto3
import json
from datetime import datetime
from typing import Dict, Any, Optional

class CloudWatchMetrics:
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = 'TaxDoc'
    
    def put_document_processed(self, form_type: str, processing_time: float, success: bool = True):
        """Track document processing metrics"""
        metrics = [
            {
                'MetricName': 'DocumentsProcessed',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': 1,
                'Unit': 'Count'
            },
            {
                'MetricName': 'ProcessingTime',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': processing_time,
                'Unit': 'Seconds'
            }
        ]
        
        if not success:
            metrics.append({
                'MetricName': 'ProcessingErrors',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': 1,
                'Unit': 'Count'
            })
        
        self.cloudwatch.put_metric_data(Namespace=self.namespace, MetricData=metrics)
    
    def put_extraction_metrics(self, form_type: str, textract_used: bool, claude_used: bool, regex_used: bool):
        """Track which extraction layers were used"""
        metrics = []
        
        if textract_used:
            metrics.append({
                'MetricName': 'TextractUsage',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': 1,
                'Unit': 'Count'
            })
        
        if claude_used:
            metrics.append({
                'MetricName': 'ClaudeUsage',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': 1,
                'Unit': 'Count'
            })
        
        if regex_used:
            metrics.append({
                'MetricName': 'RegexUsage',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': 1,
                'Unit': 'Count'
            })
        
        if metrics:
            self.cloudwatch.put_metric_data(Namespace=self.namespace, MetricData=metrics)
    
    def put_confidence_metrics(self, form_type: str, avg_confidence: float, field_count: int):
        """Track extraction confidence and field coverage"""
        metrics = [
            {
                'MetricName': 'ExtractionConfidence',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': avg_confidence,
                'Unit': 'Percent'
            },
            {
                'MetricName': 'FieldsExtracted',
                'Dimensions': [{'Name': 'FormType', 'Value': form_type}],
                'Value': field_count,
                'Unit': 'Count'
            }
        ]
        
        self.cloudwatch.put_metric_data(Namespace=self.namespace, MetricData=metrics)
    
    def put_cost_metrics(self, textract_cost: float, claude_cost: float, total_cost: float):
        """Track processing costs"""
        metrics = [
            {
                'MetricName': 'TextractCost',
                'Value': textract_cost,
                'Unit': 'None'
            },
            {
                'MetricName': 'ClaudeCost', 
                'Value': claude_cost,
                'Unit': 'None'
            },
            {
                'MetricName': 'TotalProcessingCost',
                'Value': total_cost,
                'Unit': 'None'
            }
        ]
        
        self.cloudwatch.put_metric_data(Namespace=self.namespace, MetricData=metrics)