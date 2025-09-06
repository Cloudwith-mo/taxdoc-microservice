import json
import boto3
import os
import uuid
import zipfile
import io
import csv
from datetime import datetime, timedelta
from entitlement_middleware import check_entitlements
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

@check_entitlements(required_feature='exports', quota_check=False)
def lambda_handler(event, context):
    """
    Handle document exports in multiple formats
    """
    
    try:
        user_data = event.get('user_data', {})
        user_email = user_data.get('email')
        allowed_formats = user_data.get('features', {}).get('exports', ['csv'])
        
        # Parse request
        query_params = event.get('queryStringParameters') or {}
        doc_id = query_params.get('docId')
        export_format = query_params.get('format', 'csv').lower()
        export_type = query_params.get('type', 'single')  # 'single', 'all', 'bulk'
        
        # Validate format
        if export_format not in allowed_formats:
            return {
                'statusCode': 402,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Export format not available',
                    'available_formats': allowed_formats,
                    'upgrade_url': '/subscriptions'
                })
            }
        
        if export_type == 'all':
            return export_all_documents(user_email, export_format)
        elif export_type == 'bulk':
            doc_ids = query_params.get('docIds', '').split(',')
            return export_bulk_documents(user_email, doc_ids, export_format)
        else:
            return export_single_document(doc_id, export_format, user_email)
            
    except Exception as e:
        print(f"Export error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def export_single_document(doc_id, export_format, user_email):
    """Export single document"""
    
    try:
        # Get document data
        doc_data = get_document_data(doc_id)
        if not doc_data:
            raise Exception('Document not found')
        
        # Generate export based on format
        if export_format == 'csv':
            export_content = generate_csv(doc_data)
            content_type = 'text/csv'
            file_extension = 'csv'
        elif export_format == 'json':
            export_content = generate_json(doc_data)
            content_type = 'application/json'
            file_extension = 'json'
        elif export_format == 'xlsx':
            export_content = generate_xlsx(doc_data)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            file_extension = 'xlsx'
        elif export_format == 'pdf':
            export_content = generate_pdf_summary(doc_data)
            content_type = 'application/pdf'
            file_extension = 'pdf'
        else:
            raise Exception(f'Unsupported format: {export_format}')
        
        # Store in S3 exports bucket
        export_url = store_export_file(
            export_content, 
            f"{doc_id}_export.{file_extension}",
            content_type,
            user_email
        )
        
        # Log export activity
        log_export_activity(user_email, doc_id, export_format, 'single')
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'export_url': export_url,
                'format': export_format,
                'expires_in': '15 minutes',
                'document_id': doc_id
            })
        }
        
    except Exception as e:
        print(f"Single export error: {str(e)}")
        raise e

def export_all_documents(user_email, export_format):
    """Export all user documents as ZIP"""
    
    try:
        # Get all user documents
        documents = get_user_documents(user_email)
        if not documents:
            raise Exception('No documents found')
        
        # Create ZIP with all exports
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for doc in documents:
                try:
                    # Generate export for each document
                    if export_format == 'csv':
                        content = generate_csv(doc)
                        filename = f"{doc['document_id']}_export.csv"
                    elif export_format == 'json':
                        content = generate_json(doc)
                        filename = f"{doc['document_id']}_export.json"
                    elif export_format == 'xlsx':
                        content = generate_xlsx(doc)
                        filename = f"{doc['document_id']}_export.xlsx"
                    elif export_format == 'pdf':
                        content = generate_pdf_summary(doc)
                        filename = f"{doc['document_id']}_summary.pdf"
                    
                    # Add to ZIP
                    zip_file.writestr(filename, content)
                    
                except Exception as e:
                    print(f"Error exporting document {doc.get('document_id')}: {e}")
                    continue
        
        zip_content = zip_buffer.getvalue()
        
        # Store ZIP in S3
        export_url = store_export_file(
            zip_content,
            f"all_documents_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip",
            'application/zip',
            user_email
        )
        
        # Log export activity
        log_export_activity(user_email, 'all', export_format, 'bulk')
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'export_url': export_url,
                'format': f'{export_format}_zip',
                'document_count': len(documents),
                'expires_in': '15 minutes'
            })
        }
        
    except Exception as e:
        print(f"Export all error: {str(e)}")
        raise e

