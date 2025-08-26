# TaxDoc v2.5 Implementation Guide

## 🎯 Overview

This guide covers the implementation of all 28 GitHub issues for TaxDoc v2.5, including billing & entitlements, imports/exports, alerts, CORS, dashboards, UI enhancements, and unknown document handling.

## 🚀 Quick Deployment

### Prerequisites
- AWS CLI configured with appropriate permissions
- Stripe account with test/production keys
- Email address for notifications

### One-Command Deployment
```bash
# Deploy all v2.5 features
./scripts/deploy_v25_features.sh prod your-email@domain.com

# Test all features
./scripts/test_v25_features.sh prod
```

## 📋 Features Implemented

### ✅ Epic 1: Billing & Entitlements (Stripe)
- **Enhanced Stripe Webhook** (`enhanced_stripe_handler.py`)
  - Proper signature verification with `stripe.Webhook.construct_event()`
  - Idempotency using event IDs
  - User tier updates in DynamoDB
  - Environment variables: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

- **Entitlement Middleware** (`entitlement_middleware.py`)
  - Quota checking decorator `@check_entitlements()`
  - Feature access validation
  - 402 responses with upgrade hints
  - Monthly usage tracking

- **Monthly Quota Reset** (EventBridge + Lambda)
  - Cron: `cron(5 0 1 * ? *)` (00:05 UTC on 1st of month)
  - Resets `usedThisMonth` counters
  - Stores usage history

### ✅ Epic 2: Imports (Fast Wins)
- **Batch/Folder Upload** (`batch_upload_handler.py`)
  - Multiple file selection with queue UI
  - Folder upload with `webkitdirectory`
  - Progress tracking and error handling
  - File validation and duplicate detection

- **Mobile Camera Capture**
  - `<input accept="image/*" capture="environment">`
  - Client-side compression for files >6MB
  - Auto-rotation using EXIF data

- **ZIP Bulk Ingest**
  - ZIP file extraction and validation
  - Individual file processing
  - Batch job tracking in DynamoDB

- **Email-to-Upload (MVP)**
  - SES inbound processing
  - Attachment extraction
  - User allowlist validation

### ✅ Epic 3: Exports
- **Export All (ZIP)** (`export_handler.py`)
  - Multiple format support: CSV, JSON, Excel, PDF
  - ZIP packaging for bulk exports
  - 15-minute presigned URLs

- **PDF Summary Export**
  - ReportLab-based PDF generation
  - 1-page summary with key fields
  - Confidence indicators and branding

- **Email Export**
  - SES integration for export links
  - No PII in email body
  - Secure link expiration

### ✅ Epic 4: Alerts & Status (SNS)
- **SNS Topics** (`notification_handler.py`)
  - `doc-ready`, `doc-failed`, `batch-completed` topics
  - Email notifications with HTML templates
  - No PII in SNS messages

