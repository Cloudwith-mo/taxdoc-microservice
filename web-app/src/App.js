import React, { useState } from 'react';
import TaxFormUploader from './components/TaxFormUploader';
import TaxFormResults from './components/TaxFormResults';
import TemplateDesigner from './components/TemplateDesigner';
import MarketingFeatures from './components/MarketingFeatures';
import ChatbotQA from './components/ChatbotQA';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import AIInsights from './components/AIInsights';
import SentimentAnalysis from './components/SentimentAnalysis';
import V2Dashboard from './components/V2Dashboard';
import AuthModal from './components/AuthModal';
import PricingModal from './components/PricingModal';
import './styles/colors.css';
import './styles/tax-theme.css';
import './styles/tax-components.css';
import './styles/ai-features.css';
import './styles/auth.css';
import './styles/document-results.css';
import './App.css';

function App() {
  const [results, setResults] = useState([]);
  const [activeTab, setActiveTab] = useState('upload');
  const [user, setUser] = useState(null);
  const [showAuth, setShowAuth] = useState(false);
  const [showPricing, setShowPricing] = useState(false);

  const handleResults = (newResults) => {
    setResults(Array.isArray(newResults) ? newResults : [newResults]);
  };

  return (
    <div className="app">
      <div className="app-header">
        <div className="header-content">
          <div>
            <h1>🏛️ TaxDoc Pro - AI-Powered Tax Intelligence</h1>
            <p>Turn IRS & SSA forms into clean, accurate data with AI insights</p>
            <div className="tax-badge">
              <span>AI Enhanced</span> • Federal Forms • Management Insights • CPA Ready
            </div>
          </div>
          <div className="auth-section">
            {user ? (
              <>
                <span>Welcome, {user.email}</span>
                <button onClick={() => setShowPricing(true)} className="upgrade-btn">Upgrade</button>
              </>
            ) : (
              <button onClick={() => setShowAuth(true)} className="login-btn">Login</button>
            )}
          </div>
        </div>
        
        <div className="nav-tabs">
          <button 
            className={`nav-tab ${activeTab === 'register' ? 'active' : ''}`}
            onClick={() => setActiveTab('register')}
          >
            👤 Register
          </button>
          <button 
            className={`nav-tab ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            📤 Upload & Batch
          </button>
          <button 
            className={`nav-tab ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            📄 Documents
          </button>
          <button 
            className={`nav-tab ${activeTab === 'chatbot' ? 'active' : ''}`}
            onClick={() => setActiveTab('chatbot')}
          >
            🤖 AI Chatbot
          </button>
          <button 
            className={`nav-tab ${activeTab === 'pay' ? 'active' : ''}`}
            onClick={() => setActiveTab('pay')}
          >
            💳 Pay
          </button>
        </div>
      </div>
      
      {activeTab === 'register' && (
        <div className="tab-content">
          <h2>👤 User Registration & Authentication</h2>
          <button onClick={() => setShowAuth(true)} className="auth-btn">Login / Register</button>
          {user && <p>✅ Logged in as: {user.email}</p>}
        </div>
      )}
      
      {activeTab === 'upload' && (
        <div className="tab-content">
          <TaxFormUploader onResults={handleResults} />
        </div>
      )}
      
      {activeTab === 'documents' && (
        <div className="tab-content">
          <div className="document-result">
            <h3>📄 W2-sample.png</h3>
            <p><strong>Type:</strong> W-2</p>
            <p><strong>Confidence:</strong> 95%</p>
            
            <div className="extracted-fields">
              <div className="field">
                <strong>EMPLOYEE NAME:</strong><br/>
                John Doe
              </div>
              <div className="field">
                <strong>EMPLOYER NAME:</strong><br/>
                Tech Corp Inc
              </div>
              <div className="field">
                <strong>WAGES:</strong><br/>
                $75,000.00
              </div>
              <div className="field">
                <strong>FEDERAL TAX:</strong><br/>
                $12,500.00
              </div>
            </div>
            
            <div className="download-options">
              <button className="download-btn">📥 Download CSV</button>
              <button className="download-btn">📥 Download JSON</button>
              <button className="download-btn">📥 Download Excel</button>
            </div>
          </div>
        </div>
      )}
      
      {activeTab === 'chatbot' && (
        <div className="tab-content">
          <ChatbotQA documentData={results[0]} />
        </div>
      )}
      
      {activeTab === 'pay' && (
        <div className="tab-content">
          <h2>💳 Subscription Plans</h2>
          <button onClick={() => setShowPricing(true)} className="pricing-btn">View Plans & Subscribe</button>
        </div>
      )}
      
      <MarketingFeatures />
      
      <AuthModal 
        isOpen={showAuth} 
        onClose={() => setShowAuth(false)} 
        onAuth={(userData) => setUser(userData)} 
      />
      
      <PricingModal 
        isOpen={showPricing} 
        onClose={() => setShowPricing(false)} 
        userEmail={user?.email} 
      />
    </div>
  );
}

export default App;