def export_bulk_documents(user_email, doc_ids, export_format):
    """Export multiple specific documents"""
    
    try:
        if not doc_ids or not doc_ids[0]:
            raise Exception('No document IDs provided')
        
        # Get specified documents
        documents = []
        for doc_id in doc_ids:
            doc_data = get_document_data(doc_id.strip())
            if doc_data:
                documents.append(doc_data)
        
        if not documents:
            raise Exception('No valid documents found')
        
        # Create ZIP with selected exports
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for doc in documents:
                try:
                    # Generate export for each document
                    if export_format == 'csv':
                        content = generate_csv(doc)
                        filename = f"{doc['document_id']}_export.csv"
                    elif export_format == 'json':
                        content = generate_json(doc)
                        filename = f"{doc['document_id']}_export.json"
                    elif export_format == 'xlsx':
                        content = generate_xlsx(doc)
                        filename = f"{doc['document_id']}_export.xlsx"
                    elif export_format == 'pdf':
                        content = generate_pdf_summary(doc)
                        filename = f"{doc['document_id']}_summary.pdf"
                    
                    # Add to ZIP
                    zip_file.writestr(filename, content)
                    
                except Exception as e:
                    print(f"Error exporting document {doc.get('document_id')}: {e}")
                    continue
        
        zip_content = zip_buffer.getvalue()
        
        # Store ZIP in S3
        export_url = store_export_file(
            zip_content,
            f"selected_documents_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip",
            'application/zip',
            user_email
        )
        
        # Log export activity
        log_export_activity(user_email, ','.join(doc_ids), export_format, 'bulk')
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'export_url': export_url,
                'format': f'{export_format}_zip',
                'document_count': len(documents),
                'expires_in': '15 minutes'
            })
        }
        
    except Exception as e:
        print(f"Bulk export error: {str(e)}")
        raise e

def generate_csv(doc_data):
    """Generate CSV export"""
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Field', 'Value', 'Confidence'])
    
    # Write data
    extracted_data = doc_data.get('data', {})
    confidence_scores = doc_data.get('confidence_scores', {})
    
    for field, value in extracted_data.items():
        if field in ['confidence_scores', 'layers_used', 'extraction_method']:
            continue
        
        confidence = confidence_scores.get(field, 0.95)
        writer.writerow([
            format_field_name(field),
            str(value),
            f"{int(confidence * 100)}%"
        ])
    
    return output.getvalue().encode('utf-8')

def generate_json(doc_data):
    """Generate JSON export"""
    
    export_data = {
        'document_info': {
            'document_id': doc_data.get('document_id'),
            'document_type': doc_data.get('document_type'),
            'processed_at': doc_data.get('processed_at'),
            'filename': doc_data.get('filename')
        },
        'extracted_data': doc_data.get('data', {}),
        'confidence_scores': doc_data.get('confidence_scores', {}),
        'ai_insights': doc_data.get('ai_insights'),
        'sentiment_analysis': doc_data.get('sentiment_analysis')
    }
    
    return json.dumps(export_data, indent=2).encode('utf-8')

