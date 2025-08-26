import React, { useState } from 'react';
import { useAuth } from './AuthProvider';

const EnhancedResults = ({ results }) => {
  const [activeSection, setActiveSection] = useState('extracted');
  const { userTier } = useAuth();

  const formatFieldName = (key) => {
    // Convert field keys to human-readable labels
    const fieldLabels = {
      'employee_name': 'Employee Name',
      'employee_ssn': 'Social Security Number',
      'employer_name': 'Employer Name',
      'employer_ein': 'Employer ID (EIN)',
      'wages_tips_compensation': 'Wages, Tips & Compensation',
      'federal_income_tax_withheld': 'Federal Income Tax Withheld',
      'social_security_wages': 'Social Security Wages',
      'social_security_tax_withheld': 'Social Security Tax Withheld',
      'medicare_wages': 'Medicare Wages & Tips',
      'medicare_tax_withheld': 'Medicare Tax Withheld',
      'state_wages': 'State Wages',
      'state_income_tax': 'State Income Tax',
      'payer_name': 'Payer Name',
      'payer_tin': 'Payer Tax ID',
      'recipient_name': 'Recipient Name',
      'recipient_tin': 'Recipient Tax ID',
      'nonemployee_compensation': 'Nonemployee Compensation',
      'account_holder': 'Account Holder',
      'account_number': 'Account Number',
      'statement_period': 'Statement Period',
      'beginning_balance': 'Beginning Balance',
      'ending_balance': 'Ending Balance'
    };

    return fieldLabels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const formatFieldValue = (key, value) => {
    // Format values based on field type
    if (typeof value !== 'string' && typeof value !== 'number') {
      return String(value);
    }

    const monetaryFields = [
      'wages_tips_compensation', 'federal_income_tax_withheld', 
      'social_security_wages', 'social_security_tax_withheld',
      'medicare_wages', 'medicare_tax_withheld', 'state_wages', 
      'state_income_tax', 'nonemployee_compensation',
      'beginning_balance', 'ending_balance'
    ];

    if (monetaryFields.includes(key) && !isNaN(parseFloat(value))) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
      }).format(parseFloat(value));
    }

    // Format SSN
    if (key.includes('ssn') && typeof value === 'string') {
      const cleaned = value.replace(/\D/g, '');
      if (cleaned.length === 9) {
        return `***-**-${cleaned.slice(-4)}`;
      }
    }

    return value;
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.7) return 'medium';
    return 'low';
  };

  const getSourceIcon = (source) => {
    switch (source) {
      case 'textract': return '🔍';
      case 'claude': return '🤖';
      case 'regex': return '🔧';
      default: return '📄';
    }
  };

  const renderExtractedData = () => {
    if (!results?.Data) return <p>No data extracted</p>;

    return (
      <div className="extracted-data">
        <div className="data-header">
          <h3>📋 Extracted Information</h3>
          <div className="document-type-badge">
            {results.DocumentType || 'Unknown Document'}
          </div>
        </div>

        <div className="fields-grid">
          {Object.entries(results.Data).map(([key, value], index) => {
            const confidence = results.QualityMetrics?.field_confidence_scores?.[key] || 0.95;
            const source = results.ExtractionMetadata?.field_sources?.[key] || 'textract';
            
            return (
              <div key={key} className="field-item">
                <div className="field-header">
                  <span className="field-number">{index + 1}.</span>
                  <span className="field-label">{formatFieldName(key)}</span>
                  <div className="field-metadata">
                    <span className="source-icon" title={`Extracted by ${source}`}>
                      {getSourceIcon(source)}
                    </span>
                    <span className={`confidence-badge ${getConfidenceColor(confidence)}`}>
                      {Math.round(confidence * 100)}%
                    </span>
                  </div>
                </div>
                <div className="field-value">
                  {formatFieldValue(key, value)}
                </div>
              </div>
            );
          })}
        </div>

        {results.ValidationResults?.warnings?.length > 0 && (
          <div className="validation-warnings">
            <h4>⚠️ Validation Warnings</h4>
            <ul>
              {results.ValidationResults.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const renderProcessingMetrics = () => (
    <div className="processing-metrics">
      <h3>⚙️ Processing Details</h3>
      
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Overall Confidence</div>
          <div className="metric-value">
            {Math.round((results.QualityMetrics?.overall_confidence || 0.95) * 100)}%
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Processing Layers</div>
          <div className="metric-value">
            {results.ExtractionMetadata?.processing_layers?.join(' → ') || 'Textract → AI → Regex'}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Cost Optimization</div>
          <div className="metric-value">
            {results.ExtractionMetadata?.cost_optimization?.textract_primary || 0} Textract, 
            {results.ExtractionMetadata?.cost_optimization?.claude_fallback || 0} AI
          </div>
        </div>
      </div>

      {userTier === 'premium' && (
        <div className="advanced-metrics">
          <h4>📊 Advanced Analytics</h4>
          <div className="processing-timeline">
            <div className="timeline-item">
              <span className="timeline-icon">🔍</span>
              <span>Textract OCR completed</span>
            </div>
            <div className="timeline-item">
              <span className="timeline-icon">🤖</span>
              <span>AI enhancement applied</span>
            </div>
            <div className="timeline-item">
              <span className="timeline-icon">✅</span>
              <span>Validation completed</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="enhanced-results">
      <div className="results-header">
        <h2>📊 Document Analysis Results</h2>
        <div className="results-tabs">
          <button
            className={`tab ${activeSection === 'extracted' ? 'active' : ''}`}
            onClick={() => setActiveSection('extracted')}
          >
            📋 Extracted Data
          </button>
          <button
            className={`tab ${activeSection === 'metrics' ? 'active' : ''}`}
            onClick={() => setActiveSection('metrics')}
          >
            ⚙️ Processing Details
          </button>
        </div>
      </div>

      <div className="results-content">
        {activeSection === 'extracted' && renderExtractedData()}
        {activeSection === 'metrics' && renderProcessingMetrics()}
      </div>

      <div className="results-actions">
        <button className="action-button primary">
          📥 Download Excel
        </button>
        <button className="action-button secondary">
          📋 Copy to Clipboard
        </button>
        {userTier === 'premium' && (
          <button className="action-button premium">
            🔗 Generate API Link
          </button>
        )}
      </div>
    </div>
  );
};

export default EnhancedResults;