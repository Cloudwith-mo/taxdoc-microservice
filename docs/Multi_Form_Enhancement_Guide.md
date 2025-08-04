# Multi-Form Document Processing Enhancement Guide

## Overview

The TaxDoc microservice has been upgraded with a comprehensive 3-layer extraction pipeline that supports all major tax and financial document types. This enhancement provides robust, confidence-aware document processing with AI-powered fallback mechanisms.

## Architecture

### 3-Layer Extraction Pipeline

1. **Layer 1: Textract Queries** (Primary)
   - Uses Amazon Textract's Queries feature for structured field extraction
   - Provides confidence scores for each extracted field
   - Optimized for well-formatted documents

2. **Layer 2: Claude LLM** (Fallback)
   - Amazon Bedrock Claude 3 Sonnet for low-confidence fields
   - Context-aware extraction using document-specific prompts
   - Cross-validation with Textract results

3. **Layer 3: Regex Patterns** (Safety Net)
   - Pattern-based extraction for critical fields
   - Ensures no field is completely missed
   - Marked with low confidence for review

### Document Classification

Enhanced rule-based classifier with confidence scoring:
- Priority-based classification for accuracy
- Document-specific pattern matching
- Confidence thresholds for quality control

## Supported Document Types

### Tax Documents
- **W-2**: Wage and Tax Statement
- **1099-NEC**: Nonemployee Compensation
- **1099-INT**: Interest Income
- **1099-DIV**: Dividends and Distributions
- **1099-MISC**: Miscellaneous Income
- **1098**: Mortgage Interest Statement
- **1098-E**: Student Loan Interest Statement
- **1095-A**: Health Insurance Marketplace Statement
- **1040**: Individual Income Tax Return

### Financial Documents
- **Bank Statements**: Account summaries and balances
- **Pay Stubs**: Payroll statements with YTD information
- **Receipts**: Purchase receipts with merchant and tax info
- **Invoices**: Business invoices with payment terms

## Configuration

### Document-Specific Settings

Each document type has tailored configuration in `src/config/document_config.py`:

```python
"W-2": {
    "queries": [
        {"Text": "What is the employee's name?", "Alias": "EmployeeName"},
        {"Text": "What are the wages, tips, other compensation (Box 1)?", "Alias": "Box1_Wages"},
        # ... more queries
    ],
    "claude_prompt": "Extract the following fields from this W-2 form: ...",
    "regex_patterns": {
        "Box1_Wages": r"wages.*?tips.*?compensation.*?\$?([0-9,]+\.?\d*)",
        # ... more patterns
    }
}
```

### Environment Variables

```bash
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
CONFIDENCE_THRESHOLD=0.8
ENABLE_BEDROCK_SUMMARY=true
ENABLE_W2_AI_EXTRACTION=true
```

## API Response Format

### Enhanced Response Structure

```json
{
  "DocumentID": "sample-w2.pdf",
  "DocumentType": "W-2",
  "ClassificationConfidence": 0.95,
  "ProcessingStatus": "Completed",
  "Data": {
    "EmployeeName": "John Doe",
    "Box1_Wages": 50000.00,
    "_extraction_metadata": {
      "document_type": "W-2",
      "layers_used": ["textract_queries", "claude_llm"],
      "field_sources": {
        "EmployeeName": "textract",
        "Box1_Wages": "claude"
      },
      "confidence_scores": {
        "EmployeeName": 0.98,
        "Box1_Wages": 0.85
      },
      "completeness_score": 0.90,
      "average_confidence": 0.91,
      "needs_review": false
    }
  }
}
```

### Confidence Indicators

- **High (≥80%)**: Green ✅ - Reliable extraction
- **Medium (60-79%)**: Yellow ⚠️ - May need verification
- **Low (<60%)**: Red ❌ - Requires manual review

## Deployment

### Prerequisites

1. AWS CLI configured with appropriate permissions
2. Bedrock access enabled in your AWS region
3. Claude 3 Sonnet model access approved

### Deploy the Enhancement

