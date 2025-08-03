# TaxDoc Frontend Testing Interface

Two simple web interfaces to test your TaxDoc microservice:

## 🎯 Quick Start

### Option 1: Simple Mock Interface
```bash
open frontend/index.html
```
- Drag & drop file upload
- Simulated processing results
- No AWS credentials needed
- Good for UI testing

### Option 2: Real AWS Integration
```bash
open frontend/test-with-aws.html
```
- Real AWS SDK integration
- Upload files to S3
- Check DynamoDB results
- View Lambda logs
- Requires AWS credentials

## 🔧 Setup for AWS Integration

1. **Get AWS Credentials**
   - Access Key ID
   - Secret Access Key
   - Region: `us-east-1`

2. **Configure in Browser**
   - Enter credentials in the web interface
   - Click "Configure AWS"

3. **Test Components**
   - Upload files to S3
   - Check processing results in DynamoDB
   - View Lambda execution logs
   - Run comprehensive tests

## 📋 Testing Checklist

- [ ] Upload a document
- [ ] Verify S3 upload successful
- [ ] Check Lambda logs for processing
- [ ] Verify results in DynamoDB
- [ ] Test different document types

## 🚀 Your Deployed Resources

- **S3 Bucket**: `taxdoc-uploads-dev-995805900737`
- **DynamoDB Table**: `TaxDocuments-dev`
- **Lambda Function**: `TaxDoc-ProcessDocument-dev`
- **API Gateway**: `https://yjj6ifqqxi.execute-api.us-east-1.amazonaws.com/dev`

## 🔍 Troubleshooting

If uploads fail:
1. Check AWS credentials
2. Verify bucket permissions
3. Check CORS settings
4. View browser console for errors

## 📊 Expected Results

After uploading a document, you should see:
```json
{
  "DocumentID": "sample-receipt.txt",
  "DocumentType": "Receipt",
  "ProcessingStatus": "Completed",
  "Data": {
    "Vendor": "ABC Store",
    "Total": "$25.99",
    "Date": "2024-01-15"
  }
}
```