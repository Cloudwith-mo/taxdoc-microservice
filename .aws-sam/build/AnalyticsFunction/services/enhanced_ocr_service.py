"""
Enhanced OCR Service with Textract TABLES & FORMS + docTR fallback
Stores blocks and bounding boxes for preview overlays
"""

import boto3
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple

class EnhancedOCRService:
    def __init__(self):
        self.textract = boto3.client('textract', region_name='us-east-1')
        self.cache = {}  # In-memory cache for demo (use Redis in production)
    
    def analyze_document_enhanced(self, document_bytes: bytes) -> Dict[str, Any]:
        """Enhanced document analysis with caching and layout detection"""
        
        # Generate cache key
        doc_hash = hashlib.sha256(document_bytes).hexdigest()
        
        if doc_hash in self.cache:
            print(f"Cache hit for document {doc_hash[:8]}")
            return self.cache[doc_hash]
        
        try:
            # Use Textract with TABLES and FORMS features
            response = self.textract.analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=['TABLES', 'FORMS', 'LAYOUT', 'QUERIES']
            )
            
            # Process and structure the response
            structured_result = self._process_textract_response(response)
            
            # Cache the result
            self.cache[doc_hash] = structured_result
            
            return structured_result
            
        except Exception as e:
            print(f"Textract failed: {e}, falling back to basic OCR")
            return self._fallback_ocr(document_bytes)
    
    def _process_textract_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process Textract response into structured format with bounding boxes"""
        
        result = {
            'blocks': [],
            'tables': [],
            'forms': [],
            'layout_elements': [],
            'confidence_scores': [],
            'bounding_boxes': {},
            'text_blocks_with_layout': []
        }
        
        # Process all blocks
        for block in response.get('Blocks', []):
            block_id = block.get('Id')
            block_type = block.get('BlockType')
            confidence = block.get('Confidence', 0) / 100.0
            
            # Store bounding box for preview overlays
            if 'Geometry' in block:
                bbox = block['Geometry'].get('BoundingBox', {})
                result['bounding_boxes'][block_id] = {
                    'left': bbox.get('Left', 0),
                    'top': bbox.get('Top', 0),
                    'width': bbox.get('Width', 0),
                    'height': bbox.get('Height', 0)
                }
            
            if block_type == 'LINE':
                result['blocks'].append({
                    'id': block_id,
                    'text': block.get('Text', ''),
                    'confidence': confidence,
                    'bbox': result['bounding_boxes'].get(block_id, {}),
                    'type': 'line'
                })
                result['confidence_scores'].append(confidence)
                
            elif block_type == 'TABLE':
                result['tables'].append({
                    'id': block_id,
                    'confidence': confidence,
                    'bbox': result['bounding_boxes'].get(block_id, {}),
                    'relationships': block.get('Relationships', [])
                })
                
            elif block_type == 'KEY_VALUE_SET':
                entity_types = block.get('EntityTypes', [])
                if 'KEY' in entity_types:
                    result['forms'].append({
                        'id': block_id,
                        'text': block.get('Text', ''),
                        'confidence': confidence,
                        'bbox': result['bounding_boxes'].get(block_id, {}),
                        'type': 'key',
                        'relationships': block.get('Relationships', [])
                    })
        
        # Create layout-tagged JSON blocks for LLM
        result['text_blocks_with_layout'] = self._create_layout_tagged_blocks(result['blocks'])
        
        # Calculate overall confidence
        if result['confidence_scores']:
            result['overall_confidence'] = sum(result['confidence_scores']) / len(result['confidence_scores'])
        else:
            result['overall_confidence'] = 0.0
        
        return result
    
    def _create_layout_tagged_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Create layout-tagged JSON blocks for LLM processing"""
        
        layout_blocks = []
        
        for block in blocks:
            bbox = block.get('bbox', {})
            
            # Determine layout position
            layout_tag = self._determine_layout_position(bbox)
            
            layout_blocks.append({
                'text': block['text'],
                'confidence': block['confidence'],
                'layout_position': layout_tag,
                'coordinates': {
                    'x': bbox.get('left', 0),
                    'y': bbox.get('top', 0),
                    'width': bbox.get('width', 0),
                    'height': bbox.get('height', 0)
                }
            })
        
        return layout_blocks
    
    def _determine_layout_position(self, bbox: Dict) -> str:
        """Determine layout position based on bounding box"""
        
        if not bbox:
            return 'unknown'
        
        x = bbox.get('left', 0)
        y = bbox.get('top', 0)
        
        # Simple layout classification
        if y < 0.2:
            return 'header'
        elif y > 0.8:
            return 'footer'
        elif x < 0.3:
            return 'left_column'
        elif x > 0.7:
            return 'right_column'
        else:
            return 'center'
    
    def _fallback_ocr(self, document_bytes: bytes) -> Dict[str, Any]:
        """Fallback OCR using basic Textract"""
        
        try:
            response = self.textract.detect_document_text(
                Document={'Bytes': document_bytes}
            )
            
            blocks = []
            confidence_scores = []
            
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    confidence = block.get('Confidence', 0) / 100.0
                    blocks.append({
                        'id': block.get('Id'),
                        'text': block.get('Text', ''),
                        'confidence': confidence,
                        'bbox': {},
                        'type': 'line'
                    })
                    confidence_scores.append(confidence)
            
            return {
                'blocks': blocks,
                'tables': [],
                'forms': [],
                'layout_elements': [],
                'confidence_scores': confidence_scores,
                'bounding_boxes': {},
                'text_blocks_with_layout': [{'text': b['text'], 'confidence': b['confidence'], 'layout_position': 'unknown'} for b in blocks],
                'overall_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            }
            
        except Exception as e:
            print(f"Fallback OCR failed: {e}")
            return {
                'blocks': [],
                'tables': [],
                'forms': [],
                'layout_elements': [],
                'confidence_scores': [],
                'bounding_boxes': {},
                'text_blocks_with_layout': [],
                'overall_confidence': 0.0,
                'error': str(e)
            }
    
    def get_preview_overlays(self, doc_hash: str) -> Dict[str, Any]:
        """Get bounding boxes for document preview overlays"""
        
        if doc_hash in self.cache:
            result = self.cache[doc_hash]
            return {
                'bounding_boxes': result.get('bounding_boxes', {}),
                'confidence_map': {
                    block['id']: block['confidence'] 
                    for block in result.get('blocks', [])
                }
            }
        
        return {'bounding_boxes': {}, 'confidence_map': {}}