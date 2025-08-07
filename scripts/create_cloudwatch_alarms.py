#!/usr/bin/env python3
"""
Create CloudWatch Alarms for TaxDoc System
"""
import boto3

def create_alarms():
    cloudwatch = boto3.client('cloudwatch')
    
    alarms = [
        {
            'AlarmName': 'TaxDoc-High-Error-Rate',
            'ComparisonOperator': 'GreaterThanThreshold',
            'EvaluationPeriods': 2,
            'MetricName': 'ProcessingErrors',
            'Namespace': 'TaxDoc',
            'Period': 300,
            'Statistic': 'Sum',
            'Threshold': 5.0,
            'ActionsEnabled': True,
            'AlarmDescription': 'Alert when processing errors exceed 5 in 5 minutes',
            'Unit': 'Count'
        },
        {
            'AlarmName': 'TaxDoc-Slow-Processing',
            'ComparisonOperator': 'GreaterThanThreshold',
            'EvaluationPeriods': 2,
            'MetricName': 'ProcessingTime',
            'Namespace': 'TaxDoc',
            'Period': 300,
            'Statistic': 'Average',
            'Threshold': 30.0,
            'ActionsEnabled': True,
            'AlarmDescription': 'Alert when average processing time exceeds 30 seconds',
            'Unit': 'Seconds'
        },
        {
            'AlarmName': 'TaxDoc-Low-Confidence',
            'ComparisonOperator': 'LessThanThreshold',
            'EvaluationPeriods': 3,
            'MetricName': 'ExtractionConfidence',
            'Namespace': 'TaxDoc',
            'Period': 300,
            'Statistic': 'Average',
            'Threshold': 80.0,
            'ActionsEnabled': True,
            'AlarmDescription': 'Alert when extraction confidence drops below 80%',
            'Unit': 'Percent'
        }
    ]
    
    for alarm in alarms:
        try:
            cloudwatch.put_metric_alarm(**alarm)
            print(f"✅ Created alarm: {alarm['AlarmName']}")
        except Exception as e:
            print(f"❌ Failed to create alarm {alarm['AlarmName']}: {e}")

if __name__ == "__main__":
    create_alarms()