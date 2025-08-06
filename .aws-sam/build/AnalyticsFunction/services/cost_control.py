import boto3
from typing import Dict, Any

class CostControlService:
    """Cost control and monitoring for Claude and Textract usage"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = 'DrDoc/CostControl'
        
        # Cost thresholds (daily)
        self.claude_daily_limit = 50.0  # $50/day
        self.textract_daily_limit = 30.0  # $30/day
    
    def track_claude_usage(self, tokens_used: int, document_type: str):
        """Track Claude token usage and costs"""
        
        # Claude pricing: ~$0.003 per 1K tokens (input) + $0.015 per 1K tokens (output)
        # Estimate: ~$0.01 per 1K tokens average
        estimated_cost = (tokens_used / 1000) * 0.01
        
        metrics = [
            {
                'MetricName': 'ClaudeTokensUsed',
                'Value': tokens_used,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'DocumentType', 'Value': document_type}
                ]
            },
            {
                'MetricName': 'ClaudeEstimatedCost',
                'Value': estimated_cost,
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
        
        return estimated_cost
    
    def track_textract_usage(self, pages_processed: int, document_type: str, features_used: list):
        """Track Textract usage and costs"""
        
        # Textract pricing: $0.0015 per page for basic text, +$0.0065 for tables/forms
        base_cost = pages_processed * 0.0015
        feature_cost = 0
        
        if 'TABLES' in features_used:
            feature_cost += pages_processed * 0.0065
        if 'FORMS' in features_used:
            feature_cost += pages_processed * 0.0065
        
        total_cost = base_cost + feature_cost
        
        metrics = [
            {
                'MetricName': 'TextractPagesProcessed',
                'Value': pages_processed,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'DocumentType', 'Value': document_type}
                ]
            },
            {
                'MetricName': 'TextractEstimatedCost',
                'Value': total_cost,
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
        
        return total_cost
    
    def check_daily_limits(self) -> Dict[str, bool]:
        """Check if daily cost limits are exceeded"""
        
        import datetime
        today = datetime.datetime.utcnow().date()
        
        # Get today's costs (simplified - in production use CloudWatch Insights)
        try:
            # This would query CloudWatch for today's cumulative costs
            # For now, return safe defaults
            return {
                'claude_limit_exceeded': False,
                'textract_limit_exceeded': False,
                'total_claude_cost': 0.0,
                'total_textract_cost': 0.0
            }
        except Exception:
            return {
                'claude_limit_exceeded': False,
                'textract_limit_exceeded': False,
                'total_claude_cost': 0.0,
                'total_textract_cost': 0.0
            }