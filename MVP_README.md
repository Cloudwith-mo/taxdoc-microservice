# TaxDoc MVP - Simplified Tax Form Processing

A focused MVP implementation that extracts data from W-2 and 1099 tax forms using AWS Textract and Claude AI.

## 🎯 MVP Scope

**Supported Forms:**
- W-2 (Wage and Tax Statement)
- 1099-NEC (Nonemployee Compensation)
- 1099-INT (Interest Income)
- 1099-DIV (Dividends and Distributions)
- 1099-MISC (Miscellaneous Income)

**Key Features:**
- ✅ No login required - instant use
- ✅ Simple drag & drop interface
- ✅ AWS Textract OCR extraction
- ✅ Claude AI field extraction
- ✅ Basic field validation
- ✅ Serverless architecture

## 🏗️ Architecture

```
Frontend (Static HTML) → API Gateway → Lambda → Textract + Claude → Results
```

**Components:**
- **Frontend**: Single HTML page with JavaScript
- **API**: Single Lambda function via API Gateway
- **OCR**: AWS Textract (synchronous)
- **AI**: Claude via AWS Bedrock
- **Storage**: Temporary S3 for uploads

## 🚀 Quick Start

### Deploy Backend
```bash
# Deploy to AWS
./scripts/deploy_mvp.sh

# Test locally
python3 scripts/test_mvp.py
```

### Frontend Setup
1. Update `API_ENDPOINT` in `web-mvp/index.html`
2. Host static file on S3 or any web server
3. No build process required

## 📋 Processing Pipeline

1. **File Upload** → User uploads PDF/image
2. **OCR Extraction** → Textract extracts text
3. **Form Classification** → Keyword-based form type detection
4. **Field Extraction** → Claude extracts structured fields
5. **Validation** → Basic field formatting and validation
6. **Results** → JSON response with extracted data

## 🔧 Configuration

**Environment Variables:**
- `ENVIRONMENT` → Deployment environment (mvp/prod)

**AWS Services:**
- Textract (synchronous API)
- Bedrock (Claude 3 Sonnet)
- Lambda (30s timeout)
- API Gateway (CORS enabled)
- S3 (temporary storage)

## 📊 Expected Fields

**W-2 Fields:**
- employer_name, employer_ein
- employee_name, employee_ssn
- wages_box1, federal_tax_withheld_box2
- social_security_wages_box3, social_security_tax_box4
- medicare_wages_box5, medicare_tax_box6

**1099 Fields:**
- payer_name, payer_tin
- recipient_name, recipient_tin
- Various income/compensation boxes
- federal_tax_withheld_box4

## 🧪 Testing

```bash
# Test MVP pipeline
python3 scripts/test_mvp.py

# Test with sample images
python3 -c "
from src.services.tax_form_processor import TaxFormProcessor
processor = TaxFormProcessor()
with open('images/W2-sample.png', 'rb') as f:
    result = processor.process_tax_document(f.read(), 'test.png')
print(result)
"
```

## 🔒 Security & Privacy

**Data Handling:**
- No persistent storage of documents
- SSN masking in frontend display
- HTTPS/TLS for all communications
- Temporary S3 storage only

**Rate Limiting:**
- API Gateway throttling
- No user accounts (open access)
- CloudWatch monitoring

## 💰 Cost Optimization

**Pay-per-use:**
- Lambda: ~$0.0001 per request
- Textract: ~$0.0015 per page
- Bedrock Claude: ~$0.003 per 1K tokens
- **Total**: ~$0.01 per document

## 🚀 Deployment

```bash
# Deploy complete MVP
./scripts/deploy_mvp.sh mvp

# Get API endpoint
aws cloudformation describe-stacks \
  --stack-name TaxDoc-MVP-mvp \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text
```

## 📈 Future Enhancements

**V2 Features:**
- User accounts and authentication
- Document history and storage
- Batch processing
- Additional form types
- Mobile app
- Payment integration

## 🤝 Usage

1. Visit the web interface
2. Drag & drop or select a tax form (PDF/image)
3. Click "Process"
4. View extracted fields in structured format
5. No signup required - instant results

## 📞 Support

**MVP Limitations:**
- W-2 and 1099 forms only
- Single page documents
- No user accounts
- Basic validation only

For issues or questions, check CloudWatch logs or create a GitHub issue.

---

**🎯 This MVP focuses on core tax form extraction with minimal complexity, perfect for validating the concept and gathering user feedback.**