#!/usr/bin/env python3
"""
Create CloudWatch Dashboard for TaxDoc Metrics
"""
import boto3
import json

def create_dashboard():
    cloudwatch = boto3.client('cloudwatch')
    
    dashboard_body = {
        "widgets": [
            {
                "type": "metric",
                "x": 0, "y": 0,
                "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["TaxDoc", "DocumentsProcessed", "FormType", "W-2"],
                        [".", ".", ".", "1099-NEC"],
                        [".", ".", ".", "1099-MISC"]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "Documents Processed by Type"
                }
            },
            {
                "type": "metric",
                "x": 12, "y": 0,
                "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["TaxDoc", "ProcessingTime", "FormType", "W-2"],
                        [".", ".", ".", "1099-NEC"]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1",
                    "title": "Average Processing Time (seconds)"
                }
            },
            {
                "type": "metric",
                "x": 0, "y": 6,
                "width": 8, "height": 6,
                "properties": {
                    "metrics": [
                        ["TaxDoc", "TextractUsage"],
                        [".", "ClaudeUsage"],
                        [".", "RegexUsage"]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "Extraction Layer Usage"
                }
            },
            {
                "type": "metric",
                "x": 8, "y": 6,
                "width": 8, "height": 6,
                "properties": {
                    "metrics": [
                        ["TaxDoc", "ExtractionConfidence", "FormType", "W-2"],
                        [".", ".", ".", "1099-NEC"]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1",
                    "title": "Average Extraction Confidence (%)"
                }
            },
            {
                "type": "metric",
                "x": 16, "y": 6,
                "width": 8, "height": 6,
                "properties": {
                    "metrics": [
                        ["TaxDoc", "ProcessingErrors", "FormType", "W-2"],
                        [".", ".", ".", "1099-NEC"]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "Processing Errors"
                }
            },
            {
                "type": "metric",
                "x": 0, "y": 12,
                "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["TaxDoc", "TextractCost"],
                        [".", "ClaudeCost"],
                        [".", "TotalProcessingCost"]
                    ],
                    "period": 300,
                    "stat": "Sum",
                    "region": "us-east-1",
                    "title": "Processing Costs ($)"
                }
            },
            {
                "type": "metric",
                "x": 12, "y": 12,
                "width": 12, "height": 6,
                "properties": {
                    "metrics": [
                        ["TaxDoc", "FieldsExtracted", "FormType", "W-2"],
                        [".", ".", ".", "1099-NEC"]
                    ],
                    "period": 300,
                    "stat": "Average",
                    "region": "us-east-1",
                    "title": "Fields Extracted per Document"
                }
            }
        ]
    }
    
    try:
        response = cloudwatch.put_dashboard(
            DashboardName='TaxDoc-Processing-Metrics',
            DashboardBody=json.dumps(dashboard_body)
        )
        print("✅ Dashboard created successfully!")
        print(f"Dashboard ARN: {response.get('DashboardArn')}")
        print("🌐 View at: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=TaxDoc-Processing-Metrics")
        
    except Exception as e:
        print(f"❌ Failed to create dashboard: {e}")

if __name__ == "__main__":
    create_dashboard()