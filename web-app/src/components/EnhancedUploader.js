import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

const EnhancedUploader = ({ onResults, userTier = 'free' }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [preview, setPreview] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
      
      // Create preview for images
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = () => setPreview(reader.result);
        reader.readAsDataURL(file);
      } else {
        setPreview(null);
      }
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.heic'],
      'application/pdf': ['.pdf']
    },
    maxSize: 10 * 1024 * 1024, // 10MB limit
    multiple: false
  });

  const compressImage = (file) => {
    return new Promise((resolve) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();
      
      img.onload = () => {
        const maxWidth = 1920;
        const maxHeight = 1080;
        let { width, height } = img;
        
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width *= ratio;
          height *= ratio;
        }
        
        canvas.width = width;
        canvas.height = height;
        ctx.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob(resolve, 'image/jpeg', 0.8);
      };
      
      img.src = URL.createObjectURL(file);
    });
  };

  const processDocument = async () => {
    if (!selectedFile) {
      setError('Please select a document to upload');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      let fileToProcess = selectedFile;
      
      // Compress images if needed
      if (selectedFile.type.startsWith('image/') && selectedFile.size > 2 * 1024 * 1024) {
        fileToProcess = await compressImage(selectedFile);
      }

      const base64Content = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
        reader.readAsDataURL(fileToProcess);
      });

      const response = await fetch('https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/process-document', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('cognitoToken') || ''}`
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          file_content: base64Content,
          user_tier: userTier
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Processing failed');
      }

      const uploadResult = await response.json();
      const documentId = uploadResult.document_id;
      
      // Poll for results
      let attempts = 0;
      const maxAttempts = 30;
      
      const pollForResults = async () => {
        try {
          const resultResponse = await fetch(`https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/result/${documentId}`);
          const resultData = await resultResponse.json();
          
          if (resultData.status === 'completed' && resultData.data) {
            onResults(resultData);
            return;
          }
          
          if (resultData.status === 'failed') {
            throw new Error('Document processing failed');
          }
          
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(pollForResults, 1000);
          } else {
            throw new Error('Processing timeout - please try again');
          }
        } catch (pollError) {
          setError(`Processing failed: ${pollError.message}`);
          setIsProcessing(false);
        }
      };
      
      setTimeout(pollForResults, 2000);

    } catch (err) {
      setError(`Processing failed: ${err.message}`);
      setIsProcessing(false);
    }
  };

  return (
    <div className="enhanced-uploader">
      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'active' : ''} ${selectedFile ? 'has-file' : ''}`}
      >
        <input {...getInputProps()} />
        
        {preview ? (
          <div className="file-preview">
            <img src={preview} alt="Preview" className="preview-image" />
            <div className="file-info">
              <span className="file-name">📎 {selectedFile.name}</span>
              <span className="file-size">({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
            </div>
          </div>
        ) : selectedFile ? (
          <div className="file-info">
            <div className="file-icon">📄</div>
            <span className="file-name">📎 {selectedFile.name}</span>
            <span className="file-size">({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
          </div>
        ) : (
          <div className="upload-prompt">
            <div className="upload-icon">
              {isDragActive ? '📤' : '📷'}
            </div>
            <div className="upload-text">
              {isDragActive ? (
                <p>Drop your document here...</p>
              ) : (
                <>
                  <p><strong>Drag & drop a photo or document</strong></p>
                  <p>or click to browse</p>
                  <div className="supported-formats">
                    📱 Photos (JPEG, PNG, HEIC) • 📄 PDFs • 🖼️ Images
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      <button 
        onClick={processDocument}
        disabled={!selectedFile || isProcessing}
        className="process-button enhanced"
      >
        {isProcessing ? (
          <>
            <span className="spinner">⏳</span>
            Processing Document...
          </>
        ) : (
          <>
            🤖 Extract Data with AI
          </>
        )}
      </button>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
    </div>
  );
};

export default EnhancedUploader;