"""
Enhanced LLM Extractor with function calling, JSON mode, and confidence scoring
Processes chunked, layout-tagged JSON blocks for better accuracy
"""

import json
import boto3
from typing import Dict, Any, List, Optional

class EnhancedLLMExtractor:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.claude_model_id = 'us.anthropic.claude-sonnet-4-20250514-v1:0'
    
    def extract_with_function_calling(self, layout_blocks: List[Dict], document_type: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data using function calling with JSON schema validation"""
        
        # Chunk the layout blocks to fit context window
        chunked_blocks = self._chunk_layout_blocks(layout_blocks, max_tokens=3000)
        
        results = {}
        
        for chunk_idx, chunk in enumerate(chunked_blocks):
            print(f"Processing chunk {chunk_idx + 1}/{len(chunked_blocks)}")
            
            chunk_result = self._process_chunk_with_function_calling(chunk, document_type, schema)
            
            # Merge results with confidence weighting
            results = self._merge_chunk_results(results, chunk_result)
        
        return results
    
    def _chunk_layout_blocks(self, blocks: List[Dict], max_tokens: int = 3000) -> List[List[Dict]]:
        """Chunk layout blocks to fit within token limits"""
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for block in blocks:
            # Rough token estimation (1 token ≈ 4 characters)
            block_tokens = len(block.get('text', '')) // 4
            
            if current_tokens + block_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [block]
                current_tokens = block_tokens
            else:
                current_chunk.append(block)
                current_tokens += block_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _process_chunk_with_function_calling(self, chunk: List[Dict], document_type: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chunk using function calling with confidence scoring"""
        
        # Create layout-aware context
        layout_context = self._create_layout_context(chunk)
        
        # Generate schema-aware prompt
        prompt = self._create_function_calling_prompt(layout_context, document_type, schema)
        
        try:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock.invoke_model(
                modelId=self.claude_model_id,
                body=json.dumps(payload)
            )
            
            response_body = json.loads(response['body'].read())
            llm_output = response_body['content'][0]['text']
            
            # Parse JSON with validation
            return self._parse_and_validate_json(llm_output, schema)
            
        except Exception as e:
            print(f"Function calling failed: {e}")
            return {'error': str(e), 'confidence': 0.0}
    
    def _create_layout_context(self, chunk: List[Dict]) -> str:
        """Create layout-aware context from chunk"""
        
        context_parts = []
        
        # Group by layout position
        layout_groups = {}
        for block in chunk:
            position = block.get('layout_position', 'unknown')
            if position not in layout_groups:
                layout_groups[position] = []
            layout_groups[position].append(block)
        
        # Create structured context
        for position, blocks in layout_groups.items():
            if blocks:
                context_parts.append(f"\n[{position.upper()}]")
                for block in blocks:
                    confidence_indicator = "🟢" if block.get('confidence', 0) > 0.8 else "🟡" if block.get('confidence', 0) > 0.5 else "🔴"
                    context_parts.append(f"{confidence_indicator} {block.get('text', '')}")
        
        return "\n".join(context_parts)
    
    def _create_function_calling_prompt(self, layout_context: str, document_type: str, schema: Dict[str, Any]) -> str:
        """Create function calling prompt with confidence requirements"""
        
        # Extract field names from schema
        field_names = list(schema.get('properties', {}).keys())
        
        prompt = f"""
You are an expert document parser. Extract data from this {document_type} using the layout-tagged text below.

LAYOUT-TAGGED TEXT:
{layout_context}

REQUIRED OUTPUT FORMAT:
Return ONLY valid JSON matching this exact structure:
{{
  "extracted_fields": {{
    {', '.join([f'"{field}": {{"value": null, "confidence": 0.0}}' for field in field_names])}
  }},
  "overall_confidence": 0.0,
  "extraction_method": "function_calling"
}}

CONFIDENCE SCORING RULES:
- confidence 0.9-1.0: Text exactly matches expected format
- confidence 0.7-0.8: Text is clear but may need minor formatting
- confidence 0.5-0.6: Text is present but ambiguous
- confidence 0.0-0.4: Field not found or very unclear

EXTRACTION RULES:
1. Use layout position hints (HEADER, CENTER, etc.) to locate relevant fields
2. Pay attention to confidence indicators (🟢=high, 🟡=medium, 🔴=low OCR confidence)
3. Return null for missing fields, don't guess
4. Preserve original formatting for numbers and dates
5. Calculate overall_confidence as average of individual field confidences

Extract the data now:
"""
        
        return prompt
    
    def _parse_and_validate_json(self, llm_output: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate JSON output against schema"""
        
        try:
            # Find JSON in output
            json_start = llm_output.find('{')
            json_end = llm_output.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = llm_output[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Validate against schema
                if self._validate_against_schema(parsed_data, schema):
                    return parsed_data
                else:
                    print("Schema validation failed, attempting repair")
                    return self._repair_json_output(parsed_data, schema)
            
            raise ValueError("No valid JSON found in output")
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            return {
                'extracted_fields': {},
                'overall_confidence': 0.0,
                'extraction_method': 'failed',
                'error': str(e)
            }
    
    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate extracted data against schema"""
        
        if 'extracted_fields' not in data:
            return False
        
        extracted_fields = data['extracted_fields']
        required_fields = schema.get('properties', {}).keys()
        
        # Check if all required fields are present
        for field in required_fields:
            if field not in extracted_fields:
                return False
            
            field_data = extracted_fields[field]
            if not isinstance(field_data, dict) or 'value' not in field_data or 'confidence' not in field_data:
                return False
        
        return True
    
    def _repair_json_output(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to repair malformed JSON output"""
        
        repaired = {
            'extracted_fields': {},
            'overall_confidence': 0.0,
            'extraction_method': 'repaired'
        }
        
        # Try to extract fields from malformed data
        if isinstance(data, dict):
            for field in schema.get('properties', {}).keys():
                if field in data:
                    value = data[field]
                    repaired['extracted_fields'][field] = {
                        'value': value,
                        'confidence': 0.5  # Lower confidence for repaired data
                    }
        
        # Calculate overall confidence
        confidences = [f['confidence'] for f in repaired['extracted_fields'].values()]
        if confidences:
            repaired['overall_confidence'] = sum(confidences) / len(confidences)
        
        return repaired
    
    def _merge_chunk_results(self, existing: Dict[str, Any], new_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Merge results from multiple chunks with confidence weighting"""
        
        if not existing:
            return new_chunk
        
        if 'error' in new_chunk:
            return existing
        
        merged = {
            'extracted_fields': existing.get('extracted_fields', {}),
            'overall_confidence': 0.0,
            'extraction_method': 'multi_chunk'
        }
        
        # Merge fields, keeping higher confidence values
        new_fields = new_chunk.get('extracted_fields', {})
        
        for field, field_data in new_fields.items():
            existing_field = merged['extracted_fields'].get(field)
            
            if not existing_field or field_data.get('confidence', 0) > existing_field.get('confidence', 0):
                merged['extracted_fields'][field] = field_data
        
        # Recalculate overall confidence
        confidences = [f['confidence'] for f in merged['extracted_fields'].values()]
        if confidences:
            merged['overall_confidence'] = sum(confidences) / len(confidences)
        
        return merged