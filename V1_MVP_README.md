# TaxDoc V1 MVP - Tax Document Extraction

A minimal viable product for extracting structured data from tax documents using AWS Textract and Claude LLM.

## 🎯 V1 MVP Features

**Core Functionality:**
- Extract data from W-2 and 1099 tax forms
- Simple web interface for document upload
- No user accounts or payment required
- Instant processing and results display

**Supported Documents:**
- W-2 (Wage and Tax Statement)
- 1099-NEC (Nonemployee Compensation)
- 1099-MISC (Miscellaneous Income)
- 1099-DIV (Dividends)
- 1099-INT (Interest Income)

**Technology Stack:**
- **Backend**: AWS Lambda + Python 3.9
- **OCR**: AWS Textract
- **AI Extraction**: Anthropic Claude (with regex fallback)
- **API**: AWS API Gateway
- **Frontend**: Simple HTML/CSS/JavaScript
- **Storage**: AWS S3 (temporary)

## 🚀 Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Anthropic Claude API key
- Python 3.9+ (for local testing)

### Deploy V1 MVP

1. **Set Claude API Key:**
```bash
export CLAUDE_API_KEY="your-claude-api-key-here"
```

2. **Deploy to AWS:**
```bash
./scripts/deploy_v1_mvp.sh
```

3. **Test Locally:**
```bash
python3 scripts/test_v1_mvp.py
```

4. **Open Web Interface:**
Open `web-mvp/index.html` in your browser and test with tax documents.

## 📋 Architecture

```
User Upload → API Gateway → Lambda → Textract → Claude → Results
                                  ↓
                               S3 (temp)
```

**Processing Flow:**
1. User uploads tax document via web interface
2. File converted to base64 and sent to API
3. Lambda processes document with Textract OCR
4. Document classified as W-2, 1099, or unsupported
5. Claude extracts structured data (with regex fallback)
6. Results returned to user immediately

## 🧪 Testing

**Run Test Suite:**
```bash
python3 scripts/test_v1_mvp.py
```

**Test API Directly:**
```bash
curl -X POST https://your-api-endpoint/mvp/process-document \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "w2-sample.pdf",
    "file_content": "base64-encoded-content"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "filename": "w2-sample.pdf",
  "document_type": "W-2",
  "extracted_data": {
    "employee_ssn": "123-45-6789",
    "employer_ein": "12-3456789",
    "wages_income": 50000.00,
    "federal_withheld": 7500.00,
    "social_security_wages": 50000.00,
    "medicare_wages": 50000.00
  },
  "processing_info": {
    "ocr_blocks": 25,
    "extraction_method": "Claude + Textract",
    "version": "v1-mvp"
  }
}
```

## 📊 Extracted Fields

### W-2 Fields
- Employee SSN
- Employer EIN
- Employee Name
- Employer Name
- Wages & Income (Box 1)
- Federal Tax Withheld (Box 2)
- Social Security Wages (Box 3)
- Social Security Tax (Box 4)
- Medicare Wages (Box 5)
- Medicare Tax (Box 6)

### 1099-NEC Fields
- Payer TIN
- Recipient TIN
- Payer Name
- Recipient Name
- Nonemployee Compensation (Box 1)
- Federal Tax Withheld (Box 4)

### 1099-INT Fields
- Payer Name
- Recipient Name
- Interest Income (Box 1)
- Federal Tax Withheld (Box 4)

## 🔧 Configuration

**Environment Variables:**
- `CLAUDE_API_KEY`: Anthropic Claude API key (required)

**AWS Resources Created:**
- Lambda Function: `TaxDoc-Processor-mvp`
- API Gateway: `TaxDoc-API-mvp`
- S3 Bucket: `taxdoc-uploads-mvp-{account-id}`
- CloudWatch Log Group: `/aws/lambda/TaxDoc-Processor-mvp`

## 🚨 Limitations (V1 MVP)

**By Design:**
- No user accounts or authentication
- No payment system
- No document history
- No bulk processing
- Limited to tax forms only
- No advanced validation

**Technical:**
- 30-second Lambda timeout
- 6MB file size limit (API Gateway)
- No persistent storage
- Basic error handling

## 🛣️ Roadmap to V2

**Planned V2 Enhancements:**
- User accounts and authentication
- Credit-based payment system
- Document history and management
- Enhanced UI with document preview
- Bulk processing capabilities
- Advanced validation and confidence scoring
- Export options (CSV, Excel, JSON)

## 🔐 Security

**V1 Security Measures:**
- HTTPS/TLS for all communications
- Private S3 bucket with encryption
- IAM roles with minimal permissions
- No sensitive data in logs
- Automatic file cleanup (24 hours)

**Data Handling:**
- Files temporarily stored in S3
- No persistent storage of extracted data
- SSN/EIN data returned but not logged
- CORS enabled for web interface

## 💰 Cost Estimation

**Per Document Processing:**
- Textract: ~$0.0015 per page
- Claude API: ~$0.003 per document
- Lambda: ~$0.0001 per invocation
- **Total: ~$0.005 per document**

**Monthly Estimates:**
- 1,000 documents: ~$5
- 10,000 documents: ~$50
- 100,000 documents: ~$500

## 📞 Support

**Issues:**
- Create GitHub issue for bugs
- Check CloudWatch logs for errors

**Testing:**
- Use sample documents in `images/` folder
- Monitor API Gateway metrics
- Check Lambda function logs

## 📄 License

MIT License - see LICENSE file for details

---

**🎯 V1 MVP Goal:** Prove the concept with minimal complexity while setting foundation for V2 commercial features.**