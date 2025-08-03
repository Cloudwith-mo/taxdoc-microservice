# TaxDoc Web App Deployment Guide

## AWS Amplify Deployment Strategy

### Why Amplify?
- **Integrated CI/CD**: Automatic builds and deployments from Git
- **Built-in Authentication**: Easy Cognito integration
- **Global CDN**: Automatic HTTPS and CloudFront distribution
- **Environment Management**: Dev/staging/prod branch deployments
- **Zero Infrastructure Management**: Fully managed hosting

## Deployment Steps

### 1. Deploy Backend Infrastructure
```bash
# Deploy enhanced microservice with Excel generation
sam build --template infrastructure/template.yaml
sam deploy --stack-name taxdoc-stack-dev --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
```

### 2. Setup Amplify App
```bash
# Install Amplify CLI
npm install -g @aws-amplify/cli

# Initialize Amplify project
cd web-app
amplify init

# Add hosting
amplify add hosting
# Choose: Amazon CloudFront and S3

# Deploy to Amplify
amplify publish
```

### 3. Connect to Git Repository
1. Go to AWS Amplify Console
2. Connect your GitHub repository
3. Select the `web-app` folder as build root
4. Amplify will auto-detect the `amplify.yml` build settings

### 4. Configure Environment Variables
In Amplify Console → App Settings → Environment Variables:
```
REACT_APP_API_ENDPOINT=https://yjj6ifqqxi.execute-api.us-east-1.amazonaws.com/dev
```

## API Endpoints

### Document Processing
- **POST** `/process-document` - Process uploaded document
- **GET** `/result/{doc_id}` - Get processing results
- **GET** `/download-excel/{doc_id}` - Download Excel report

### Excel Download Flow
1. User uploads document → Processing complete
2. User clicks "Download Excel" → API generates Excel file
3. File uploaded to S3 → Presigned URL returned
4. Browser downloads file immediately

## Features

### ✅ Implemented
- **React Web App**: Modern UI with drag-drop upload
- **AWS Amplify**: Managed hosting with CI/CD
- **Excel Generation**: On-demand Excel reports via S3 presigned URLs
- **Async Processing**: Large PDF support via SNS + Lambda
- **AI Enhancement**: Comprehend classification + Bedrock summarization
- **Real-time Status**: Processing status updates

### 🔄 Architecture Benefits
- **Scalable**: Serverless auto-scaling
- **Secure**: IAM-based permissions, HTTPS by default
- **Cost-Effective**: Pay-per-use pricing
- **Maintainable**: Managed services reduce operational overhead

## Testing

### Local Development
```bash
cd web-app
npm install
npm start
# App runs on http://localhost:3000
```

### Production Testing
1. Upload test document via web interface
2. Verify processing completes
3. Download Excel report
4. Check S3 bucket for exported files

## Monitoring

- **Amplify Console**: Build logs and deployment status
- **CloudWatch**: Lambda function logs and metrics
- **API Gateway**: Request/response monitoring
- **S3**: File upload/download metrics

## Cost Optimization

- **Amplify**: Free tier includes 1000 build minutes/month
- **Lambda**: Pay per request (free tier: 1M requests/month)
- **S3**: Pay per storage and transfer
- **API Gateway**: Pay per API call (free tier: 1M calls/month)

## Security

- **HTTPS**: Automatic SSL certificates
- **CORS**: Configured for cross-origin requests
- **IAM**: Least-privilege access policies
- **Presigned URLs**: Time-limited file access (1 hour expiry)