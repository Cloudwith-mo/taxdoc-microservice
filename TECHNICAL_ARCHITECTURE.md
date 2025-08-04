# TaxDoc Microservice - Technical Architecture Overview

## 🏗️ Overall System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TaxDoc System                            │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (React/Amplify)  │  Backend (AWS Serverless)          │
│  ┌─────────────────────┐   │  ┌─────────────────────────────────┐ │
│  │ • Document Upload   │   │  │ • Lambda Functions              │ │
│  │ • Multi-Form Display│   │  │ • Three-Layer Extraction        │ │
│  │ • Confidence UI     │   │  │ • Document Classification       │ │
│  │ • Results Dashboard │   │  │ • Storage & Processing          │ │
│  └─────────────────────┘   │  └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Backend Architecture

### **Core Processing Pipeline**
```
Document Upload (S3) → Classification → Three-Layer Extraction → Storage (DynamoDB)
                                      ↓
                    ┌─────────────────────────────────────┐
                    │        Three-Layer Extraction       │
                    │  1. Textract Queries (Primary)     │
                    │  2. LLM Enhancement (Fallback)      │
                    │  3. Regex Patterns (Safety Net)    │
                    └─────────────────────────────────────┘
```

### **AWS Services Stack**
- **S3**: Document storage with event triggers
- **Lambda**: Serverless processing functions
- **Textract**: OCR and structured data extraction
- **Bedrock**: LLM services (Titan/Claude)
- **DynamoDB**: Metadata and results storage
- **API Gateway**: RESTful API endpoints
- **SNS**: Async processing notifications
- **CloudWatch**: Logging and monitoring

### **Lambda Functions**
1. **ProcessDocumentFunction**: Main processing orchestrator
2. **TextractResultProcessor**: Async result handler
3. **ApiProcessFunction**: Synchronous API processing
4. **ExcelGeneratorFunction**: Report generation

## 🎨 Frontend Architecture

### **React Component Structure**
```
App.js
├── MultiFormDisplay.js (Dynamic document rendering)
├── ConfidenceIndicators (Visual confidence scoring)
├── DocumentUploader (Drag-and-drop interface)
└── ResultsExporter (Excel/PDF generation)
```

### **AWS Amplify Integration**
- **Hosting**: Static site deployment
- **CI/CD**: Automated build and deployment
- **Authentication**: User management (if needed)
- **API Integration**: Direct connection to API Gateway

## 📊 Data Flow Architecture

### **Document Processing Flow**
```
1. Upload → S3 Bucket
2. S3 Event → Lambda Trigger
3. Classification → Document Type Detection
4. Extraction Pipeline:
   ├── Textract Queries (High Precision)
   ├── LLM Enhancement (Smart Fallback)
   └── Regex Patterns (Safety Net)
5. Results → DynamoDB Storage
6. Response → Frontend Display
```

### **Three-Layer Extraction Detail**
```
Layer 1: Textract Queries
├── Natural language questions
├── High confidence extraction
└── Structured form understanding

Layer 2: LLM Enhancement
├── Low-confidence field processing
├── Context-aware extraction
└── Cross-validation with Layer 1

Layer 3: Regex Fallback
├── Pattern-based extraction
├── Critical field safety net
└── Last resort processing
```

## 🔐 Security Architecture

### **IAM Roles & Permissions**
- **Lambda Execution Role**: Minimal required permissions
- **Textract Service Role**: SNS publishing rights
- **S3 Bucket Policies**: Private access only
- **API Gateway**: CORS and authentication

### **Data Security**
- **Encryption at Rest**: S3 and DynamoDB
- **Encryption in Transit**: HTTPS/TLS
- **Access Control**: IAM-based permissions
- **Audit Logging**: CloudWatch integration

## 📈 Scalability & Performance

### **Serverless Benefits**
- **Auto-scaling**: Lambda concurrent execution
- **Cost optimization**: Pay-per-use model
- **High availability**: Multi-AZ deployment
- **Performance**: Sub-second response times

### **Processing Optimization**
- **Intelligent routing**: Sync vs async processing
- **Confidence-based processing**: Skip unnecessary layers
- **Caching**: DynamoDB for metadata
- **Batch processing**: Multiple document support

## 🔄 Integration Points

### **External Services**
- **AWS Textract**: Document OCR and analysis
- **AWS Bedrock**: LLM processing
- **AWS Comprehend**: Document classification (optional)

### **API Endpoints**
```
POST /process-document    # Synchronous processing
GET  /result/{doc_id}     # Retrieve results
GET  /download-excel/{id} # Export functionality
```

## 📱 Multi-Platform Support

### **Document Types Supported**
- **Tax Forms**: W-2, 1099 series, 1098 series, 1095-A, 1040
- **Financial**: Bank statements, pay stubs
- **Business**: Receipts, invoices

### **Output Formats**
- **JSON**: Structured data with confidence scores
- **Excel**: Formatted reports
- **PDF**: Document summaries (future)

## 🔍 Monitoring & Observability

### **CloudWatch Integration**
- **Metrics**: Processing success rates, latency
- **Logs**: Detailed execution traces
- **Alarms**: Error rate monitoring
- **Dashboards**: Real-time system health

### **Performance Tracking**
- **Extraction accuracy**: Per-document type metrics
- **Confidence scores**: Quality assessment
- **Processing times**: Performance optimization
- **Cost tracking**: Usage-based monitoring