import React from 'react';

const MultiFormDisplay = ({ result }) => {
  if (!result || !result.Data) return null;

  const { Data, DocumentType } = result;
  const metadata = Data.ExtractionMetadata || {};

  // Get confidence level styling
  const getConfidenceStyle = (confidence) => {
    if (confidence >= 0.9) return { color: '#28a745', fontWeight: 'bold' };
    if (confidence >= 0.7) return { color: '#ffc107', fontWeight: 'bold' };
    return { color: '#dc3545', fontWeight: 'bold' };
  };

  // Get source icon
  const getSourceIcon = (source) => {
    switch (source) {
      case 'textract': return '🔍';
      case 'llm': return '🤖';
      case 'regex': return '📝';
      default: return '❓';
    }
  };

  // Render field with confidence and source
  const renderField = (key, value) => {
    if (key === 'DocumentType' || key === 'ExtractionMetadata' || 
        key.endsWith('_confidence') || key.endsWith('_source') || 
        key.endsWith('_cross_validated')) {
      return null;
    }

    const confidenceKey = `${key}_confidence`;
    const sourceKey = `${key}_source`;
    const confidence = Data[confidenceKey];
    const source = Data[sourceKey];
    const crossValidated = Data[`${key}_cross_validated`];

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
    const fields = Object.keys(Data).filter(key => 
      !key.endsWith('_confidence') && 
      !key.endsWith('_source') && 
      !key.endsWith('_cross_validated') &&
      key !== 'DocumentType' && 
      key !== 'ExtractionMetadata'
    );

    if (DocumentType === 'W-2') {
      return {
        'Employee Information': fields.filter(f => f.includes('Employee')),
        'Employer Information': fields.filter(f => f.includes('Employer')),
        'Tax Information': fields.filter(f => f.startsWith('Box')),
        'Other': fields.filter(f => !f.includes('Employee') && !f.includes('Employer') && !f.startsWith('Box'))
      };
    } else if (DocumentType.startsWith('1099')) {
      return {
        'Payer Information': fields.filter(f => f.includes('Payer')),
        'Recipient Information': fields.filter(f => f.includes('Recipient')),
        'Tax Information': fields.filter(f => f.startsWith('Box')),
        'Other': fields.filter(f => !f.includes('Payer') && !f.includes('Recipient') && !f.startsWith('Box'))
      };
    } else if (DocumentType === 'Bank Statement') {
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
    <div className="multi-form-display">
      <div className="document-header">
        <h3>📄 {DocumentType} - Extraction Results</h3>
        <div className="extraction-summary">
          <div className="summary-item">
            <span className="label">Overall Confidence:</span>
            <span className="value" style={getConfidenceStyle(metadata.overall_confidence || 0)}>
              {((metadata.overall_confidence || 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="summary-item">
            <span className="label">Total Fields:</span>
            <span className="value">{metadata.total_fields || 0}</span>
          </div>
          <div className="summary-item">
            <span className="label">Needs Review:</span>
            <span className={`value ${metadata.needs_review ? 'warning' : 'success'}`}>
              {metadata.needs_review ? '⚠️ Yes' : '✅ No'}
            </span>
          </div>
        </div>
      </div>

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
                {groupFields.map(field => renderField(field, Data[field]))}
              </div>
            </div>
          );
        })}
      </div>

      {metadata.needs_review && (
        <div className="review-notice">
          <h4>⚠️ Review Required</h4>
          <p>Some fields have low confidence scores or were extracted using fallback methods. Please review the highlighted fields for accuracy.</p>
        </div>
      )}
    </div>
  );
};

export default MultiFormDisplay;