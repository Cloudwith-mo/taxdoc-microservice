"""
File Type Detection Service
Implements MIME type detection and file format classification for Any-Doc processing
"""

import magic
import mimetypes
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

class FileTypeDetector:
    def __init__(self):
        self.supported_types = {
            'application/pdf': {'category': 'pdf', 'needs_ocr': True},
            'image/jpeg': {'category': 'image', 'needs_ocr': True},
            'image/png': {'category': 'image', 'needs_ocr': True},
            'image/tiff': {'category': 'image', 'needs_ocr': True},
            'image/webp': {'category': 'image', 'needs_ocr': True},
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {'category': 'docx', 'needs_ocr': False},
            'application/msword': {'category': 'doc', 'needs_ocr': False},
            'text/plain': {'category': 'text', 'needs_ocr': False},
            'application/vnd.ms-excel': {'category': 'excel', 'needs_ocr': False},
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': {'category': 'xlsx', 'needs_ocr': False}
        }
    
    def detect_file_type(self, file_bytes: bytes, filename: str = None) -> Dict[str, Any]:
        """
        Detect file type using magic bytes and filename extension
        Returns: {mime_type, category, needs_ocr, is_supported, confidence}
        """
        # Primary detection using magic bytes
        mime_type = magic.from_buffer(file_bytes, mime=True)
        
        # Fallback to filename extension if magic fails
        if not mime_type or mime_type == 'application/octet-stream':
            if filename:
                mime_type, _ = mimetypes.guess_type(filename)
        
        # Determine processing requirements
        if mime_type in self.supported_types:
            type_info = self.supported_types[mime_type]
            return {
                'mime_type': mime_type,
                'category': type_info['category'],
                'needs_ocr': type_info['needs_ocr'],
                'is_supported': True,
                'confidence': 0.95,
                'processing_route': 'ocr' if type_info['needs_ocr'] else 'text_extraction'
            }
        
        # Handle unsupported but potentially processable types
        if mime_type and mime_type.startswith(('image/', 'application/pdf')):
            return {
                'mime_type': mime_type,
                'category': 'unknown_visual',
                'needs_ocr': True,
                'is_supported': False,
                'confidence': 0.7,
                'processing_route': 'ocr'
            }
        
        return {
            'mime_type': mime_type or 'unknown',
            'category': 'unsupported',
            'needs_ocr': False,
            'is_supported': False,
            'confidence': 0.0,
            'processing_route': 'error'
        }
    
    def is_multi_page_document(self, file_bytes: bytes, mime_type: str) -> bool:
        """Check if document might have multiple pages"""
        if mime_type == 'application/pdf':
            # Simple PDF page count check
            return b'/Count' in file_bytes or file_bytes.count(b'/Page') > 1
        return False
    
    def get_processing_strategy(self, file_info: Dict[str, Any]) -> str:
        """Determine optimal processing strategy based on file type"""
        if not file_info['is_supported']:
            return 'reject'
        
        if file_info['needs_ocr']:
            return 'ocr_pipeline'
        else:
            return 'text_extraction_pipeline'