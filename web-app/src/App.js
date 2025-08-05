import React, { useState } from 'react';
import DrDocUploader from './components/DrDocUploader';
import AnyDocResults from './components/AnyDocResults';
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
    </div>
  );
}

export default App;