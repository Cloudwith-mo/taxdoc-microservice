import React, { useState } from 'react';

const TaxFormUploader = ({ onResults }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFormType, setSelectedFormType] = useState('Auto');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);

  const supportedForms = [
    'Auto',
    '1040',
    'W-2', 
    '1099-NEC',
    '1099-MISC',
    '1099-DIV',
    '1099-INT',
    'K-1 (1065)',
    'K-1 (1120S)',
    '941'
  ];

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleFormTypeChange = (event) => {
    setSelectedFormType(event.target.value);
  };

  const processDocument = async () => {
    if (!selectedFile) {
      setError('Please select a tax form to upload');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      // Convert file to base64
      const base64Content = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result.split(',')[1];
          resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(selectedFile);
      });

      // Call the enhanced API
      const response = await fetch('https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/process-document', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          file_content: base64Content,
          form_type: selectedFormType === 'Auto' ? null : selectedFormType
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        
        if (response.status === 400 && errorData.error === 'Unsupported Document (Tax Edition)') {
          setError(
            <div className="unsupported-doc-message">
              <h3>📋 Tax Forms Only</h3>
              <p>{errorData.message}</p>
              <p>Supported federal tax forms:</p>
              <div className="supported-forms-list">
                {errorData.supported_forms.map(form => (
                  <span key={form} className="supported-form-tag">{form}</span>
                ))}
              </div>
              <p style={{marginTop: '16px', fontSize: '0.9em'}}>
                Need other document types? Email <strong>sales@taxflowsai.com</strong>
              </p>
            </div>
          );
          return;
        }
        
        throw new Error(errorData.error || 'Processing failed');
      }

      const result = await response.json();
      onResults(result);

    } catch (err) {
      console.error('Processing error:', err);
      setError(`Processing failed: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="tax-uploader-container">
      <div className="upload-section">
        <h2>📄 Upload Federal Tax Form</h2>
        
        <div className="form-type-selector">
          <label htmlFor="form-type">Form Type:</label>
          <select 
            id="form-type" 
            value={selectedFormType} 
            onChange={handleFormTypeChange}
            className="form-type-dropdown"
          >
            {supportedForms.map(form => (
              <option key={form} value={form}>{form}</option>
            ))}
          </select>
        </div>

        <div className="file-upload-area">
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={handleFileSelect}
            className="file-input"
            id="tax-file-input"
          />
          <label htmlFor="tax-file-input" className="file-upload-label">
            {selectedFile ? (
              <div>
                <span className="file-name">📎 {selectedFile.name}</span>
                <span className="file-size">({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
              </div>
            ) : (
              <div>
                <div className="upload-icon">📁</div>
                <div>Click to select tax form</div>
                <div className="file-types">PDF, PNG, JPG supported</div>
              </div>
            )}
          </label>
        </div>

        <button 
          onClick={processDocument}
          disabled={!selectedFile || isProcessing}
          className="process-button"
        >
          {isProcessing ? (
            <>
              <span className="spinner">⏳</span>
              Processing Tax Form...
            </>
          ) : (
            <>
              🔍 Extract Tax Data
            </>
          )}
        </button>

        {error && (
          <div className="error-message">
            {typeof error === 'string' ? error : error}
          </div>
        )}
      </div>

      <div className="tax-info-panel">
        <h3>🎯 Tax Edition Features</h3>
        <ul>
          <li>✅ <strong>IRS Math Validation</strong> - Automatic error detection</li>
          <li>✅ <strong>Cross-Form Validation</strong> - W-2 vs 1040 matching</li>
          <li>✅ <strong>PII Protection</strong> - SSN/EIN masking</li>
          <li>✅ <strong>CPA Ready</strong> - Professional formatting</li>
          <li>✅ <strong>87-99% Accuracy</strong> - Three-layer AI extraction</li>
        </ul>
        
        <div className="pricing-hint">
          <p><strong>💰 Tax Season Pricing</strong></p>
          <p>Yearly plans available - perfect for tax preparers!</p>
        </div>
      </div>
    </div>
  );
};

export default TaxFormUploader;