import React, { useState } from 'react';
import TaxFormUploader from './components/TaxFormUploader';
import TaxFormResults from './components/TaxFormResults';
import TemplateDesigner from './components/TemplateDesigner';
import MarketingFeatures from './components/MarketingFeatures';
import ChatbotQA from './components/ChatbotQA';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import './styles/colors.css';
import './styles/tax-theme.css';
import './styles/tax-components.css';
import './App.css';



function App() {
  const [results, setResults] = useState([]);

  const handleResults = (newResults) => {
    setResults(Array.isArray(newResults) ? newResults : [newResults]);
  };

  return (
    <div className="app">
      <div className="app-header">
        <h1>🏛️ TaxDoc - Federal Tax Form Processor</h1>
        <p>Turn IRS & SSA forms into clean, accurate data in seconds</p>
        <div className="tax-badge">
          <span>Tax Edition</span> • Federal Forms Only • CPA Ready
        </div>
      </div>
      
      <TaxFormUploader onResults={handleResults} />
      
      {results.length > 0 && (
        <TaxFormResults results={results[0]} />
      )}
      
      {results.length > 0 && (
        <>
          <ChatbotQA documentData={results[0]} />
          <AnalyticsDashboard />
        </>
      )}
      
      <TemplateDesigner 
        documentUrl=""
        onSaveTemplate={(template) => console.log('Template saved:', template)}
      />
      
      <MarketingFeatures />
    </div>
  );
}

export default App;