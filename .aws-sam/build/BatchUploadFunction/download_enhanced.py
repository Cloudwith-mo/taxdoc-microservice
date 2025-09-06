import json
import boto3
import csv
import io
from datetime import datetime
import xlsxwriter

def lambda_handler(event, context):
    """Enhanced download with multiple formats and email delivery"""
    
    try:
        # Parse request
        doc_id = event.get('pathParameters', {}).get('doc_id')
        format_type = event.get('queryStringParameters', {}).get('format', 'json')
        email_to = event.get('queryStringParameters', {}).get('email')
        
        if not doc_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing document ID'})
            }
        
        # Get document from DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('DrDocDocuments-prod')
        
        response = table.get_item(Key={'document_id': doc_id})
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Document not found'})
            }
        
        document = response['Item']
        extracted_data = document.get('extracted_data', {})
        
        # Generate file based on format
        if format_type.lower() == 'csv':
            file_content, content_type = generate_csv(extracted_data, document)
            filename = f"{doc_id}_extracted.csv"
        elif format_type.lower() == 'excel':
            file_content, content_type = generate_excel(extracted_data, document)
            filename = f"{doc_id}_extracted.xlsx"
        else:  # JSON
            file_content = json.dumps({
                'document_id': doc_id,
                'filename': document.get('filename'),
                'document_type': document.get('document_type'),
                'extracted_data': extracted_data,
                'confidence_scores': document.get('confidence_scores', {}),
                'processed_at': document.get('upload_timestamp')
            }, indent=2)
            content_type = 'application/json'
            filename = f"{doc_id}_extracted.json"
        
        # If email requested, send via SES
        if email_to:
            send_email_with_attachment(email_to, filename, file_content, content_type, document)
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'message': f'File sent to {email_to}'})
            }
        
        # Return file for download
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename="{filename}"'
            },
            'body': file_content,
            'isBase64Encoded': format_type.lower() == 'excel'
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

def generate_csv(extracted_data, document):
    """Generate CSV format"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Field', 'Value', 'Confidence'])
    
    # Data rows
    confidence_scores = document.get('confidence_scores', {})
    for field, value in extracted_data.items():
        confidence = confidence_scores.get(field, 'N/A')
        writer.writerow([field.replace('_', ' ').title(), value, f"{confidence}%"])
    
    return output.getvalue(), 'text/csv'

def generate_excel(extracted_data, document):
    """Generate Excel format"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Extracted Data')
    
    # Headers
    bold = workbook.add_format({'bold': True})
    worksheet.write('A1', 'Field', bold)
    worksheet.write('B1', 'Value', bold)
    worksheet.write('C1', 'Confidence', bold)
    
    # Data
    confidence_scores = document.get('confidence_scores', {})
    row = 1
    for field, value in extracted_data.items():
        confidence = confidence_scores.get(field, 'N/A')
        worksheet.write(row, 0, field.replace('_', ' ').title())
        worksheet.write(row, 1, str(value))
        worksheet.write(row, 2, f"{confidence}%")
        row += 1
    
    workbook.close()
    output.seek(0)
    
    import base64
    return base64.b64encode(output.read()).decode(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def send_email_with_attachment(email_to, filename, file_content, content_type, document):
    """Send email with file attachment"""
    ses = boto3.client('ses')
    
    # Create email with attachment
    msg = f"""
    Your TaxDoc extraction results are ready!
    
    Document: {document.get('filename')}
    Type: {document.get('document_type')}
    Processed: {document.get('upload_timestamp')}
    
    Please find the extracted data attached.
    
    Best regards,
    TaxDoc Team
    """
    
    try:
        ses.send_email(
            Source='noreply@taxdoc.com',
            Destination={'ToAddresses': [email_to]},
            Message={
                'Subject': {'Data': f'TaxDoc Results - {document.get("filename")}'},
                'Body': {'Text': {'Data': msg}}
            }
        )
    except Exception as e:
        print(f"Email send failed: {e}")
        # Continue without failing the request