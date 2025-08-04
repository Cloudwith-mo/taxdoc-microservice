import React from 'react';

const DocumentViewer = ({ document }) => {
  if (!document) {
    return <div className="no-document">No document selected</div>;
  }

  const { DocumentType, Data, ExtractionMetadata, ClassificationConfidence } = document;
  const extractionMeta = ExtractionMetadata || {};

  // Get confidence level styling
  const getConfidenceStyle = (confidence) => {
    if (confidence >= 0.8) return { color: '#28a745', fontWeight: 'bold' };
    if (confidence >= 0.6) return { color: '#ffc107', fontWeight: 'bold' };
    return { color: '#dc3545', fontWeight: 'bold' };
  };

  // Get confidence icon
  const getConfidenceIcon = (confidence) => {
    if (confidence >= 0.8) return '✅';
    if (confidence >= 0.6) return '⚠️';
    return '❌';
  };

  // Render field with confidence indicator
  const renderField = (key, value, confidence) => {
    if (key.startsWith('_') || !value) return null;

    const fieldConfidence = extractionMeta.confidence_scores?.[key] || confidence || 0;
    const source = extractionMeta.field_sources?.[key] || 'unknown';

    return (
      <div key={key} className="field-row">
        <div className="field-label">
          {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}:
        </div>
        <div className="field-value">
          <span className="value">{typeof value === 'number' ? value.toLocaleString() : value}</span>
          <span className="confidence-indicator" style={getConfidenceStyle(fieldConfidence)}>
            {getConfidenceIcon(fieldConfidence)} {(fieldConfidence * 100).toFixed(0)}%
          </span>
          <span className="source-indicator" title={`Extracted using ${source}`}>
            ({source === 'textract' ? 'OCR' : source === 'claude' ? 'AI' : 'Pattern'})
          </span>
        </div>
      </div>
    );
  };

  // Group fields by document type
  const getFieldGroups = () => {
    if (!Data) return {};

    switch (DocumentType) {
      case 'W-2':
        return {
          'Employee Information': ['EmployeeName', 'EmployeeSSN'],
          'Employer Information': ['EmployerName', 'EmployerEIN'],
          'Wage Information': ['Box1_Wages', 'Box2_FederalTaxWithheld', 'Box3_SocialSecurityWages', 'Box4_SocialSecurityTax', 'Box5_MedicareWages', 'Box6_MedicareTax'],
          'Other': ['TaxYear']
        };
      case '1099-NEC':
        return {
          'Payer Information': ['PayerName', 'PayerTIN'],
          'Recipient Information': ['RecipientName', 'RecipientTIN'],
          'Income Information': ['Box1_NonemployeeComp', 'Box4_FederalTaxWithheld'],
          'Other': ['TaxYear']
        };
      case 'Bank Statement':
        return {
          'Account Information': ['AccountHolder', 'AccountNumber'],
          'Statement Period': ['StatementPeriod'],
          'Balances': ['BeginningBalance', 'EndingBalance']
        };
      case 'Pay Stub':
        return {
          'Employee Information': ['EmployeeName'],
          'Pay Period': ['PayPeriod'],
          'Current Pay': ['GrossPayCurrent', 'NetPayCurrent'],
          'Year to Date': ['GrossPayYTD']
        };
      default:
        return { 'All Fields': Object.keys(Data).filter(key => !key.startsWith('_')) };
    }
  };

  const fieldGroups = getFieldGroups();

  return (
    <div className="document-viewer">
      {/* Document Header */}
      <div className="document-header">
        <h2>{DocumentType}</h2>
        <div className="classification-info">
          <span className="classification-confidence" style={getConfidenceStyle(ClassificationConfidence)}>
            {getConfidenceIcon(ClassificationConfidence)} Classification: {(ClassificationConfidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Extraction Summary */}
      {extractionMeta && (
        <div className="extraction-summary">
          <div className="summary-stats">
            <div className="stat">
              <span className="stat-label">Completeness:</span>
              <span className="stat-value" style={getConfidenceStyle(extractionMeta.completeness_score || 0)}>
                {((extractionMeta.completeness_score || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Avg Confidence:</span>
              <span className="stat-value" style={getConfidenceStyle(extractionMeta.average_confidence || 0)}>
                {((extractionMeta.average_confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Layers Used:</span>
              <span className="stat-value">
                {(extractionMeta.layers_used || []).join(', ') || 'Unknown'}
              </span>
            </div>
          </div>
          
          {extractionMeta.needs_review && (
            <div className="review-warning">
              ⚠️ This document may need manual review due to low confidence or conflicts.
            </div>
          )}
        </div>
      )}

      {/* Document Fields */}
      <div className="document-fields">
        {Object.entries(fieldGroups).map(([groupName, fieldKeys]) => (
          <div key={groupName} className="field-group">
            <h3 className="group-title">{groupName}</h3>
            <div className="group-fields">
              {fieldKeys.map(key => renderField(key, Data[key], ClassificationConfidence))}
            </div>
          </div>
        ))}
      </div>

      {/* Conflicts Section */}
      {extractionMeta.conflicts && extractionMeta.conflicts.length > 0 && (
        <div className="conflicts-section">
          <h3>⚠️ Extraction Conflicts</h3>
          {extractionMeta.conflicts.map((conflict, index) => (
            <div key={index} className="conflict-item">
              <strong>{conflict.field}:</strong>
              <div>OCR: {conflict.textract}</div>
              <div>AI: {conflict.claude}</div>
            </div>
          ))}
        </div>
      )}

      <style jsx>{`
        .document-viewer {
          max-width: 800px;
          margin: 0 auto;
          padding: 20px;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .document-header {
          border-bottom: 2px solid #e9ecef;
          padding-bottom: 15px;
          margin-bottom: 20px;
        }

        .document-header h2 {
          margin: 0 0 10px 0;
          color: #495057;
        }

        .classification-info {
          font-size: 14px;
        }

        .extraction-summary {
          background: #f8f9fa;
          border-radius: 8px;
          padding: 15px;
          margin-bottom: 20px;
        }

        .summary-stats {
          display: flex;
          gap: 20px;
          margin-bottom: 10px;
        }

        .stat {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .stat-label {
          font-size: 12px;
          color: #6c757d;
          margin-bottom: 5px;
        }

        .stat-value {
          font-size: 16px;
          font-weight: bold;
        }

        .review-warning {
          background: #fff3cd;
          border: 1px solid #ffeaa7;
          border-radius: 4px;
          padding: 10px;
          color: #856404;
          font-size: 14px;
        }

        .field-group {
          margin-bottom: 25px;
        }

        .group-title {
          color: #495057;
          border-bottom: 1px solid #dee2e6;
          padding-bottom: 5px;
          margin-bottom: 15px;
        }

        .field-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid #f8f9fa;
        }

        .field-label {
          font-weight: 500;
          color: #495057;
          flex: 1;
        }

        .field-value {
          flex: 2;
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .value {
          font-family: 'Monaco', 'Menlo', monospace;
          background: #f8f9fa;
          padding: 2px 6px;
          border-radius: 3px;
        }

        .confidence-indicator {
          font-size: 12px;
        }

        .source-indicator {
          font-size: 11px;
          color: #6c757d;
          font-style: italic;
        }

        .conflicts-section {
          background: #f8d7da;
          border: 1px solid #f5c6cb;
          border-radius: 8px;
          padding: 15px;
          margin-top: 20px;
        }

        .conflicts-section h3 {
          margin-top: 0;
          color: #721c24;
        }

        .conflict-item {
          margin-bottom: 10px;
          padding: 8px;
          background: white;
          border-radius: 4px;
        }

        .no-document {
          text-align: center;
          color: #6c757d;
          padding: 40px;
          font-style: italic;
        }
      `}</style>
    </div>
  );
};

export default DocumentViewer;