def generate_xlsx(doc_data):
    """Generate Excel export"""
    
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Extracted Data')
    
    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white'
    })
    
    high_conf_format = workbook.add_format({'bg_color': '#C6EFCE'})
    med_conf_format = workbook.add_format({'bg_color': '#FFEB9C'})
    low_conf_format = workbook.add_format({'bg_color': '#FFC7CE'})
    
    # Write headers
    worksheet.write(0, 0, 'Field', header_format)
    worksheet.write(0, 1, 'Value', header_format)
    worksheet.write(0, 2, 'Confidence', header_format)
    
    # Write data
    extracted_data = doc_data.get('data', {})
    confidence_scores = doc_data.get('confidence_scores', {})
    
    row = 1
    for field, value in extracted_data.items():
        if field in ['confidence_scores', 'layers_used', 'extraction_method']:
            continue
        
        confidence = confidence_scores.get(field, 0.95)
        
        # Choose format based on confidence
        if confidence >= 0.9:
            cell_format = high_conf_format
        elif confidence >= 0.7:
            cell_format = med_conf_format
        else:
            cell_format = low_conf_format
        
        worksheet.write(row, 0, format_field_name(field), cell_format)
        worksheet.write(row, 1, str(value), cell_format)
        worksheet.write(row, 2, f"{int(confidence * 100)}%", cell_format)
        
        row += 1
    
    # Auto-adjust column widths
    worksheet.set_column(0, 0, 25)
    worksheet.set_column(1, 1, 30)
    worksheet.set_column(2, 2, 12)
    
    workbook.close()
    output.seek(0)
    
    return output.getvalue()

def generate_pdf_summary(doc_data):
    """Generate PDF summary"""
    
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50')
    )
    
    title = Paragraph(f"Document Summary: {doc_data.get('document_type', 'Unknown')}", title_style)
    story.append(title)
    
    # Document info
    info_data = [
        ['Document ID:', doc_data.get('document_id', 'N/A')],
        ['Filename:', doc_data.get('filename', 'N/A')],
        ['Processed:', doc_data.get('processed_at', 'N/A')],
        ['Document Type:', doc_data.get('document_type', 'N/A')]
    ]
    
    info_table = Table(info_data, colWidths=[2*72, 4*72])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Extracted data
    story.append(Paragraph("Extracted Data", styles['Heading2']))
    
    extracted_data = doc_data.get('data', {})
    confidence_scores = doc_data.get('confidence_scores', {})
    
    data_rows = [['Field', 'Value', 'Confidence']]
    
    for field, value in extracted_data.items():
        if field in ['confidence_scores', 'layers_used', 'extraction_method']:
            continue
        
        confidence = confidence_scores.get(field, 0.95)
        data_rows.append([
            format_field_name(field),
            str(value)[:50] + ('...' if len(str(value)) > 50 else ''),
            f"{int(confidence * 100)}%"
        ])
    
    data_table = Table(data_rows, colWidths=[2*72, 3*72, 1*72])
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    story.append(data_table)
    
    # AI Insights if available
    if doc_data.get('ai_insights'):
        story.append(Spacer(1, 20))
        story.append(Paragraph("AI Insights", styles['Heading2']))
        story.append(Paragraph(doc_data['ai_insights'].get('summary', ''), styles['Normal']))
    
    doc.build(story)
    output.seek(0)
    
    return output.getvalue()

def store_export_file(content, filename, content_type, user_email):
    """Store export file in S3 and return presigned URL"""
    
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('EXPORTS_BUCKET', 'drdoc-exports-prod-995805900737')
        
        # Generate S3 key
        s3_key = f"exports/{user_email}/{datetime.utcnow().strftime('%Y/%m/%d')}/{filename}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
            Metadata={
                'user_email': user_email,
                'created_at': datetime.utcnow().isoformat()
            }
        )
        
        # Generate presigned URL (15 minutes)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=900  # 15 minutes
        )
        
        return presigned_url
        
    except Exception as e:
        print(f"Error storing export file: {e}")
        raise e

def get_document_data(doc_id):
    """Get document data from DynamoDB"""
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('RESULTS_TABLE', 'DrDocDocuments-prod'))
        
        response = table.get_item(Key={'document_id': doc_id})
        
        if 'Item' in response:
            return response['Item']
        
        return None
        
    except Exception as e:
        print(f"Error getting document data: {e}")
        return None

