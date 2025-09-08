import json

def lambda_handler(event, context):
    """Simple test handler for API Gateway"""
    
    print(f"Received event: {json.dumps(event)}")
    
    # Extract body from API Gateway event
    body = event.get('body', '{}')
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except:
            body = {}
    
    # Mock extracted data based on filename
    filename = body.get('filename', 'unknown')
    mock_data = {
        'employee_name': 'John Doe',
        'employer_name': 'Tech Corp Inc',
        'wages_tips_compensation': '75000.00',
        'federal_income_tax_withheld': '12500.00',
        'social_security_wages': '75000.00',
        'social_security_tax_withheld': '4650.00',
        'medicare_wages': '75000.00',
        'medicare_tax_withheld': '1087.50'
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'DocumentType': 'W-2',
            'ClassificationConfidence': 0.95,
            'Data': mock_data,
            'status': 'success'
        })
    }