### ✅ Epic 5: CORS & Auth
- **API Gateway CORS**
  - Exact origin allowlist
  - Proper headers: `Authorization`, `Content-Type`
  - Methods: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`

- **Auth Sanity**
  - JWT token validation
  - 401/403 for unauthorized requests
  - Protected route enforcement

### ✅ Epic 6: Observability
- **CloudWatch Dashboard**
  - Lambda metrics (invocations, errors, p95)
  - S3 bucket size monitoring
  - DynamoDB throttling alerts

- **Structured Logs**
  - JSON format with `traceId`, `tenantId`, `userId`
  - Request correlation across services
  - X-Ray integration ready

### ✅ Epic 7: UI Enhancements
- **Upload Queue + Progress**
  - Visual queue with progress bars
  - File validation and error handling
  - Cancel/retry functionality
  - Auto-rotation for images

- **Import Stepper & Empty States**
  - Progress indicator: Import → Processing → Extracted → Export
  - Empty state cards with sample actions
  - Helpful microcopy

- **Documents Grid Filters/Sort/Search**
  - Type, confidence, date filters
  - Text search on filename/fields
  - Bulk selection with checkboxes
  - Sort by processed date, confidence, name

- **Document Viewer Polish**
  - Confidence chips with tooltips
  - Mask/reveal for sensitive data (SSN/EIN)
  - Copy buttons per field
  - Field citations with bbox highlighting

- **Export Drawer**
  - Right-side drawer with format options
  - Size estimates and expiry info
  - One-click export actions

- **Live "Doc Ready" Toast + Bell**
  - Real-time notifications
  - Polling/SSE for status updates
  - Header bell with unread count

- **Usage Meter + Upgrade CTA**
  - Header pill with progress bar
  - Color-coded usage levels
  - Inline upgrade prompts at cap

- **Subscriptions Page Polish**
  - Plan comparison cards
  - Current plan indicators
  - Loading states and error handling

- **AI Chat UX Enhancements**
  - Context chips for quick questions
  - Document context injection
  - Multi-line input with Shift+Enter

- **Analytics Improvements**
  - KPI cards with mini-sparklines
  - Skeleton loading states
  - Empty state handling

- **Accessibility & Responsive**
  - Keyboard navigation (tab order, focus rings)
  - ARIA labels and contrast compliance
  - Mobile-responsive breakpoints

- **Global Toaster + Validation**
  - Unified toast system
  - Inline form validation
  - Standard error components

### ✅ Epic 8: Unknown Docs & Citations
- **Unknown Doc Handling**
  - Top Fields extraction for unknown types
  - "Help me label" functionality
  - User-defined field mapping

- **Field Citations**
  - Click-to-highlight on document preview
  - Bbox coordinates from Textract
  - Canvas overlay with zoom

- **Trainable Patterns**
  - Tenant-scoped custom templates
  - Pattern matching by keywords/layout
  - Firm-specific training (upsell feature)

### ✅ Epic 9: Go/No-Go Testing
- **Comprehensive Test Script** (`test_v25_features.sh`)
  - 50+ automated tests
  - API endpoint validation
  - Infrastructure verification
  - Security and performance checks

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway    │    │   Lambda        │
│   (Enhanced)    │───▶│   (v2 routes)    │───▶│   Functions     │
│                 │    │                  │    │                 │
│ • Upload Queue  │    │ • /v2/batch      │    │ • Batch Handler │
│ • Export Drawer │    │ • /v2/export     │    │ • Export Handler│
│ • Usage Meter   │    │ • /v2/webhooks   │    │ • Stripe Handler│
│ • Filters/Sort  │    │ • CORS Enabled   │    │ • Notification  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   DynamoDB      │    │   S3 Buckets     │    │   SNS Topics    │
│                 │    │                  │    │                 │
│ • Users         │    │ • Uploads        │    │ • Doc Ready     │
│ • ExportJobs    │    │ • Exports        │    │ • Doc Failed    │
│ • ExportLogs    │    │ • (Lifecycle)    │    │ • Batch Done    │
│ • Batches       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔧 Configuration

### Environment Variables
```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# DynamoDB Tables
USERS_TABLE=DrDocUsers-prod
EXPORT_JOBS_TABLE=DrDocExportJobs-prod
BATCH_TABLE=DrDocBatches-prod

# S3 Buckets
UPLOAD_BUCKET=drdoc-uploads-prod-995805900737
EXPORTS_BUCKET=drdoc-exports-prod-995805900737

# SNS Topics
DOC_READY_TOPIC_ARN=arn:aws:sns:us-east-1:995805900737:drdoc-doc-ready-prod
```

### Stripe Webhook Configuration
1. **Webhook URL**: `https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/v2/webhooks/stripe`
2. **Events to Send**:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

### Plan Configuration
```javascript
const PLANS = {
  free: { limit: 20, features: ['csv'] },
  starter: { limit: 100, features: ['csv', 'json', 'xlsx', 'aiInsights', 'api'] },
  professional: { limit: 500, features: ['all', 'batchProcessing'] },
  enterprise: { limit: -1, features: ['all', 'customModels'] }
};
```

## 🧪 Testing

### Automated Testing
```bash
# Run all tests
./scripts/test_v25_features.sh prod

# Test specific components
curl -X POST "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/v2/batch-upload" \
  -H "Content-Type: application/json" \
  -d '{"files": []}'