```bash
# Deploy using the enhanced script
./scripts/deploy_multi_form_enhancement.sh dev

# Or use standard SAM deployment
sam build && sam deploy --stack-name taxdoc-stack-dev
```

### Verify Deployment

```bash
# Run comprehensive tests
python scripts/test_multi_form_extraction.py --stack-name taxdoc-stack-dev

# Test specific document types
python scripts/test_single_image.py images/W2-sample.png
```

## Usage Examples

### Processing a W-2 Document

```python
# Upload document
response = requests.post(f"{API_ENDPOINT}/process-document", 
                        files={"file": open("w2.pdf", "rb")})

# Check results
doc_id = response.json()["DocumentID"]
result = requests.get(f"{API_ENDPOINT}/result/{doc_id}")

# Access extracted data
data = result.json()["Data"]
wages = data["Box1_Wages"]
confidence = data["_extraction_metadata"]["confidence_scores"]["Box1_Wages"]
```

### Front-End Integration

```jsx
import DocumentViewer from './components/DocumentViewer';

function App() {
  const [document, setDocument] = useState(null);
  
  return (
    <div>
      <DocumentViewer document={document} />
    </div>
  );
}
```

## Monitoring and Troubleshooting

### CloudWatch Metrics

Monitor these key metrics:
- Extraction completeness scores
- Average confidence levels
- Layer usage distribution
- Processing duration

### Common Issues

1. **Low Confidence Scores**
   - Check document quality (resolution, clarity)
   - Verify document type classification
   - Review regex patterns for edge cases

2. **Bedrock Errors**
   - Ensure proper IAM permissions
   - Check model availability in region
   - Verify request payload size limits

3. **Classification Issues**
   - Add keywords to classification config
   - Adjust confidence thresholds
   - Review document text extraction quality

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check extraction metadata:
```python
metadata = result["Data"]["_extraction_metadata"]
print(f"Layers used: {metadata['layers_used']}")
print(f"Needs review: {metadata['needs_review']}")
```

## Performance Optimization

### Cost Management

- Textract Queries: ~$0.0015 per page
- Bedrock Claude: ~$0.003 per 1K tokens
- Optimize by using higher confidence thresholds

### Speed Optimization

- Use synchronous processing for single-page documents
- Implement async processing for multi-page documents
- Cache common extraction patterns

## Security Considerations

### Data Protection

- All documents encrypted at rest in S3
- Temporary processing data cleaned up automatically
- No sensitive data logged in CloudWatch

### Access Control

- IAM roles with minimal required permissions
- API authentication via AWS IAM or API keys
- VPC endpoints for internal traffic

## Future Enhancements

### Planned Features

- [ ] Multi-language document support
- [ ] Custom ML model training for classification
- [ ] Batch processing capabilities
- [ ] Human review workflow integration (Amazon A2I)
- [ ] Real-time processing status updates

### Extensibility

Adding new document types:

1. Add classification keywords to `CLASSIFICATION_KEYWORDS`
2. Define queries, prompts, and patterns in `DOCUMENT_CONFIGS`
3. Update front-end field groupings in `DocumentViewer.js`
4. Test with sample documents

## Support

### Getting Help

- Check CloudWatch logs for detailed error messages
- Review extraction metadata for processing insights
- Use test scripts to validate specific document types

### Contributing

1. Fork the repository
2. Add new document type configurations
3. Include test cases and sample documents
4. Submit pull request with documentation updates

## Changelog

### v2.0.0 - Multi-Form Enhancement

- ✅ 3-layer extraction pipeline
- ✅ Support for 12+ document types
- ✅ Enhanced classification with confidence scoring
- ✅ Claude LLM integration via Bedrock
- ✅ Cross-validation and conflict detection
- ✅ Comprehensive test suite
- ✅ Enhanced front-end with confidence indicators

### Migration from v1.x

Existing W-2 processing remains compatible. New features:
- Enhanced extraction accuracy
- Confidence scoring
- Support for additional document types
- Improved error handling and metadata