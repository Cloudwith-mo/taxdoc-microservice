import React, { useState } from 'react';
import AIInsights from './AIInsights';
import DocumentPreview from './DocumentPreview';
import './AnyDocResults.css';

const AnyDocResults = ({ results }) => {
  const [selectedResult, setSelectedResult] = useState(0);
  const [showRawData, setShowRawData] = useState(false);

  if (!results || results.length === 0) {
    return null;
  }

  const currentResult = results[selectedResult];

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return '#27ae60';
    if (confidence >= 0.6) return '#f39c12';
    return '#e74c3c';
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  const renderFieldValue = (key, value, metadata = {}) => {
    if (value === null || value === undefined || value === '') {
      return <span className="empty-value">Not found</span>;
    }

    // Handle different data types
    if (typeof value === 'object') {
      return <pre className="json-value">{JSON.stringify(value, null, 2)}</pre>;
    }

    // Format monetary values
    if (typeof value === 'number' && (key.toLowerCase().includes('amount') || 
        key.toLowerCase().includes('wage') || key.toLowerCase().includes('tax'))) {
      return <span className="monetary-value">${value.toLocaleString()}</span>;
    }

    return <span className="field-value">{String(value)}</span>;
  };

  const renderProcessingMetadata = (metadata) => {
    if (!metadata) return null;

    return (
      <div className="processing-metadata">
        <h4>🔍 Processing Details</h4>
        <div className="metadata-grid">
          <div className="metadata-item">
            <span className="metadata-label">File Type:</span>
            <span className="metadata-value">{metadata.file_type || 'Unknown'}</span>
          </div>
          <div className="metadata-item">
            <span className="metadata-label">Processing Route:</span>
            <span className="metadata-value">{metadata.processing_route || 'Standard'}</span>
          </div>
          <div className="metadata-item">
            <span className="metadata-label">Template Match:</span>
            <span className="metadata-value">{metadata.template_match || 'None'}</span>
          </div>
          <div className="metadata-item">
            <span className="metadata-label">Extraction Strategy:</span>
            <span className="metadata-value">{metadata.extraction_strategy || 'Auto'}</span>
          </div>
          {metadata.total_pages && (
            <div className="metadata-item">
              <span className="metadata-label">Pages:</span>
              <span className="metadata-value">{metadata.total_pages}</span>
            </div>
          )}
          {metadata.has_tables && (
            <div className="metadata-item">
              <span className="metadata-label">Contains Tables:</span>
              <span className="metadata-value">✅ Yes</span>
            </div>
          )}
          {metadata.has_forms && (
            <div className="metadata-item">
              <span className="metadata-label">Contains Forms:</span>
              <span className="metadata-value">✅ Yes</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderQualityMetrics = (metrics) => {
    if (!metrics) return null;

    return (
      <div className="quality-metrics">
        <h4>📊 Quality Metrics</h4>
        <div className="metrics-grid">
          <div className="metric-item">
            <span className="metric-label">Overall Confidence:</span>
            <div className="confidence-bar">
              <div 
                className="confidence-fill" 
                style={{ 
                  width: `${(metrics.overall_confidence || 0) * 100}%`,
                  backgroundColor: getConfidenceColor(metrics.overall_confidence || 0)
                }}
              ></div>
              <span className="confidence-text">
                {((metrics.overall_confidence || 0) * 100).toFixed(1)}% 
                ({getConfidenceLabel(metrics.overall_confidence || 0)})
              </span>
            </div>
          </div>
          {metrics.needs_human_review && (
            <div className="metric-item review-needed">
              <span className="metric-label">⚠️ Human Review:</span>
              <span className="metric-value">Recommended</span>
            </div>
          )}
          {metrics.processing_time_estimate && (
            <div className="metric-item">
              <span className="metric-label">Processing Time:</span>
              <span className="metric-value">{metrics.processing_time_estimate}</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderExtractedData = (data) => {
    if (!data || Object.keys(data).length === 0) {
      return (
        <div className="no-data">
          <p>No structured data extracted from this document.</p>
        </div>
      );
    }

    return (
      <div className="extracted-data">
        <div className="data-grid">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="data-item">
              <div className="data-label">
                {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
              </div>
              <div className="data-value">
                {renderFieldValue(key, value)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const downloadResults = (format = 'json') => {
    const data = format === 'json' ? 
      JSON.stringify(currentResult, null, 2) : 
      convertToCSV(currentResult);
    
    const blob = new Blob([data], { 
      type: format === 'json' ? 'application/json' : 'text/csv' 
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentResult.DocumentID || 'document'}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const convertToCSV = (result) => {
    const data = result.Data || {};
    const headers = Object.keys(data);
    const values = Object.values(data);
    
    return [
      headers.join(','),
      values.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')
    ].join('\n');
  };

  return (
    <div className="anydoc-results">
      <div className="results-header">
        <h2>📋 Processing Results</h2>
        {results.length > 1 && (
          <div className="result-selector">
            <label>Document:</label>
            <select 
              value={selectedResult} 
              onChange={(e) => setSelectedResult(parseInt(e.target.value))}
            >
              {results.map((result, index) => (
                <option key={index} value={index}>
                  {result.DocumentID || `Document ${index + 1}`}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="result-content">
        <div className="document-info">
          <div className="info-card">
            <h3>📄 {currentResult.DocumentType || 'Unknown Document'}</h3>
            <div className="document-details">
              <p><strong>Document ID:</strong> {currentResult.DocumentID || 'N/A'}</p>
              <p><strong>Processing Status:</strong> 
                <span className={`status ${currentResult.ProcessingStatus?.toLowerCase()}`}>
                  {currentResult.ProcessingStatus || 'Unknown'}
                </span>
              </p>
              {currentResult.UploadDate && (
                <p><strong>Processed:</strong> {new Date(currentResult.UploadDate).toLocaleString()}</p>
              )}
            </div>
          </div>
        </div>

        {renderQualityMetrics(currentResult.QualityMetrics)}
        {renderProcessingMetadata(currentResult.ProcessingMetadata)}

        <div className="extracted-content">
          <div className="content-header">
            <h3>📊 Extracted Data</h3>
            <div className="view-controls">
              <button 
                className={`view-btn ${!showRawData ? 'active' : ''}`}
                onClick={() => setShowRawData(false)}
              >
                📋 Structured View
              </button>
              <button 
                className={`view-btn ${showRawData ? 'active' : ''}`}
                onClick={() => setShowRawData(true)}
              >
                🔧 Raw Data
              </button>
            </div>
          </div>

          {showRawData ? (
            <div className="raw-data">
              <pre>{JSON.stringify(currentResult, null, 2)}</pre>
            </div>
          ) : (
            renderExtractedData(currentResult.Data)
          )}
        </div>

        <DocumentPreview 
          documentUrl={`data:image/png;base64,${currentResult.DocumentID}`}
          boundingBoxes={currentResult.ProcessingMetadata?.bounding_boxes || {}}
          onEntityClick={(entityId) => console.log('Entity clicked:', entityId)}
        />

        {currentResult.AIInsights && (
          <AIInsights insights={currentResult.AIInsights} />
        )}

        <div className="action-buttons">
          <button 
            className="btn download-btn"
            onClick={() => downloadResults('json')}
          >
            📥 Download JSON
          </button>
          <button 
            className="btn download-btn"
            onClick={() => downloadResults('csv')}
          >
            📊 Download CSV
          </button>
          <button 
            className="btn download-btn"
            onClick={() => window.open(`${process.env.REACT_APP_API_BASE}/download-excel/${currentResult.DocumentID}`, '_blank')}
          >
            📊 Download Excel
          </button>
          {currentResult.QualityMetrics?.needs_human_review && (
            <button className="btn review-btn">
              👁️ Request Human Review
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnyDocResults;