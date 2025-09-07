import React, { useState } from 'react';
import API_CONFIG from '../config/api';

const EditableResults = ({ documentData, onDataUpdate }) => {
  const [editMode, setEditMode] = useState({});
  const [editValues, setEditValues] = useState({});
  const [saving, setSaving] = useState(false);

  const startEdit = (fieldKey) => {
    setEditMode({ ...editMode, [fieldKey]: true });
    setEditValues({ 
      ...editValues, 
      [fieldKey]: documentData.extracted_data[fieldKey] || '' 
    });
  };

  const cancelEdit = (fieldKey) => {
    setEditMode({ ...editMode, [fieldKey]: false });
    delete editValues[fieldKey];
    setEditValues({ ...editValues });
  };

  const saveEdit = async (fieldKey) => {
    setSaving(true);
    
    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/update-field`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentData.document_id,
          field_key: fieldKey,
          new_value: editValues[fieldKey],
          user_id: localStorage.getItem('user_id') || 'anonymous'
        })
      });

      if (response.ok) {
        // Update local data
        const updatedData = {
          ...documentData,
          extracted_data: {
            ...documentData.extracted_data,
            [fieldKey]: editValues[fieldKey]
          }
        };
        
        onDataUpdate(updatedData);
        setEditMode({ ...editMode, [fieldKey]: false });
        delete editValues[fieldKey];
        setEditValues({ ...editValues });
      } else {
        throw new Error('Failed to save changes');
      }
    } catch (error) {
      console.error('Save error:', error);
      alert('Failed to save changes: ' + error.message);
    } finally {
      setSaving(false);
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 95) return '#22c55e'; // green
    if (confidence >= 85) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  const downloadFile = async (format) => {
    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}/download/${documentData.document_id}?format=${format}`,
        { method: 'GET' }
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${documentData.document_id}_extracted.${format}`;
        a.click();
        window.URL.revokeObjectURL(url);
      } else {
        throw new Error('Download failed');
      }
    } catch (error) {
      console.error('Download error:', error);
      alert('Download failed: ' + error.message);
    }
  };

  const emailResults = async () => {
    const email = prompt('Enter email address to send results:');
    if (!email) return;

    try {
      const response = await fetch(
        `${API_CONFIG.BASE_URL}/download/${documentData.document_id}?format=json&email=${email}`,
        { method: 'GET' }
      );

      if (response.ok) {
        alert(`Results sent to ${email}`);
      } else {
        throw new Error('Email send failed');
      }
    } catch (error) {
      console.error('Email error:', error);
      alert('Failed to send email: ' + error.message);
    }
  };

  if (!documentData || !documentData.extracted_data) {
    return <div>No data to display</div>;
  }

  return (
    <div className="editable-results">
      <div className="results-header">
        <h3>📄 {documentData.filename}</h3>
        <div className="document-info">
          <span className="doc-type">{documentData.document_type}</span>
          <span className="confidence-score">
            Overall Confidence: {documentData.confidence_score || 'N/A'}%
          </span>
        </div>
      </div>

      <div className="extracted-fields">
        {Object.entries(documentData.extracted_data).map(([fieldKey, fieldValue]) => {
          const confidence = documentData.confidence_scores?.[fieldKey] || 0;
          const isEditing = editMode[fieldKey];
          
          return (
            <div key={fieldKey} className="field-row">
              <div className="field-label">
                {fieldKey.replace(/_/g, ' ').toUpperCase()}
                <div 
                  className="confidence-indicator"
                  style={{ backgroundColor: getConfidenceColor(confidence) }}
                  title={`${confidence}% confidence`}
                >
                  {confidence}%
                </div>
              </div>
              
              <div className="field-value">
                {isEditing ? (
                  <div className="edit-controls">
                    <input
                      type="text"
                      value={editValues[fieldKey] || ''}
                      onChange={(e) => setEditValues({
                        ...editValues,
                        [fieldKey]: e.target.value
                      })}
                      className="edit-input"
                    />
                    <button 
                      onClick={() => saveEdit(fieldKey)}
                      disabled={saving}
                      className="save-btn"
                    >
                      ✓
                    </button>
                    <button 
                      onClick={() => cancelEdit(fieldKey)}
                      className="cancel-btn"
                    >
                      ✕
                    </button>
                  </div>
                ) : (
                  <div className="display-value">
                    <span>{fieldValue}</span>
                    <button 
                      onClick={() => startEdit(fieldKey)}
                      className="edit-btn"
                      title="Edit this field"
                    >
                      ✏️
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="action-buttons">
        <div className="download-section">
          <h4>Download Results</h4>
          <div className="download-buttons">
            <button onClick={() => downloadFile('json')} className="download-btn">
              📥 JSON
            </button>
            <button onClick={() => downloadFile('csv')} className="download-btn">
              📊 CSV
            </button>
            <button onClick={() => downloadFile('excel')} className="download-btn">
              📈 Excel
            </button>
          </div>
        </div>
        
        <div className="email-section">
          <h4>Email Results</h4>
          <button onClick={emailResults} className="email-btn">
            📧 Send via Email
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditableResults;