import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import API_CONFIG from '../config/api';

const EnhancedUploader = ({ onUploadComplete, onBatchComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [files, setFiles] = useState([]);
  const [progress, setProgress] = useState({});

  const onDrop = useCallback((acceptedFiles) => {
    if (batchMode) {
      setFiles(prev => [...prev, ...acceptedFiles.map(file => ({
        file,
        id: Date.now() + Math.random(),
        status: 'pending'
      }))]);
    } else {
      // Single file upload
      if (acceptedFiles.length > 0) {
        uploadSingleFile(acceptedFiles[0]);
      }
    }
  }, [batchMode]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg']
    },
    multiple: batchMode
  });

  const uploadSingleFile = async (file) => {
    setUploading(true);
    
    try {
      const base64 = await fileToBase64(file);
      
      const response = await fetch(`${API_CONFIG.BASE_URL}/process-document-enhanced`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          file_content: base64,
          enable_ai: true,
          user_id: localStorage.getItem('user_id') || 'anonymous'
        })
      });

      const result = await response.json();
      
      if (response.ok) {
        onUploadComplete(result);
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  const uploadBatch = async () => {
    if (files.length === 0) return;
    
    setUploading(true);
    
    try {
      // Convert all files to base64
      const fileData = await Promise.all(
        files.map(async ({ file }) => ({
          filename: file.name,
          file_content: await fileToBase64(file)
        }))
      );

      const response = await fetch(`${API_CONFIG.BASE_URL}/batch-upload-enhanced`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: fileData,
          user_id: localStorage.getItem('user_id') || 'anonymous'
        })
      });

      const result = await response.json();
      
      if (response.ok) {
        // Start polling for batch status
        pollBatchStatus(result.batch_id);
      } else {
        throw new Error(result.error || 'Batch upload failed');
      }
    } catch (error) {
      console.error('Batch upload error:', error);
      alert('Batch upload failed: ' + error.message);
      setUploading(false);
    }
  };

  const pollBatchStatus = async (batchId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_CONFIG.BASE_URL}/batch-status/${batchId}`);
        const status = await response.json();
        
        setProgress(status);
        
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(pollInterval);
          setUploading(false);
          onBatchComplete(status);
        }
      } catch (error) {
        console.error('Status polling error:', error);
        clearInterval(pollInterval);
        setUploading(false);
      }
    }, 2000);
  };

  const fileToBase64 = (file) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(',')[1]);
      reader.readAsDataURL(file);
    });
  };

  const removeFile = (id) => {
    setFiles(files.filter(f => f.id !== id));
  };

  return (
    <div className="enhanced-uploader">
      <div className="upload-mode-toggle">
        <button 
          className={!batchMode ? 'active' : ''}
          onClick={() => setBatchMode(false)}
        >
          Single Upload
        </button>
        <button 
          className={batchMode ? 'active' : ''}
          onClick={() => setBatchMode(true)}
        >
          Batch Upload
        </button>
      </div>

      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
      >
        <input {...getInputProps()} />
        <div className="dropzone-content">
          <div className="upload-icon">📤</div>
          <h3>
            {batchMode ? 'Drop multiple files here' : 'Drop your document here'}
          </h3>
          <p>or click to browse</p>
          <p className="file-types">Supports PDF, PNG, JPG</p>
        </div>
      </div>

      {batchMode && files.length > 0 && (
        <div className="batch-files">
          <h4>Files to Process ({files.length})</h4>
          <div className="file-list">
            {files.map(({ file, id, status }) => (
              <div key={id} className="file-item">
                <span className="file-name">{file.name}</span>
                <span className={`file-status ${status}`}>{status}</span>
                <button onClick={() => removeFile(id)} className="remove-btn">×</button>
              </div>
            ))}
          </div>
          <button 
            onClick={uploadBatch} 
            disabled={uploading || files.length === 0}
            className="batch-upload-btn"
          >
            {uploading ? 'Processing...' : `Process ${files.length} Files`}
          </button>
        </div>
      )}

      {uploading && progress.total_files && (
        <div className="batch-progress">
          <h4>Batch Progress</h4>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${(progress.processed_files / progress.total_files) * 100}%` }}
            />
          </div>
          <p>{progress.processed_files} of {progress.total_files} files processed</p>
        </div>
      )}
    </div>
  );
};

export default EnhancedUploader;