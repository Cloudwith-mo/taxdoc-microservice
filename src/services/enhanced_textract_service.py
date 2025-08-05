import boto3
import json
from typing import Dict, Any, List, Optional
import os

class EnhancedTextractService:
    """Enhanced Textract service with Queries support and async processing"""
    
    def __init__(self):
        self.client = boto3.client('textract', region_name='us-east-1')
        self.sns_topic = os.environ.get('TEXTRACT_SNS_TOPIC')
        self.textract_role = os.environ.get('TEXTRACT_ROLE_ARN')
    
    def analyze_with_queries(self, document_bytes: bytes, queries: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze document with Textract Queries (synchronous)"""
        
        query_config = {
            "Queries": [{"Text": q["Text"], "Alias": q["Alias"]} for q in queries]
        }
        
        try:
            response = self.client.analyze_document(
                Document={'Bytes': document_bytes},
                FeatureTypes=['QUERIES'],
                QueriesConfig=query_config
            )
            return response
        except Exception as e:
            print(f"Textract queries failed: {e}")
            return {'Blocks': []}
    
    def start_async_queries(self, bucket: str, key: str, queries: List[Dict[str, str]]) -> str:
        """Start async Textract job with queries"""
        
        query_config = {
            "Queries": [{"Text": q["Text"], "Alias": q["Alias"]} for q in queries]
        }
        
        try:
            response = self.client.start_document_analysis(
                DocumentLocation={'S3Object': {'Bucket': bucket, 'Name': key}},
                FeatureTypes=['QUERIES'],
                QueriesConfig=query_config,
                NotificationChannel={
                    'SNSTopicArn': self.sns_topic,
                    'RoleArn': self.textract_role
                },
                JobTag='DrDoc-Queries'
            )
            return response['JobId']
        except Exception as e:
            print(f"Failed to start async Textract job: {e}")
            raise e
    
    def get_query_results(self, job_id: str) -> Dict[str, Any]:
        """Get results from async Textract job"""
        
        try:
            response = self.client.get_document_analysis(JobId=job_id)
            
            # Handle pagination if needed
            blocks = response.get('Blocks', [])
            while 'NextToken' in response:
                response = self.client.get_document_analysis(
                    JobId=job_id, 
                    NextToken=response['NextToken']
                )
                blocks.extend(response.get('Blocks', []))
            
            return {'Blocks': blocks, 'JobStatus': response.get('JobStatus')}
        except Exception as e:
            print(f"Failed to get Textract results: {e}")
            raise e
    
    def extract_query_answers(self, textract_response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract query answers from Textract response"""
        
        try:
            results = {}
            
            # Validate input
            if not isinstance(textract_response, dict):
                print(f"ERROR: textract_response is not a dict: {type(textract_response)}")
                return {}
            
            # Create a mapping of block IDs to blocks for faster lookup
            blocks_by_id = {block['Id']: block for block in textract_response.get('Blocks', [])}
            
            # Find all QUERY blocks first to get aliases
            query_aliases = {}
            for block in textract_response.get('Blocks', []):
                if block['BlockType'] == 'QUERY':
                    query_aliases[block['Id']] = block.get('Query', {}).get('Alias', '')
            
            # Now find QUERY_RESULT blocks and match them to queries
            for block in textract_response.get('Blocks', []):
                if block['BlockType'] == 'QUERY_RESULT':
                    text = block.get('Text', '').strip()
                    confidence = block.get('Confidence', 0) / 100.0
                    
                    # Find the corresponding query through relationships
                    query_alias = None
                    for relationship in block.get('Relationships', []):
                        if relationship['Type'] == 'ANSWER':
                            for id_ref in relationship['Ids']:
                                if id_ref in query_aliases:
                                    query_alias = query_aliases[id_ref]
                                    break
                            if query_alias:
                                break
                    
                    # If we couldn't find through relationships, try to match by position/content
                    if not query_alias and text:
                        # Use a simple heuristic - match to first available alias
                        available_aliases = [alias for alias in query_aliases.values() if alias not in results]
                        if available_aliases:
                            query_alias = available_aliases[0]
                    
                    if query_alias and text:
                        # Parse the value based on field type
                        parsed_value = self._parse_field_value(text, query_alias)
                        
                        results[query_alias] = {
                            'value': parsed_value,
                            'confidence': confidence,
                            'source': 'textract_query',
                            'raw_text': text
                        }
            
            print(f"Extracted {len(results)} query results from Textract")
            return results
            
        except Exception as e:
            print(f"ERROR: Failed to extract query answers: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _find_block_by_id(self, response: Dict[str, Any], block_id: str) -> Optional[Dict[str, Any]]:
        """Find a block by its ID"""
        for block in response.get('Blocks', []):
            if block.get('Id') == block_id:
                return block
        return None
    
    def _parse_field_value(self, text: str, field_name: str) -> Any:
        """Parse field value based on field type"""
        if not text or text.lower() in ['null', 'none', 'n/a', '', 'not detected']:
            return None
        
        import re
        
        # Monetary fields
        if any(keyword in field_name.lower() for keyword in ['wages', 'tax', 'income', 'amount']):
            # Remove currency symbols and parse as float
            cleaned = re.sub(r'[^\d.]', '', text)
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return text.strip()
        
        # SSN fields
        if 'ssn' in field_name.lower():
            ssn_match = re.search(r'(\d{3}-\d{2}-\d{4})', text)
            return ssn_match.group(1) if ssn_match else text.strip()
        
        # EIN fields
        if 'ein' in field_name.lower():
            ein_match = re.search(r'(\d{2}-\d{7})', text)
            return ein_match.group(1) if ein_match else text.strip()
        
        # Year fields
        if 'year' in field_name.lower():
            year_match = re.search(r'(20\d{2})', text)
            return int(year_match.group(1)) if year_match else text.strip()
        
        # Default: return cleaned text
        return text.strip()