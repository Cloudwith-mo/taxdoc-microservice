import React from 'react';

const MultiFormDisplay = ({ result }) => {
  if (!result) return null;

  // Handle new API response structure
  const data = result.Data || {};
  const documentType = result.DocumentType || 'Unknown';
  const metadata = result.ExtractionMetadata || {};
  const qualityMetrics = result.QualityMetrics || {};
  const hasError = result.Error || result.ProcessingStatus === 'Failed';

  // Get confidence level styling
  const getConfidenceStyle = (confidence) => {
    if (confidence >= 0.9) return { color: '#28a745', fontWeight: 'bold' };
    if (confidence >= 0.7) return { color: '#ffc107', fontWeight: 'bold' };
    return { color: '#dc3545', fontWeight: 'bold' };
  };

  // Get source icon
  const getSourceIcon = (source) => {
    switch (source) {
      case 'textract':
      case 'textract_query':
      case 'textract_low': return '🔍';
      case 'claude':
      case 'llm': return '🤖';
      case 'regex': return '📝';
      default: return '❓';
    }
  };

  // Render field with confidence and source from new structure
  const renderField = (key, value) => {
    if (key.endsWith('_source') || key.endsWith('_cross_validated')) {
      return null;
    }

    const sourceKey = `${key}_source`;
    const source = data[sourceKey];
    const crossValidated = data[`${key}_cross_validated`];
    const confidence = qualityMetrics.field_confidence_scores?.[key];

    return (
      <div key={key} className="field-row">
        <div className="field-label">
          {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}:
        </div>
        <div className="field-value">
          <span className="value">{value || 'N/A'}</span>
          {confidence && (
            <span className="confidence" style={getConfidenceStyle(confidence)}>
              ({(confidence * 100).toFixed(0)}%)
            </span>
          )}
          {source && (
            <span className="source" title={`Source: ${source}`}>
              {getSourceIcon(source)}
            </span>
          )}
          {crossValidated && (
            <span className="cross-validated" title="Cross-validated">
              ✓
            </span>
          )}
        </div>
      </div>
    );
  };

  // Group fields by document type for better display
  const getFieldGroups = () => {
    const fields = Object.keys(data).filter(key => 
      !key.endsWith('_source') && 
      !key.endsWith('_cross_validated') &&
      key !== 'error'
    );

    if (documentType === 'W-2') {
      return {
        'Employee Information': fields.filter(f => f.includes('Employee')),
        'Employer Information': fields.filter(f => f.includes('Employer')),
        'Tax Information': fields.filter(f => f.startsWith('Box')),
        'Other': fields.filter(f => !f.includes('Employee') && !f.includes('Employer') && !f.startsWith('Box'))
      };
    } else if (documentType.startsWith('1099') || documentType.includes('1099')) {
      return {
        'Payer Information': fields.filter(f => f.includes('Payer')),
        'Recipient Information': fields.filter(f => f.includes('Recipient')),
        'Tax Information': fields.filter(f => f.startsWith('Box')),
        'Other': fields.filter(f => !f.includes('Payer') && !f.includes('Recipient') && !f.startsWith('Box'))
      };
    } else if (documentType === 'Bank Statement') {
      return {
        'Account Information': fields.filter(f => f.includes('Account')),
        'Balance Information': fields.filter(f => f.includes('Balance')),
        'Other': fields.filter(f => !f.includes('Account') && !f.includes('Balance'))
      };
    } else {
      return { 'All Fields': fields };
    }
  };

  const fieldGroups = getFieldGroups();

  return (
    <div className="multi-form-display" data-doc-type={documentType}>
      <div className="document-header">
        <h3>{hasError ? '❌ Processing Failed' : '✅ Processing Complete'}</h3>
        <div><strong>Document ID:</strong> {result.DocumentID || 'N/A'}</div>
        <div><strong>Type:</strong> {documentType}</div>
        <div><strong>Status:</strong> {result.ProcessingStatus || 'Completed'}</div>
        
        {hasError && (
          <div className="error-message">
            <strong>Error:</strong> {result.Error || 'Processing failed'}
          </div>
        )}
        
        {!hasError && (
          <>
            <h4>📄 {documentType} - Extraction Results</h4>
            <div className="extraction-summary">
              <div className="summary-item">
                <span className="label">Overall Confidence:</span>
                <span className="value" style={getConfidenceStyle(qualityMetrics.overall_confidence || 0)}>
                  {((qualityMetrics.overall_confidence || 0) * 100).toFixed(0)}%
                </span>
              </div>
              <div className="summary-item">
                <span className="label">Total Fields:</span>
                <span className="value">{metadata.total_fields || 0}</span>
              </div>
              <div className="summary-item">
                <span className="label">Quality:</span>
                <span className="value">{qualityMetrics.extraction_quality || 'Unknown'}</span>
              </div>
              <div className="summary-item">
                <span className="label">Needs Review:</span>
                <span className={`value ${metadata.needs_review ? 'warning' : 'success'}`}>
                  {metadata.needs_review ? '⚠️ Yes' : '✅ No'}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      {!hasError && (
        <>
          <div className="extraction-stats">
            <div className="stat-item">
              <span className="icon">🔍</span>
              <span className="count">{metadata.textract_fields || 0}</span>
              <span className="label">Textract</span>
            </div>
            <div className="stat-item">
              <span className="icon">🤖</span>
              <span className="count">{metadata.llm_fields || 0}</span>
              <span className="label">AI Enhanced</span>
            </div>
            <div className="stat-item">
              <span className="icon">📝</span>
              <span className="count">{metadata.regex_fields || 0}</span>
              <span className="label">Pattern Match</span>
            </div>
          </div>

          <div className="fields-container">
            {Object.entries(fieldGroups).map(([groupName, groupFields]) => {
              if (groupFields.length === 0) return null;
              
              return (
                <div key={groupName} className="field-group">
                  <h4 className="group-title">{groupName}</h4>
                  <div className="fields-list">
                    {groupFields.map(field => renderField(field, data[field]))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {!hasError && metadata.needs_review && (
        <div className="review-notice">
          <h4>⚠️ Review Required</h4>
          <p>Some fields have low confidence scores or were extracted using fallback methods. Please review the highlighted fields for accuracy.</p>
        </div>
      )}
    </div>
  );
};

export default MultiFormDisplay;