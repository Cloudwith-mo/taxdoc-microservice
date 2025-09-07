# TaxDoc Frontend - Multi-Form Document Processing Interface

## 🌐 Live Application
**Production URL**: http://taxdoc-web-app-prod-1754284862.s3-website-us-east-1.amazonaws.com/

## 🎨 Features

### **Multi-Form Display**
- Dynamic rendering based on document type (W-2, 1099s, Bank Statements, etc.)
- Confidence indicators with color coding:
  - 🟢 Green: High confidence (90%+)
  - 🟡 Yellow: Medium confidence (70-89%)
  - 🔴 Red: Low confidence (<70%)
- Source attribution showing extraction method:
  - 🔍 Textract Queries
  - 🤖 Claude LLM
  - 📝 Regex Patterns

### **User Experience**
- Drag-and-drop document upload
- Real-time processing status
- Field grouping by document sections
- Cross-validation indicators
- Excel export functionality
- Responsive design for all devices

## 🏗️ Architecture

### **Tech Stack**
- **React**: Frontend framework
- **AWS Amplify**: Hosting and deployment
- **Axios**: API communication
- **CSS3**: Responsive styling

### **Components**
```
src/
├── App.js                    # Main application component
├── components/
│   ├── MultiFormDisplay.js   # Dynamic document display
│   └── MultiFormDisplay.css  # Styling for multi-form UI
├── aws-config.js            # AWS configuration
└── index.js                 # Application entry point
```

## 🔌 API Integration

### **Backend Connection**
- **API Base**: https://n82datyqse.execute-api.us-east-1.amazonaws.com/prod
- **Endpoints**:
  - `POST /process-document` - Upload and process documents
  - `GET /result/{doc_id}` - Retrieve processing results
  - `GET /download-excel/{doc_id}` - Export to Excel

### **Data Flow**
1. User uploads document via drag-and-drop
2. Frontend calls `/process-document` API
3. Backend processes with three-layer extraction
4. Results displayed with confidence indicators
5. User can export to Excel format

## 📊 Display Features

### **Document Type Support**
- **Tax Forms**: W-2, 1099-NEC, 1099-INT, 1099-DIV, 1098-E, 1098, 1095-A, 1040
- **Financial**: Bank Statements, Pay Stubs
- **Business**: Receipts, Invoices

### **Field Grouping**
- **W-2**: Employee Info, Employer Info, Tax Info
- **1099s**: Payer Info, Recipient Info, Tax Info
- **Bank Statements**: Account Info, Balance Info
- **Others**: Organized by document structure

## 🚀 Development

### **Local Setup**
```bash
cd web-app
npm install
npm start
```

### **Build for Production**
```bash
npm run build
```

### **Deploy with Amplify**
```bash
amplify publish
```

## 🎯 Key Features Implemented

### **Enhanced Display**
- ✅ Multi-document type support
- ✅ Confidence-based color coding
- ✅ Source attribution icons
- ✅ Cross-validation indicators
- ✅ Responsive mobile design

### **User Interface**
- ✅ Clean, intuitive design
- ✅ Real-time processing feedback
- ✅ Error handling and validation
- ✅ Export functionality
- ✅ Document type recognition

## 📱 Responsive Design

### **Desktop**
- Full-width field display
- Side-by-side confidence indicators
- Detailed extraction statistics

### **Mobile**
- Stacked field layout
- Touch-optimized interactions
- Condensed confidence display

## 🔧 Configuration

### **Environment Variables**
```javascript
const API_BASE = 'https://n82datyqse.execute-api.us-east-1.amazonaws.com/prod';
```

### **Supported File Types**
- PDF documents
- Image files (JPG, PNG)
- Text files

## 📈 Performance

### **Optimization Features**
- Lazy loading of components
- Efficient re-rendering
- Minimal API calls
- Cached results display

### **User Experience Metrics**
- Sub-second UI response times
- Real-time processing status
- Clear confidence indicators
- Intuitive field organization

## 🎨 Styling

### **Design System**
- Clean, professional interface
- Color-coded confidence levels
- Consistent typography
- Accessible design patterns

### **CSS Features**
- Flexbox layouts
- CSS Grid for field organization
- Responsive breakpoints
- Smooth animations

The frontend provides a comprehensive, user-friendly interface for the TaxDoc multi-form extraction system with real-time confidence indicators and professional document processing capabilities.