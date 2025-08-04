import React, { useState } from 'react';
import axios from 'axios';
import MultiFormDisplay from './components/MultiFormDisplay';
import './components/MultiFormDisplay.css';
import './App.css';

const API_BASE = 'https://n82datyqse.execute-api.us-east-1.amazonaws.com/prod';

function App() {
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileSelect = (event) => {
    const selectedFile = event.target.files[0];
    setFile(selectedFile);
    setResult(null);
    setError(null);
    
    // Create preview for images
    if (selectedFile && selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setFilePreview(e.target.result);
      reader.readAsDataURL(selectedFile);
    } else {
      setFilePreview(null);
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer.files[0];
    setFile(droppedFile);
    setResult(null);
    setError(null);
    
    // Create preview for images
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => setFilePreview(e.target.result);
      reader.readAsDataURL(droppedFile);
    } else {
      setFilePreview(null);
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
  };

  const processDocument = async () => {
    if (!file) return;

    setProcessing(true);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE}/process-document`, {
        filename: file.name,
        contentType: file.type,
        size: file.size
      });

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Processing failed');
    } finally {
      setProcessing(false);
    }
  };

  const downloadExcel = async () => {
    if (!result?.DocumentID) return;

    try {
      const response = await axios.get(`${API_BASE}/download-excel/${result.DocumentID}`, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${result.DocumentID}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Excel download failed');
    }
  };

  return (
    <div className="container">
      <h1>🧾 TaxDoc - AI Document Processing</h1>
      <p>Upload your tax documents for intelligent processing and data extraction</p>

      <div 
        className={`upload-area ${file ? 'has-file' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          type="file"
          onChange={handleFileSelect}
          accept=".pdf,.jpg,.jpeg,.png,.txt"
          style={{ display: 'none' }}
          id="file-input"
        />
        <label htmlFor="file-input" style={{ cursor: 'pointer' }}>
          {file ? (
            <div>
              <p>📄 {file.name}</p>
              <p>Size: {(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <div>
              <p>📁 Drag and drop your document here</p>
              <p>or click to browse</p>
              <p><small>Supports: PDF, JPG, PNG, TXT</small></p>
            </div>
          )}
        </label>
      </div>

      <div style={{ textAlign: 'center' }}>
        <button 
          className="btn" 
          onClick={processDocument} 
          disabled={!file || processing}
        >
          {processing ? '⏳ Processing...' : '🚀 Process Document'}
        </button>
      </div>

      {error && (
        <div className="status error">
          ❌ {error}
        </div>
      )}

      {(filePreview || result) && (
        <div className="document-container">
          {filePreview && (
            <div className="document-preview">
              <h3>📄 Document Preview</h3>
              <div className="preview-image">
                <img src={filePreview} alt="Document preview" />
              </div>
            </div>
          )}
          
          {result && (
            <div className="extraction-results">
              <MultiFormDisplay result={result} />
              
              <div style={{ marginTop: '20px' }}>
                <button className="btn" onClick={downloadExcel}>
                  📊 Download Excel Report
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;