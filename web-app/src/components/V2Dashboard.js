import React, { useState } from 'react';
import EnhancedUploader from './EnhancedUploader';
import EditableResults from './EditableResults';
// import { AuthProvider, useAuth, LoginForm } from './UserAuth';

const V2Dashboard = () => {
  const [currentDocument, setCurrentDocument] = useState(null);
  const [batchResults, setBatchResults] = useState(null);
  const [activeTab, setActiveTab] = useState('upload');
  // const { user } = useAuth();
  const user = null;

  const handleUploadComplete = (result) => {
    setCurrentDocument(result);
    setActiveTab('results');
  };

  const handleBatchComplete = (results) => {
    setBatchResults(results);
    setActiveTab('batch-results');
  };

  const handleDataUpdate = (updatedData) => {
    setCurrentDocument(updatedData);
  };

  return (
    <div className="v2-dashboard">
      <div className="dashboard-header">
        <h1>🏛️ TaxDoc v2.0</h1>
        <p>AI-Enhanced Document Processing Platform</p>
        <div className="migration-status">
          <div className="status-item">
            <span className="status-label">Upload:</span>
            <span className="status-value working">✅ Drag & Drop + Batch</span>
          </div>
          <div className="status-item">
            <span className="status-label">Extract:</span>
            <span className="status-value working">✅ AI + Edit Enabled</span>
          </div>
          <div className="status-item">
            <span className="status-label">Download:</span>
            <span className="status-value working">✅ CSV, JSON, Excel + Email</span>
          </div>
          <div className="status-item">
            <span className="status-label">Alerts:</span>
            <span className="status-value pending">⏳ SNS Integration</span>
          </div>
          <div className="status-item">
            <span className="status-label">Payment:</span>
            <span className="status-value pending">⏳ Stripe Integration</span>
          </div>
        </div>
      </div>

      <div className="dashboard-tabs">
        <button 
          className={activeTab === 'upload' ? 'active' : ''}
          onClick={() => setActiveTab('upload')}
        >
          📤 Upload & Process
        </button>
        <button 
          className={activeTab === 'results' ? 'active' : ''}
          onClick={() => setActiveTab('results')}
          disabled={!currentDocument}
        >
          📄 Results & Edit
        </button>
        <button 
          className={activeTab === 'batch-results' ? 'active' : ''}
          onClick={() => setActiveTab('batch-results')}
          disabled={!batchResults}
        >
          📚 Batch Results
        </button>
        <button 
          className={activeTab === 'chatbot' ? 'active' : ''}
          onClick={() => setActiveTab('chatbot')}
          disabled={!currentDocument}
        >
          🤖 AI Assistant
        </button>
      </div>

      <div className="dashboard-content">
        {activeTab === 'upload' && (
          <div className="upload-section">
            <EnhancedUploader 
              onUploadComplete={handleUploadComplete}
              onBatchComplete={handleBatchComplete}
            />
            
            <div className="feature-highlights">
              <h3>✨ v2.0 Features</h3>
              <div className="feature-grid">
                <div className="feature-card">
                  <h4>🎯 AI-Enhanced Extraction</h4>
                  <p>3-layer pipeline: Textract → Claude AI → Regex fallback</p>
                </div>
                <div className="feature-card">
                  <h4>✏️ Inline Editing</h4>
                  <p>Click any field to edit and improve accuracy</p>
                </div>
                <div className="feature-card">
                  <h4>📊 Multiple Formats</h4>
                  <p>Download as JSON, CSV, or Excel</p>
                </div>
                <div className="feature-card">
                  <h4>📧 Email Delivery</h4>
                  <p>Send results directly to your email</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'results' && currentDocument && (
          <EditableResults 
            documentData={currentDocument}
            onDataUpdate={handleDataUpdate}
          />
        )}

        {activeTab === 'batch-results' && batchResults && (
          <div className="batch-results">
            <h3>📚 Batch Processing Results</h3>
            <div className="batch-summary">
              <div className="summary-card">
                <h4>Total Files</h4>
                <span className="summary-value">{batchResults.total_files}</span>
              </div>
              <div className="summary-card">
                <h4>Successful</h4>
                <span className="summary-value success">{batchResults.successful || 0}</span>
              </div>
              <div className="summary-card">
                <h4>Failed</h4>
                <span className="summary-value error">{batchResults.failed || 0}</span>
              </div>
            </div>
            
            <div className="batch-actions">
              <button className="download-all-btn">
                📥 Download All Results
              </button>
              <button className="email-all-btn">
                📧 Email All Results
              </button>
            </div>
          </div>
        )}

        {activeTab === 'chatbot' && currentDocument && (
          <div className="chatbot-section">
            <h3>🤖 AI Document Assistant</h3>
            <div className="chat-container">
              <div className="chat-messages">
                <div className="bot-message">
                  👋 Hi! I can help explain your {currentDocument.document_type} document. 
                  Ask me about any field or tax-related questions!
                </div>
              </div>
              <div className="chat-input">
                <input 
                  type="text" 
                  placeholder="Ask about your document..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      // Handle chat message
                      console.log('Chat message:', e.target.value);
                    }
                  }}
                />
                <button>Send</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default V2Dashboard;