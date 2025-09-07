import React, { useState, useRef } from 'react';
import { Stage, Layer, Rect, Text } from 'react-konva';
import './TemplateDesigner.css';

const TemplateDesigner = ({ documentUrl, onSaveTemplate }) => {
  const [isDrawing, setIsDrawing] = useState(false);
  const [fields, setFields] = useState([]);
  const [currentField, setCurrentField] = useState(null);
  const [templateName, setTemplateName] = useState('');
  const [showFieldModal, setShowFieldModal] = useState(false);
  const [selectedField, setSelectedField] = useState(null);
  const stageRef = useRef();

  const handleMouseDown = (e) => {
    if (!isDrawing) return;
    
    const pos = e.target.getStage().getPointerPosition();
    const newField = {
      id: Date.now(),
      x: pos.x,
      y: pos.y,
      width: 0,
      height: 0,
      name: '',
      type: 'text',
      required: false
    };
    setCurrentField(newField);
  };

  const handleMouseMove = (e) => {
    if (!isDrawing || !currentField) return;
    
    const pos = e.target.getStage().getPointerPosition();
    const updatedField = {
      ...currentField,
      width: pos.x - currentField.x,
      height: pos.y - currentField.y
    };
    setCurrentField(updatedField);
  };

  const handleMouseUp = () => {
    if (!currentField || currentField.width === 0 || currentField.height === 0) {
      setCurrentField(null);
      return;
    }
    
    setSelectedField(currentField);
    setShowFieldModal(true);
  };

  const saveField = (fieldData) => {
    const newField = {
      ...currentField,
      ...fieldData,
      bbox: {
        left: currentField.x / 600, // Normalize to 0-1
        top: currentField.y / 800,
        width: Math.abs(currentField.width) / 600,
        height: Math.abs(currentField.height) / 800
      }
    };
    
    setFields([...fields, newField]);
    setCurrentField(null);
    setShowFieldModal(false);
    setSelectedField(null);
  };

  const deleteField = (fieldId) => {
    setFields(fields.filter(f => f.id !== fieldId));
  };

  const saveTemplate = async () => {
    if (!templateName || fields.length === 0) {
      alert('Please provide a template name and add at least one field');
      return;
    }

    const template = {
      template_id: `template_${Date.now()}`,
      name: templateName,
      version: 1,
      fields: fields.map(f => ({
        name: f.name,
        type: f.type,
        required: f.required,
        bbox: f.bbox
      })),
      created_at: new Date().toISOString()
    };

    try {
      const response = await fetch('/api/templates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(template)
      });

      if (response.ok) {
        onSaveTemplate && onSaveTemplate(template);
        alert('Template saved successfully!');
        setFields([]);
        setTemplateName('');
      } else {
        alert('Failed to save template');
      }
    } catch (error) {
      console.error('Error saving template:', error);
      alert('Error saving template');
    }
  };

  return (
    <div className="template-designer">
      <div className="designer-header">
        <h3>📝 Create Custom Template</h3>
        <div className="template-controls">
          <input
            type="text"
            placeholder="Template name"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            className="template-name-input"
          />
          <button
            className={`draw-btn ${isDrawing ? 'active' : ''}`}
            onClick={() => setIsDrawing(!isDrawing)}
          >
            {isDrawing ? '✋ Stop Drawing' : '✏️ Draw Fields'}
          </button>
          <button className="save-template-btn" onClick={saveTemplate}>
            💾 Save Template
          </button>
        </div>
      </div>

      <div className="designer-content">
        <div className="canvas-container">
          <Stage
            width={600}
            height={800}
            ref={stageRef}
            onMouseDown={handleMouseDown}
            onMousemove={handleMouseMove}
            onMouseup={handleMouseUp}
          >
            <Layer>
              {/* Background image would go here */}
              
              {/* Existing fields */}
              {fields.map(field => (
                <React.Fragment key={field.id}>
                  <Rect
                    x={field.x}
                    y={field.y}
                    width={Math.abs(field.width)}
                    height={Math.abs(field.height)}
                    fill="rgba(20, 184, 166, 0.3)"
                    stroke="#14B8A6"
                    strokeWidth={2}
                  />
                  <Text
                    x={field.x + 5}
                    y={field.y - 20}
                    text={field.name || 'Unnamed Field'}
                    fontSize={12}
                    fill="#111418"
                  />
                </React.Fragment>
              ))}
              
              {/* Current drawing field */}
              {currentField && (
                <Rect
                  x={currentField.x}
                  y={currentField.y}
                  width={Math.abs(currentField.width)}
                  height={Math.abs(currentField.height)}
                  fill="rgba(251, 191, 36, 0.3)"
                  stroke="#FBBF24"
                  strokeWidth={2}
                  dash={[5, 5]}
                />
              )}
            </Layer>
          </Stage>
        </div>

        <div className="fields-panel">
          <h4>📋 Fields ({fields.length})</h4>
          <div className="fields-list">
            {fields.map(field => (
              <div key={field.id} className="field-item">
                <div className="field-info">
                  <span className="field-name">{field.name}</span>
                  <span className="field-type">{field.type}</span>
                  {field.required && <span className="required-badge">Required</span>}
                </div>
                <button
                  className="delete-field-btn"
                  onClick={() => deleteField(field.id)}
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Field Configuration Modal */}
      {showFieldModal && (
        <FieldModal
          field={selectedField}
          onSave={saveField}
          onCancel={() => {
            setShowFieldModal(false);
            setCurrentField(null);
            setSelectedField(null);
          }}
        />
      )}
    </div>
  );
};

const FieldModal = ({ field, onSave, onCancel }) => {
  const [name, setName] = useState('');
  const [type, setType] = useState('text');
  const [required, setRequired] = useState(false);

  const handleSave = () => {
    if (!name.trim()) {
      alert('Field name is required');
      return;
    }
    onSave({ name: name.trim(), type, required });
  };

  return (
    <div className="modal-overlay">
      <div className="field-modal">
        <h4>Configure Field</h4>
        
        <div className="form-group">
          <label>Field Name:</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Employee Name"
            autoFocus
          />
        </div>

        <div className="form-group">
          <label>Field Type:</label>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="text">Text</option>
            <option value="number">Number</option>
            <option value="date">Date</option>
            <option value="email">Email</option>
            <option value="currency">Currency</option>
          </select>
        </div>

        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={required}
              onChange={(e) => setRequired(e.target.checked)}
            />
            Required Field
          </label>
        </div>

        <div className="modal-actions">
          <button className="cancel-btn" onClick={onCancel}>Cancel</button>
          <button className="save-btn" onClick={handleSave}>Save Field</button>
        </div>
      </div>
    </div>
  );
};

export default TemplateDesigner;