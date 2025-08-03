# TaxDoc Document-Ingestion Microservice

An AWS-based microservice that automatically ingests tax-related documents (receipts, forms, statements), extracts structured data using OCR, and outputs JSON format for integration with TaxFlowsAI.

## Architecture Overview

Event-driven, serverless pipeline using AWS managed services:
- **S3** → Document storage and upload triggers
- **Lambda** → Processing orchestration  
- **Textract** → OCR and form data extraction
- **Comprehend** → Document classification (optional)
- **DynamoDB** → Structured data storage

## Pipeline Flow

1. Document upload to S3 bucket
2. S3 event triggers Lambda function
3. Lambda calls Textract for OCR/form extraction
4. Document type classification (receipt, invoice, W-2, etc.)
5. Key field extraction and JSON structuring
6. Results stored in database/returned via API

## Quick Start

### Prerequisites
- AWS CLI configured
- Python 3.9+
- AWS account with appropriate permissions

### Setup
```bash
# Clone and setup
git clone <repo-url>
cd taxdoc-microservice
pip install -r requirements.txt

# Deploy infrastructure
aws cloudformation deploy --template-file infrastructure/template.yaml --stack-name taxdoc-stack

# Test with sample document
python scripts/test_upload.py sample-receipt.pdf
```

## Supported Document Types

- **Receipts** → Vendor, date, total, tax, line items
- **Invoices** → Invoice #, date, amount, vendor details
- **Tax Forms** → W-2, 1099, form-specific fields
- **Bank Statements** → Account info, transactions, balances

## API Endpoints

### Synchronous Processing
```
POST /process-document
Content-Type: multipart/form-data

Response: JSON with extracted fields
```

### Asynchronous Processing
```
POST /upload → Returns document ID
GET /result/{doc_id} → Returns processing status/results
```

## Configuration

Key environment variables:
- `UPLOAD_BUCKET` → S3 bucket for document uploads
- `RESULTS_TABLE` → DynamoDB table for metadata
- `CONFIDENCE_THRESHOLD` → Minimum OCR confidence (default: 0.8)

## Development

### Project Structure
```
├── src/
│   ├── handlers/          # Lambda functions
│   ├── services/          # Business logic
│   └── models/            # Data structures
├── infrastructure/        # CloudFormation templates
├── tests/                # Unit and integration tests
└── scripts/              # Deployment and utility scripts
```

### Local Testing
```bash
# Run unit tests
pytest tests/

# Test Lambda locally
sam local invoke ProcessDocumentFunction --event test-event.json
```

## Deployment

### Production
```bash
# Deploy via CloudFormation
./scripts/deploy.sh production

# Or using AWS CDK
cdk deploy TaxDocStack
```

### Monitoring
- CloudWatch logs for Lambda execution
- X-Ray tracing for performance analysis
- Custom metrics for processing success rates

## Security

- Private S3 buckets with encryption at rest
- IAM roles with minimal required permissions
- API authentication via AWS IAM or API keys
- HTTPS for all API communications

## Cost Optimization

- Textract synchronous API for single-page docs
- Asynchronous processing for multi-page documents
- DynamoDB on-demand pricing for variable workloads
- Lambda provisioned concurrency for consistent performance

## Roadmap

- [ ] Multi-language document support
- [ ] Custom ML model training for classification
- [ ] Batch processing capabilities
- [ ] Human review workflow integration (Amazon A2I)
- [ ] Real-time processing status updates

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Create GitHub issue
- Email: support@taxflowsai.com
- Documentation: [docs.taxflowsai.com](https://docs.taxflowsai.com)