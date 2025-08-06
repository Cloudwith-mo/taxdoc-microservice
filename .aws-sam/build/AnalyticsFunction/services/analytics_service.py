import boto3
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

class AnalyticsService:
    """Advanced analytics and processing insights"""
    
    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch')
        self.dynamodb = boto3.resource('dynamodb')
        
    def track_processing_event(self, event_data: Dict[str, Any]):
        """Track document processing events"""
        
        # Send custom metrics to CloudWatch
        metrics = [
            {
                'MetricName': 'DocumentsProcessed',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'DocumentType', 'Value': event_data.get('document_type', 'Unknown')},
                    {'Name': 'ProcessingStatus', 'Value': event_data.get('status', 'Unknown')}
                ]
            },
            {
                'MetricName': 'ProcessingTime',
                'Value': event_data.get('processing_time', 0),
                'Unit': 'Seconds',
                'Dimensions': [{'Name': 'DocumentType', 'Value': event_data.get('document_type', 'Unknown')}]
            },
            {
                'MetricName': 'ExtractionAccuracy',
                'Value': event_data.get('confidence', 0) * 100,
                'Unit': 'Percent',
                'Dimensions': [{'Name': 'DocumentType', 'Value': event_data.get('document_type', 'Unknown')}]
            }
        ]
        
        try:
            self.cloudwatch.put_metric_data(
                Namespace='TaxDoc/Processing',
                MetricData=metrics
            )
        except Exception as e:
            print(f"Failed to send metrics: {e}")
    
    def get_processing_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get processing insights and trends"""
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        try:
            # Get processing success rates
            success_rate = self._get_metric_stats('DocumentsProcessed', start_time, end_time, 'ProcessingStatus', 'Success')
            total_processed = self._get_metric_stats('DocumentsProcessed', start_time, end_time)
            
            # Get document type trends
            doc_types = self._get_document_type_trends(start_time, end_time)
            
            # Get average processing times
            avg_processing_time = self._get_metric_stats('ProcessingTime', start_time, end_time)
            
            # Get accuracy trends
            accuracy_trend = self._get_metric_stats('ExtractionAccuracy', start_time, end_time)
            
            return {
                "period_days": days,
                "total_documents": total_processed.get('Sum', 0),
                "success_rate": (success_rate.get('Sum', 0) / max(total_processed.get('Sum', 1), 1)) * 100,
                "avg_processing_time": avg_processing_time.get('Average', 0),
                "avg_accuracy": accuracy_trend.get('Average', 0),
                "document_type_breakdown": doc_types,
                "cost_estimate": self._calculate_cost_estimate(total_processed.get('Sum', 0)),
                "recommendations": self._generate_recommendations(success_rate, accuracy_trend, avg_processing_time)
            }
            
        except Exception as e:
            print(f"Failed to get insights: {e}")
            return {"error": str(e)}
    
    def get_team_productivity_metrics(self) -> Dict[str, Any]:
        """Get team productivity insights"""
        
        # Mock data for demo - in production, integrate with user management
        return {
            "active_users": 25,
            "documents_per_user_avg": 12.5,
            "top_performers": [
                {"user": "analyst_1", "documents": 45, "accuracy": 98.2},
                {"user": "analyst_2", "documents": 38, "accuracy": 97.8},
                {"user": "analyst_3", "documents": 32, "accuracy": 99.1}
            ],
            "peak_usage_hours": ["9-10 AM", "2-3 PM", "4-5 PM"],
            "efficiency_score": 87.5,
            "time_saved_hours": 156.7
        }
    
    def get_cost_optimization_insights(self) -> Dict[str, Any]:
        """Analyze costs and optimization opportunities"""
        
        return {
            "current_monthly_cost": 245.67,
            "cost_per_document": 0.012,
            "optimization_opportunities": [
                {
                    "area": "Textract Usage",
                    "potential_savings": "$45/month",
                    "recommendation": "Use async processing for multi-page documents"
                },
                {
                    "area": "Claude API Calls", 
                    "potential_savings": "$23/month",
                    "recommendation": "Skip LLM for high-confidence Textract results"
                },
                {
                    "area": "Storage Costs",
                    "potential_savings": "$8/month", 
                    "recommendation": "Implement automatic cleanup of processed files"
                }
            ],
            "cost_trend": "increasing",
            "budget_utilization": 67.3
        }
    
    def _get_metric_stats(self, metric_name: str, start_time: datetime, end_time: datetime, 
                         dimension_name: str = None, dimension_value: str = None) -> Dict[str, float]:
        """Get CloudWatch metric statistics"""
        
        try:
            dimensions = []
            if dimension_name and dimension_value:
                dimensions = [{'Name': dimension_name, 'Value': dimension_value}]
            
            response = self.cloudwatch.get_metric_statistics(
                Namespace='TaxDoc/Processing',
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Sum', 'Average', 'Maximum']
            )
            
            if response['Datapoints']:
                latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                return {
                    'Sum': latest.get('Sum', 0),
                    'Average': latest.get('Average', 0),
                    'Maximum': latest.get('Maximum', 0)
                }
            
        except Exception as e:
            print(f"Failed to get metric stats: {e}")
        
        return {'Sum': 0, 'Average': 0, 'Maximum': 0}
    
    def _get_document_type_trends(self, start_time: datetime, end_time: datetime) -> Dict[str, int]:
        """Get document type processing trends"""
        
        # Mock data - in production, query actual metrics
        return {
            "W-2": 145,
            "1099-NEC": 89,
            "1099-INT": 34,
            "1099-DIV": 23,
            "1099-MISC": 18,
            "Other": 12
        }
    
    def _calculate_cost_estimate(self, total_docs: int) -> Dict[str, float]:
        """Calculate processing cost estimates"""
        
        textract_cost = total_docs * 0.0015  # $0.0015 per page
        claude_cost = total_docs * 0.003     # ~$0.003 per document
        lambda_cost = total_docs * 0.0001    # Lambda execution
        
        return {
            "textract": textract_cost,
            "claude": claude_cost, 
            "lambda": lambda_cost,
            "total": textract_cost + claude_cost + lambda_cost
        }
    
    def _generate_recommendations(self, success_rate: Dict, accuracy: Dict, processing_time: Dict) -> List[str]:
        """Generate optimization recommendations"""
        
        recommendations = []
        
        if success_rate.get('Sum', 0) < 95:
            recommendations.append("Consider improving error handling - success rate below 95%")
        
        if accuracy.get('Average', 0) < 90:
            recommendations.append("Review Claude prompts - accuracy below 90%")
        
        if processing_time.get('Average', 0) > 10:
            recommendations.append("Optimize processing pipeline - average time over 10 seconds")
        
        if not recommendations:
            recommendations.append("System performing well - no immediate optimizations needed")
        
        return recommendations