import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Stage, Layer, Rect } from 'react-konva';
import './DocumentPreview.css';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

const DocumentPreview = ({ documentUrl, boundingBoxes = {}, onEntityClick, selectedEntity }) => {
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageWidth, setPageWidth] = useState(600);
  const [pageHeight, setPageHeight] = useState(800);
  const [isImage, setIsImage] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    // Detect if document is an image
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.tiff'];
    const isImg = imageExtensions.some(ext => documentUrl?.toLowerCase().includes(ext));
    setIsImage(isImg);
  }, [documentUrl]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  const onPageLoadSuccess = (page) => {
    const { width, height } = page.getViewport({ scale: 1 });
    setPageWidth(width);
    setPageHeight(height);
  };

  const renderBoundingBoxes = () => {
    if (!boundingBoxes || Object.keys(boundingBoxes).length === 0) {
      return null;
    }

    return Object.entries(boundingBoxes).map(([entityId, bbox]) => {
      const isSelected = selectedEntity === entityId;
      
      return (
        <Rect
          key={entityId}
          x={bbox.left * pageWidth}
          y={bbox.top * pageHeight}
          width={bbox.width * pageWidth}
          height={bbox.height * pageHeight}
          fill={isSelected ? 'rgba(20, 184, 166, 0.4)' : 'rgba(20, 184, 166, 0.2)'}
          stroke={isSelected ? '#14B8A6' : '#2DD4BF'}
          strokeWidth={isSelected ? 3 : 1}
          onClick={() => onEntityClick && onEntityClick(entityId)}
          onTap={() => onEntityClick && onEntityClick(entityId)}
          style={{ cursor: 'pointer' }}
        />
      );
    });
  };

  const renderImagePreview = () => {
    return (
      <div className="image-preview-container">
        <div className="image-wrapper" style={{ position: 'relative' }}>
          <img
            src={documentUrl}
            alt="Document preview"
            className="document-image"
            onLoad={(e) => {
              setPageWidth(e.target.naturalWidth);
              setPageHeight(e.target.naturalHeight);
            }}
          />
          <Stage
            width={pageWidth}
            height={pageHeight}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              pointerEvents: 'auto'
            }}
          >
            <Layer>
              {renderBoundingBoxes()}
            </Layer>
          </Stage>
        </div>
      </div>
    );
  };

  const renderPdfPreview = () => {
    return (
      <div className="pdf-preview-container">
        <Document
          file={documentUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={<div className="loading">Loading PDF...</div>}
          error={<div className="error">Failed to load PDF</div>}
        >
          <div style={{ position: 'relative' }}>
            <Page
              pageNumber={pageNumber}
              onLoadSuccess={onPageLoadSuccess}
              width={600}
              loading={<div className="loading">Loading page...</div>}
            />
            <Stage
              width={pageWidth}
              height={pageHeight}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                pointerEvents: 'auto'
              }}
            >
              <Layer>
                {renderBoundingBoxes()}
              </Layer>
            </Stage>
          </div>
        </Document>

        {numPages && numPages > 1 && (
          <div className="page-controls">
            <button
              onClick={() => setPageNumber(Math.max(1, pageNumber - 1))}
              disabled={pageNumber <= 1}
              className="page-btn"
            >
              Previous
            </button>
            <span className="page-info">
              Page {pageNumber} of {numPages}
            </span>
            <button
              onClick={() => setPageNumber(Math.min(numPages, pageNumber + 1))}
              disabled={pageNumber >= numPages}
              className="page-btn"
            >
              Next
            </button>
          </div>
        )}
      </div>
    );
  };

  if (!documentUrl) {
    return (
      <div className="document-preview">
        <div className="no-document">
          <p>No document to preview</p>
        </div>
      </div>
    );
  }

  return (
    <div className="document-preview" ref={containerRef}>
      <div className="preview-header">
        <h3>📄 Document Preview</h3>
        {Object.keys(boundingBoxes).length > 0 && (
          <p className="bbox-info">
            {Object.keys(boundingBoxes).length} detected regions
          </p>
        )}
      </div>

      <div className="preview-content">
        {isImage ? renderImagePreview() : renderPdfPreview()}
      </div>

      <div className="preview-legend">
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: 'rgba(20, 184, 166, 0.2)' }}></div>
          <span>Detected Fields</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ backgroundColor: 'rgba(20, 184, 166, 0.4)' }}></div>
          <span>Selected Field</span>
        </div>
      </div>
    </div>
  );
};

export default DocumentPreview;