def get_user_documents(user_email):
    """Get all documents for user"""
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('RESULTS_TABLE', 'DrDocDocuments-prod'))
        
        # Scan for user documents (in production, use GSI)
        response = table.scan(
            FilterExpression='user_email = :email',
            ExpressionAttributeValues={':email': user_email}
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Error getting user documents: {e}")
        return []

def log_export_activity(user_email, doc_id, export_format, export_type):
    """Log export activity"""
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ.get('EXPORT_LOGS_TABLE', 'DrDocExportLogs-prod'))
        
        table.put_item(
            Item={
                'log_id': str(uuid.uuid4()),
                'user_email': user_email,
                'document_id': doc_id,
                'export_format': export_format,
                'export_type': export_type,
                'timestamp': datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        print(f"Error logging export activity: {e}")

def format_field_name(field):
    """Format field name for display"""
    return field.replace('_', ' ').title()

def get_cors_headers():
    """Get CORS headers"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

# Email export handler
@check_entitlements(required_feature='exports', quota_check=False)
def email_export_handler(event, context):
    """Send export via email"""
    
    try:
        user_data = event.get('user_data', {})
        user_email = user_data.get('email')
        
        body = json.loads(event.get('body', '{}'))
        doc_id = body.get('doc_id')
        export_format = body.get('format', 'csv')
        recipient_email = body.get('email', user_email)
        
        # Generate export
        doc_data = get_document_data(doc_id)
        if not doc_data:
            raise Exception('Document not found')
        
        # Create export file
        if export_format == 'csv':
            export_content = generate_csv(doc_data)
            content_type = 'text/csv'
            file_extension = 'csv'
        elif export_format == 'json':
            export_content = generate_json(doc_data)
            content_type = 'application/json'
            file_extension = 'json'
        else:
            raise Exception(f'Unsupported email format: {export_format}')
        
        # Store in S3
        export_url = store_export_file(
            export_content,
            f"{doc_id}_export.{file_extension}",
            content_type,
            user_email
        )
        
        # Send email via SES
        send_export_email(recipient_email, export_url, doc_data, export_format)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': f'Export sent to {recipient_email}',
                'format': export_format
            })
        }
        
    except Exception as e:
        print(f"Email export error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        }

def send_export_email(recipient_email, export_url, doc_data, export_format):
    """Send export email via SES"""
    
    try:
        ses_client = boto3.client('ses')
        
        subject = f"TaxDoc Export: {doc_data.get('document_type', 'Document')}"
        
        body_text = f"""
Your document export is ready!

Document: {doc_data.get('filename', 'Unknown')}
Type: {doc_data.get('document_type', 'Unknown')}
Format: {export_format.upper()}

Download Link: {export_url}

Note: This link expires in 15 minutes for security.

Best regards,
TaxDoc Team
        """
        
        body_html = f"""
<html>
<body>
    <h2>Your TaxDoc Export is Ready!</h2>
    
    <p><strong>Document:</strong> {doc_data.get('filename', 'Unknown')}</p>
    <p><strong>Type:</strong> {doc_data.get('document_type', 'Unknown')}</p>
    <p><strong>Format:</strong> {export_format.upper()}</p>
    
    <p><a href="{export_url}" style="background-color: #4472C4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Download Export</a></p>
    
    <p><em>Note: This link expires in 15 minutes for security.</em></p>
    
    <p>Best regards,<br>TaxDoc Team</p>
</body>
</html>
        """
        
        ses_client.send_email(
            Source='noreply@taxflowsai.com',
            Destination={'ToAddresses': [recipient_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': body_text},
                    'Html': {'Data': body_html}
                }
            }
        )
        
        print(f"Export email sent to {recipient_email}")
        
    except Exception as e:
        print(f"Error sending export email: {e}")
        raise e