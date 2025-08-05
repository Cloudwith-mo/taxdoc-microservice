import React, { useState } from 'react';
import DrDocUploader from './components/DrDocUploader';
import AnyDocResults from './components/AnyDocResults';
import TemplateDesigner from './components/TemplateDesigner';
import MarketingFeatures from './components/MarketingFeatures';
import ChatbotQA from './components/ChatbotQA';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import './styles/colors.css';
import './App.css';



function App() {
  const [results, setResults] = useState([]);

  const handleResults = (newResults) => {
    setResults(Array.isArray(newResults) ? newResults : [newResults]);
  };

  return (
    <div className="app">
      <div className="app-header">
        <h1>📄 Dr.Doc - Universal Document AI</h1>
        <p>Process any document type with advanced AI extraction</p>
      </div>
      
      <DrDocUploader onResults={handleResults} />
      
      {results.length > 0 && (
        <AnyDocResults results={results} />
      )}
      
      <ChatbotQA documentData={results[0]} />
      
      <AnalyticsDashboard />
      
      <TemplateDesigner 
        documentUrl=""
        onSaveTemplate={(template) => console.log('Template saved:', template)}
      />
      
      <MarketingFeatures />
    </div>
  );
}

export default App;