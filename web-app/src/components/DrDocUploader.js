import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import './DrDocUploader.css';

const API_BASE = 'https://n82datyqse.execute-api.us-east-1.amazonaws.com/prod';

const DrDocUploader = ({ onResults }) => {
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState({});
  const [supportedTypes, setSupportedTypes] = useState([]);

  // Fetch supported types on component mount
  React.useEffect(() => {
    fetchSupportedTypes();
  }, []);

  const fetchSupportedTypes = async () => {
    try {
      const response = await axios.get(`${API_BASE}/supported-types`);
      setSupportedTypes(response.data.supported_types);
    } catch (error) {
      console.error('Failed to fetch supported types:', error);
    }
  };

  const onDrop = useCallback((acceptedFiles) => {
    const newFiles = acceptedFiles.map((file, index) => ({
      id: `file_${Date.now()}_${index}`,
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
      status: 'ready',
      result: null,
      error: null
    }));
    
    setFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png', '.tiff', '.webp'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    multiple: true,
    maxSize: 10 * 1024 * 1024 // 10MB limit
  });

  const removeFile = (fileId) => {
    setFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const processFiles = async () => {
    if (files.length === 0) return;

    setProcessing(true);
    
    if (files.length === 1) {
      // Single file processing
      await processSingleFile(files[0]);
    } else {
      // Batch processing
      await processBatchFiles();
    }
    
    setProcessing(false);
  };

  const processSingleFile = async (fileData) => {
    try {
      setProgress({ [fileData.id]: 'processing' });
      
      const fileContent = await fileToBase64(fileData.file);
      
      const response = await axios.post(`${API_BASE}/process-document`, {
        filename: fileData.file.name,
        file_content: fileContent
      });

      setFiles(prev => prev.map(f => 
        f.id === fileData.id 
          ? { ...f, status: 'completed', result: response.data }
          : f
      ));

      setProgress({ [fileData.id]: 'completed' });
      onResults([response.data]);

    } catch (error) {
      setFiles(prev => prev.map(f => 
        f.id === fileData.id 
          ? { ...f, status: 'error', error: error.response?.data?.error || 'Processing failed' }
          : f
      ));
      setProgress({ [fileData.id]: 'error' });
    }
  };

  const processBatchFiles = async () => {
    try {
      // Prepare batch data
      const batchData = await Promise.all(
        files.map(async (fileData) => ({
          id: fileData.id,
          filename: fileData.file.name,
          file_content: await fileToBase64(fileData.file)
        }))
      );

      // Update progress for all files
      const progressUpdate = {};
      files.forEach(f => progressUpdate[f.id] = 'processing');
      setProgress(progressUpdate);

      const response = await axios.post(`${API_BASE}/process-batch`, {
        files: batchData
      });

      // Update files with results
      const results = response.data.results;
      setFiles(prev => prev.map(f => {
        const result = results.find(r => r.batch_id === f.id);
        return {
          ...f,
          status: result ? 'completed' : 'error',
          result: result || null,
          error: result ? null : 'No result returned'
        };
      }));

      // Update progress
      const finalProgress = {};
      files.forEach(f => finalProgress[f.id] = 'completed');
      setProgress(finalProgress);

      onResults(results);

    } catch (error) {
      // Mark all as error
      setFiles(prev => prev.map(f => ({
        ...f,
        status: 'error',
        error: error.response?.data?.error || 'Batch processing failed'
      })));

      const errorProgress = {};
      files.forEach(f => errorProgress[f.id] = 'error');
      setProgress(errorProgress);
    }
  };

  const fileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'ready': return '📄';
      case 'processing': return '⏳';
      case 'completed': return '✅';
      case 'error': return '❌';
      default: return '📄';
    }
  };

  const getProgressText = (fileId) => {
    const status = progress[fileId];
    switch (status) {
      case 'processing': return 'Processing...';
      case 'completed': return 'Completed';
      case 'error': return 'Failed';
      default: return 'Ready';
    }
  };

  return (
    <div className="drdoc-uploader">
      <div className="upload-header">
        <h2>🩺 Dr.Doc - Document Processing</h2>
        <p>Drag & drop documents or click to browse. Supports batch processing!</p>
      </div>

      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'active' : ''} ${files.length > 0 ? 'has-files' : ''}`}
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <div className="drop-message">
            <p>📥 Drop files here...</p>
          </div>
        ) : (
          <div className="drop-message">
            <p>📁 Drag & drop documents here, or click to browse</p>
            <p className="supported-types">
              Supported: PDF, Images, Word docs, Excel, Text files
            </p>
            {supportedTypes.length > 0 && (
              <p className="type-count">
                {supportedTypes.length} file types supported
              </p>
            )}
          </div>
        )}
      </div>

      {files.length > 0 && (
        <div className="file-list">
          <div className="file-list-header">
            <h3>📋 Files ({files.length})</h3>
            <div className="batch-actions">
              <button 
                className="btn process-btn"
                onClick={processFiles}
                disabled={processing}
              >
                {processing ? '⏳ Processing...' : `🚀 Process ${files.length > 1 ? 'Batch' : 'Document'}`}
              </button>
              <button 
                className="btn clear-btn"
                onClick={() => setFiles([])}
                disabled={processing}
              >
                🗑️ Clear All
              </button>
            </div>
          </div>

          <div className="files">
            {files.map((fileData) => (
              <div key={fileData.id} className={`file-item ${fileData.status}`}>
                <div className="file-info">
                  <div className="file-icon">
                    {fileData.preview ? (
                      <img src={fileData.preview} alt="Preview" className="file-preview" />
                    ) : (
                      <span className="file-type-icon">📄</span>
                    )}
                  </div>
                  <div className="file-details">
                    <p className="file-name">{fileData.file.name}</p>
                    <p className="file-size">{(fileData.file.size / 1024).toFixed(1)} KB</p>
                    <p className="file-status">
                      {getStatusIcon(fileData.status)} {getProgressText(fileData.id)}
                    </p>
                    {fileData.error && (
                      <p className="error-message">❌ {fileData.error}</p>
                    )}
                  </div>
                </div>
                <button 
                  className="remove-btn"
                  onClick={() => removeFile(fileData.id)}
                  disabled={processing}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {processing && (
        <div className="processing-overlay">
          <div className="processing-message">
            <div className="spinner">⏳</div>
            <p>Processing {files.length} document{files.length > 1 ? 's' : ''}...</p>
            <p>This may take a few moments</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default DrDocUploader;