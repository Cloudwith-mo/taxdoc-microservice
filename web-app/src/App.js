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
import './styles/colors.css';
import './styles/tax-theme.css';
import './styles/tax-components.css';
import './styles/ai-features.css';
import './App.css';



function App() {
  const [results, setResults] = useState([]);
  const [activeTab, setActiveTab] = useState('process');

  const handleResults = (newResults) => {
    setResults(Array.isArray(newResults) ? newResults : [newResults]);
  };

  return (
    <div className="app">
      <div className="app-header">
        <h1>🏛️ TaxDoc Pro - AI-Powered Tax Intelligence</h1>
        <p>Turn IRS & SSA forms into clean, accurate data with AI insights</p>
        <div className="tax-badge">
          <span>AI Enhanced</span> • Federal Forms • Management Insights • CPA Ready
        </div>
        
        <div className="nav-tabs">
          <button 
            className={`nav-tab ${activeTab === 'v2' ? 'active' : ''}`}
            onClick={() => setActiveTab('v2')}
          >
            🚀 v2.0 Migration
          </button>
          <button 
            className={`nav-tab ${activeTab === 'process' ? 'active' : ''}`}
            onClick={() => setActiveTab('process')}
          >
            🤖 AI Processing
          </button>
          <button 
            className={`nav-tab ${activeTab === 'insights' ? 'active' : ''}`}
            onClick={() => setActiveTab('insights')}
          >
            😊 Sentiment Analysis
          </button>
          <button 
            className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            📊 Analytics
          </button>
        </div>
      </div>
      
      {activeTab === 'v2' && <V2Dashboard />}
      
      {activeTab === 'process' && (
        <>
          <TaxFormUploader onResults={handleResults} />
          
          {results.length > 0 && (
            <>
              <AIInsights documentData={results[0]} />
              <TaxFormResults results={results[0]} />
              <ChatbotQA documentData={results[0]} />
            </>
          )}
          
          <TemplateDesigner 
            documentUrl=""
            onSaveTemplate={(template) => console.log('Template saved:', template)}
          />
        </>
      )}
      
      {activeTab === 'insights' && (
        <SentimentAnalysis />
      )}
      
      {activeTab === 'analytics' && (
        <AnalyticsDashboard />
      )}
      
      <MarketingFeatures />
    </div>
  );
}

export default App;