```

### Manual Testing Checklist
- [ ] **Upload Flow**: Single, batch, folder, ZIP uploads
- [ ] **Processing**: Queue management, progress tracking
- [ ] **Export Flow**: CSV, JSON, Excel, PDF exports
- [ ] **Bulk Actions**: Multi-select, bulk export/delete
- [ ] **Usage Tracking**: Meter updates, quota enforcement
- [ ] **Notifications**: SNS alerts, email notifications
- [ ] **Authentication**: JWT validation, tier checking
- [ ] **UI/UX**: Responsive design, accessibility
- [ ] **Error Handling**: Graceful failures, user feedback

## 🚨 Troubleshooting

### Common Issues

1. **Stripe Webhook 403 Errors**
   ```bash
   # Check webhook secret
   aws lambda get-function-configuration \
     --function-name DrDoc-EnhancedStripeHandler-prod \
     --query 'Environment.Variables.STRIPE_WEBHOOK_SECRET'
   ```

2. **Export Failures**
   ```bash
   # Check S3 bucket permissions
   aws s3api get-bucket-policy --bucket drdoc-exports-prod-995805900737
   ```

3. **Batch Upload Timeouts**
   ```bash
   # Check Lambda timeout settings
   aws lambda get-function-configuration \
     --function-name DrDoc-BatchUploadHandler-prod \
     --query 'Timeout'
   ```

4. **CORS Issues**
   ```bash
   # Test CORS headers
   curl -I -X OPTIONS "https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/v2/export"
   ```

### Monitoring & Alerts

- **CloudWatch Dashboard**: `DrDoc-v25-prod`
- **Key Metrics**: Lambda errors, DynamoDB throttling, S3 bucket size
- **Alarms**: Email notifications for failures
- **Logs**: Structured JSON logs with correlation IDs

## 📈 Performance Optimization

### Cost Optimization
- **Intelligent Processing**: Skip LLM when Textract confidence is high
- **S3 Lifecycle**: Auto-delete exports after 24 hours
- **DynamoDB**: On-demand pricing with TTL
- **Lambda**: Right-sized memory allocation

### Scalability
- **Auto-scaling**: Lambda concurrency limits
- **Queue Management**: SQS with DLQ for failed messages
- **Caching**: API Gateway caching for static responses
- **CDN**: CloudFront for frontend assets

## 🔐 Security

### Data Protection
- **Encryption**: S3 server-side encryption (AES256)
- **Access Control**: IAM roles with minimal permissions
- **PII Handling**: Masking in UI, no PII in logs/SNS
- **Audit Trail**: All actions logged with user context

### Authentication & Authorization
- **JWT Validation**: Cognito token verification
- **Entitlement Checks**: Feature and quota validation
- **API Security**: Rate limiting, input validation
- **Webhook Security**: Stripe signature verification

## 🎯 Success Metrics

### Technical KPIs
- **Uptime**: >99.9% availability
- **Performance**: <2s API response time
- **Error Rate**: <1% failure rate
- **Processing Accuracy**: >95% confidence

### Business KPIs
- **User Engagement**: Upload frequency, feature usage
- **Conversion Rate**: Free to paid upgrades
- **Support Tickets**: Reduction in processing issues
- **Customer Satisfaction**: NPS score improvement

## 🔄 Rollback Plan

### Emergency Rollback
```bash
# Disable v2.5 features
aws ssm put-parameter --name "/drdoc/feature-flags/v25-enabled" --value "false" --overwrite

# Route traffic to v1 API
aws apigateway update-stage --rest-api-id YOUR_API_ID --stage-name prod \
  --patch-ops op=replace,path=/variables/version,value=v1

# Rollback frontend
aws s3 cp web-mvp/mvp2.html s3://taxdoc-mvp-web-1754513919/index.html
```

### Rollback Triggers
- Error rate >5%
- User complaints >10/day
- Processing accuracy <85%
- System downtime >1 hour

## 📞 Support

### Documentation
- **Technical Architecture**: [TECHNICAL_ARCHITECTURE.md](TECHNICAL_ARCHITECTURE.md)
- **API Documentation**: Swagger/OpenAPI specs
- **User Guide**: Frontend help documentation

### Contact
- **Issues**: Create GitHub issue
- **Email**: support@taxflowsai.com
- **Emergency**: On-call rotation

---

## 🎉 Conclusion

TaxDoc v2.5 represents a major leap forward in document processing capabilities, user experience, and operational excellence. All 28 GitHub issues have been successfully implemented with:

- **Enhanced User Experience**: Batch uploads, export drawer, usage tracking
- **Robust Infrastructure**: Proper authentication, monitoring, alerting
- **Scalable Architecture**: Microservices, event-driven processing
- **Production Ready**: Comprehensive testing, security, monitoring

The system is now ready for production deployment with confidence! 🚀