#!/usr/bin/env python3

import boto3
import json

def create_v2_dashboard():
    """Create CloudWatch dashboard for v2.0 monitoring"""
    
    cloudwatch = boto3.client('cloudwatch')
    
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Cognito", "SignUpSuccesses", "UserPool", "DrDoc-UserPool-prod"],
                        [".", "SignInSuccesses", ".", "."],
                        [".", "SignUpThrottles", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "User Authentication Metrics"
                }
            },
            {
                "type": "metric", 
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Invocations", "FunctionName", "DrDoc-StripeHandler-prod"],
                        [".", "Errors", ".", "."],
                        [".", "Duration", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1", 
                    "title": "Payment Processing"
                }
            },
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        ["AWS/Lambda", "Invocations", "FunctionName", "DrDoc-EnhancedChatbot-prod"],
                        [".", "Errors", ".", "."]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "AI Chat Usage"
                }
            },
            {
                "type": "log",
                "properties": {
                    "query": "SOURCE '/aws/lambda/DrDoc-StripeHandler-prod'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 20",
                    "region": "us-east-1",
                    "title": "Payment Errors",
                    "view": "table"
                }
            }
        ]
    }
    
    try:
        response = cloudwatch.put_dashboard(
            DashboardName='TaxDoc-v2-Monitoring',
            DashboardBody=json.dumps(dashboard_body)
        )
        print("✅ Dashboard created successfully")
        print(f"🔗 View at: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=TaxDoc-v2-Monitoring")
        return True
    except Exception as e:
        print(f"❌ Error creating dashboard: {e}")
        return False

def create_v2_alarms():
    """Create CloudWatch alarms for v2.0"""
    
    cloudwatch = boto3.client('cloudwatch')
    
    alarms = [
        {
            'AlarmName': 'TaxDoc-v2-AuthFailures',
            'ComparisonOperator': 'GreaterThanThreshold',
            'EvaluationPeriods': 2,
            'MetricName': 'SignInErrors',
            'Namespace': 'AWS/Cognito',
            'Period': 300,
            'Statistic': 'Sum',
            'Threshold': 10.0,
            'ActionsEnabled': True,
            'AlarmDescription': 'High authentication failure rate',
            'Dimensions': [
                {
                    'Name': 'UserPool',
                    'Value': 'DrDoc-UserPool-prod'
                }
            ]
        },
        {
            'AlarmName': 'TaxDoc-v2-PaymentErrors', 
            'ComparisonOperator': 'GreaterThanThreshold',
            'EvaluationPeriods': 1,
            'MetricName': 'Errors',
            'Namespace': 'AWS/Lambda',
            'Period': 300,
            'Statistic': 'Sum', 
            'Threshold': 5.0,
            'ActionsEnabled': True,
            'AlarmDescription': 'Payment processing errors',
            'Dimensions': [
                {
                    'Name': 'FunctionName',
                    'Value': 'DrDoc-StripeHandler-prod'
                }
            ]
        }
    ]
    
    for alarm in alarms:
        try:
            cloudwatch.put_metric_alarm(**alarm)
            print(f"✅ Created alarm: {alarm['AlarmName']}")
        except Exception as e:
            print(f"❌ Error creating alarm {alarm['AlarmName']}: {e}")

if __name__ == "__main__":
    print("🔧 Setting up TaxDoc v2.0 monitoring...")
    
    create_v2_dashboard()
    create_v2_alarms()
    
    print("\n📊 Monitoring setup complete!")
    print("Key metrics to watch:")
    print("- User registration/login rates")
    print("- Payment success/failure rates") 
    print("- AI chat usage patterns")
    print("- Error rates across all services")