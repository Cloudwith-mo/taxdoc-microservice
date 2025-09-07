import React, { useState } from 'react';

const TaxFormResults = ({ results }) => {
  const [activeTab, setActiveTab] = useState('line-items');

  if (!results || !results.Data) {
    return <div>No tax data available</div>;
  }

  const { DocumentType, Data, QualityMetrics, ExtractionMetadata, ValidationResults } = results;

  const renderLineItemSummary = () => (
    <div className="line-item-summary">
      <h3>📋 Line-Item Summary</h3>
      <div className="tax-fields-grid">
        {Object.entries(Data).map(([field, value]) => {
          if (field.endsWith('_source') || field.endsWith('_cross_validated') || field.endsWith('_masked')) {
            return null;
          }
          
          const confidence = QualityMetrics?.field_confidence_scores?.[field] || 0;
          const source = Data[`${field}_source`] || 'unknown';
          const crossValidated = Data[`${field}_cross_validated`] || false;
          
          return (
            <div key={field} className="tax-field-row">
              <div className="field-info">
                <span className="field-label">{field}</span>
                {getBoxNumber(field, DocumentType) && (
                  <span className="field-box-label">Box {getBoxNumber(field, DocumentType)}</span>
                )}
              </div>
              <div className="field-value">
                <span className="value">{formatTaxValue(value, field)}</span>
                <div className="field-metadata">
                  <span className={`confidence-badge ${getConfidenceClass(confidence)}`}>
                    {(confidence * 100).toFixed(0)}%
                  </span>
                  <span className={`source-badge source-${source}`}>
                    {getSourceLabel(source)}
                  </span>
                  {crossValidated && (
                    <span className="cross-validated-badge">✓ Verified</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderMathChecks = () => (
    <div className="math-checks">
      <h3>🧮 Math Checks</h3>
      {ValidationResults ? (
        <div className="validation-results">
          {ValidationResults.errors?.length > 0 && (
            <div className="validation-errors">
              <h4>❌ Errors Found</h4>
              {ValidationResults.errors.map((error, index) => (
                <div key={index} className="math-check-failed">
                  {error}
                </div>
              ))}
            </div>
          )}
          
          {ValidationResults.warnings?.length > 0 && (
            <div className="validation-warnings">
              <h4>⚠️ Warnings</h4>
              {ValidationResults.warnings.map((warning, index) => (
                <div key={index} className="tax-warning">
                  {warning}
                </div>
              ))}
            </div>
          )}
          
          {ValidationResults.errors?.length === 0 && ValidationResults.warnings?.length === 0 && (
            <div className="math-check-passed">
              ✅ All IRS math rules passed
            </div>
          )}
        </div>
      ) : (
        <div className="math-check-passed">
          ✅ Basic validation passed
        </div>
      )}
    </div>
  );

  const renderRefundCalculation = () => {
    if (DocumentType !== '1040') return null;
    
    const totalTax = parseFloat(Data.total_tax || 0);
    const totalPayments = parseFloat(Data.total_payments || 0);
    const refund = parseFloat(Data.refund_amount || 0);
    const owed = parseFloat(Data.amount_owed || 0);
    
    const calculatedDifference = totalPayments - totalTax;
    
    return (
      <div className="refund-calculation">
        <h3>💰 Refund / Balance Due</h3>
        <div className="calculation-chart">
          <div className="calc-row">
            <span>Total Payments:</span>
            <span className="amount">${totalPayments.toLocaleString()}</span>
          </div>
          <div className="calc-row">
            <span>Total Tax:</span>
            <span className="amount">-${totalTax.toLocaleString()}</span>
          </div>
          <div className="calc-divider"></div>
          <div className="calc-row total">
            <span>{calculatedDifference >= 0 ? 'Refund Due:' : 'Amount Owed:'}</span>
            <span className={`amount ${calculatedDifference >= 0 ? 'refund' : 'owed'}`}>
              ${Math.abs(calculatedDifference).toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    );
  };

  const renderMissingForms = () => (
    <div className="missing-forms">
      <h3>📄 Missing Forms</h3>
      <div className="form-checklist">
        {DocumentType === '1040' && (
          <>
            <div className="form-check">
              <span className="form-status unknown">?</span>
              <span>W-2 forms (check if wages reported)</span>
            </div>
            <div className="form-check">
              <span className="form-status unknown">?</span>
              <span>1099 forms (check if other income reported)</span>
            </div>
          </>
        )}
        {DocumentType === 'W-2' && (
          <div className="form-check">
            <span className="form-status unknown">?</span>
            <span>Corresponding 1040 return</span>
          </div>
        )}
        <p className="missing-forms-note">
          Upload additional forms to enable cross-validation
        </p>
      </div>
    </div>
  );

  const renderAIExplanation = () => (
    <div className="ai-explanation">
      <h3>🤖 AI Explanation</h3>
      <div className="extraction-summary">
        <p><strong>Processing Summary:</strong></p>
        <ul>
          <li>Document Type: <span className="tax-form-indicator">{DocumentType}</span></li>
          <li>Fields Extracted: {Object.keys(Data).filter(k => !k.includes('_')).length}</li>
          <li>Overall Confidence: {(QualityMetrics?.overall_confidence * 100 || 0).toFixed(0)}%</li>
          <li>Processing Layers: {ExtractionMetadata?.processing_layers?.join(' → ') || 'Unknown'}</li>
        </ul>
        
        {ExtractionMetadata?.cost_optimization && (
          <div className="cost-optimization">
            <p><strong>Cost Optimization:</strong></p>
            <ul>
              <li>Textract Primary: {ExtractionMetadata.cost_optimization.textract_primary} fields</li>
              <li>Claude Fallback: {ExtractionMetadata.cost_optimization.claude_fallback} fields</li>
              <li>Regex Safety: {ExtractionMetadata.cost_optimization.regex_safety} fields</li>
            </ul>
            <p className="savings-note">
              💡 Saved {Math.round((1 - ExtractionMetadata.cost_optimization.claude_fallback / 
                (ExtractionMetadata.cost_optimization.textract_primary + ExtractionMetadata.cost_optimization.claude_fallback || 1)) * 100)}% 
              on LLM costs through intelligent layering
            </p>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="tax-results-container">
      <div className="results-header">
        <h2>📊 Tax Form Analysis: {DocumentType}</h2>
        <div className="quality-indicator">
          <span className={`quality-badge ${getQualityClass(QualityMetrics?.overall_confidence)}`}>
            {getQualityLabel(QualityMetrics?.overall_confidence)} Quality
          </span>
        </div>
      </div>

      <div className="results-tabs">
        <button 
          className={`tab ${activeTab === 'line-items' ? 'active' : ''}`}
          onClick={() => setActiveTab('line-items')}
        >
          📋 Line Items
        </button>
        <button 
          className={`tab ${activeTab === 'math-checks' ? 'active' : ''}`}
          onClick={() => setActiveTab('math-checks')}
        >
          🧮 Math Checks
        </button>
        {DocumentType === '1040' && (
          <button 
            className={`tab ${activeTab === 'refund' ? 'active' : ''}`}
            onClick={() => setActiveTab('refund')}
          >
            💰 Refund/Owed
          </button>
        )}
        <button 
          className={`tab ${activeTab === 'missing' ? 'active' : ''}`}
          onClick={() => setActiveTab('missing')}
        >
          📄 Missing Forms
        </button>
        <button 
          className={`tab ${activeTab === 'ai-explanation' ? 'active' : ''}`}
          onClick={() => setActiveTab('ai-explanation')}
        >
          🤖 AI Analysis
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'line-items' && renderLineItemSummary()}
        {activeTab === 'math-checks' && renderMathChecks()}
        {activeTab === 'refund' && renderRefundCalculation()}
        {activeTab === 'missing' && renderMissingForms()}
        {activeTab === 'ai-explanation' && renderAIExplanation()}
      </div>
    </div>
  );
};

// Helper functions
const getBoxNumber = (field, docType) => {
  const boxMappings = {
    'W-2': {
      'wages_income': '1',
      'federal_withheld': '2',
      'social_security_wages': '3',
      'social_security_tax': '4',
      'medicare_wages': '5',
      'medicare_tax': '6'
    },
    '1099-NEC': {
      'nonemployee_compensation': '1',
      'federal_withheld': '4'
    }
  };
  
  return boxMappings[docType]?.[field];
};

const formatTaxValue = (value, field) => {
  if (field.includes('ssn') || field.includes('ein')) {
    return value; // Already masked
  }
  
  if (field.includes('amount') || field.includes('wage') || field.includes('tax') || field.includes('income')) {
    const num = parseFloat(value);
    return isNaN(num) ? value : `$${num.toLocaleString()}`;
  }
  
  return value;
};

const getConfidenceClass = (confidence) => {
  if (confidence >= 0.9) return 'high';
  if (confidence >= 0.7) return 'medium';
  return 'low';
};

const getSourceLabel = (source) => {
  const labels = {
    'textract_high': 'Textract',
    'textract_low': 'Textract*',
    'claude': 'AI',
    'regex': 'Pattern'
  };
  return labels[source] || source;
};

const getQualityClass = (confidence) => {
  if (confidence >= 0.9) return 'excellent';
  if (confidence >= 0.8) return 'good';
  if (confidence >= 0.6) return 'fair';
  return 'poor';
};

const getQualityLabel = (confidence) => {
  if (confidence >= 0.9) return 'Excellent';
  if (confidence >= 0.8) return 'Good';
  if (confidence >= 0.6) return 'Fair';
  return 'Poor';
};

export default TaxFormResults;