# Production Hardening Checklist

## ✅ Implemented Guardrails

### S3 Security & Cost Control
- [x] **Lifecycle Policy**: Abort multipart uploads after 1 day
- [x] **Document Retention**: Delete originals after 30 days
- [x] **Bucket Policy**: Restrict uploads to API Gateway only
- [x] **Access Control**: Lambda-specific S3 permissions

### Lambda Concurrency & Performance
- [x] **Reserved Concurrency**: 
  - EnhancedApiFunction: 20 concurrent executions
  - SQSProcessorFunction: 10 concurrent executions  
  - TextractResultProcessor: 15 concurrent executions
- [x] **Overflow Protection**: Excess requests go to SQS DLQ
- [x] **X-Ray Tracing**: Enabled on all Lambda functions

### Cost Control & Monitoring
- [x] **Claude Cost Tracking**: Token usage metrics per document
- [x] **Textract Cost Tracking**: Page processing costs
- [x] **Daily Limits**: $50 Claude, $30 Textract
- [x] **Cost Alarms**: Automated alerts when limits exceeded

### Textract Optimization
- [x] **Feature Minimization**: Only use TABLES/FORMS when needed
- [x] **Size-based Processing**: Sync for <1MB, async for larger
- [x] **Batch Processing**: Efficient handling of small documents

### Observability & Debugging
- [x] **X-Ray Tracing**: End-to-end request tracing
- [x] **Custom Metrics**: Processing time, confidence, layer usage
- [x] **Error Tracking**: Detailed error metrics by type
- [x] **Cost Monitoring**: Real-time spend tracking

## 🚨 Operational Playbook

### Monitor Daily Costs
```bash
# Check Claude costs
aws cloudwatch get-metric-statistics \
  --namespace DrDoc/CostControl \
  --metric-name ClaudeEstimatedCost \
  --start-time $(date -d '1 day ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Check Textract costs  
aws cloudwatch get-metric-statistics \
  --namespace DrDoc/CostControl \
  --metric-name TextractEstimatedCost \
  --start-time $(date -d '1 day ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum
```

### Debug Processing Issues
```bash
# Tail Lambda logs
aws logs tail /aws/lambda/DrDoc-EnhancedApi-prod --since 5m --format short

# Check SQS DLQ for failed jobs
aws sqs receive-message --queue-url https://sqs.us-east-1.amazonaws.com/.../DrDoc-Processing-DLQ-prod

# View X-Ray traces
aws xray get-trace-summaries --time-range-type TimeRangeByStartTime \
  --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)
```

### Emergency Cost Control
```bash
# Temporarily disable Claude processing
aws lambda put-function-configuration \
  --function-name DrDoc-EnhancedApi-prod \
  --environment Variables='{ENABLE_BEDROCK_SUMMARY=false}'

# Reduce Lambda concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name DrDoc-EnhancedApi-prod \
  --provisioned-concurrency-config ProvisionedConcurrencyLevel=5
```

## 📊 Key Metrics to Watch

### Cost Metrics
- `DrDoc/CostControl/ClaudeEstimatedCost` - Daily Claude spending
- `DrDoc/CostControl/TextractEstimatedCost` - Daily Textract spending
- `DrDoc/CostControl/ClaudeTokensUsed` - Token consumption rate

### Performance Metrics
- `AWS/Lambda/Duration` - Processing latency
- `AWS/Lambda/ConcurrentExecutions` - Concurrency usage
- `AWS/SQS/ApproximateAgeOfOldestMessage` - Queue backlog

### Quality Metrics
- `DrDoc/Processing/ConfidenceScore` - Extraction accuracy
- `DrDoc/Processing/ProcessingErrors` - Failure rates
- `DrDoc/Processing/LayerUsage` - AI layer utilization

## 🔒 Security Hardening Status

- [x] S3 bucket policy restricts uploads to API Gateway
- [x] Lambda functions have minimal IAM permissions
- [x] API Gateway throttling prevents abuse
- [x] X-Ray tracing for security audit trails
- [x] CloudWatch alarms for anomaly detection

## 💡 Future Enhancements

- [ ] Implement circuit breaker for cost overruns
- [ ] Add document size validation before processing
- [ ] Implement user-based rate limiting
- [ ] Add ML model confidence thresholds
- [ ] Implement automated cost optimization