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
            
            for block in textract_response.get('Blocks', []):
                if block['BlockType'] == 'QUERY_RESULT':
                    # Find the corresponding query
                    query_alias = None
                    for relationship in block.get('Relationships', []):
                        if relationship['Type'] == 'ANSWER':
                            for id_ref in relationship['Ids']:
                                # Find the query block
                                query_block = self._find_block_by_id(textract_response, id_ref)
                                if query_block and query_block['BlockType'] == 'QUERY':
                                    query_alias = query_block.get('Query', {}).get('Alias')
                                    break
                    
                    if query_alias:
                        results[query_alias] = {
                            'value': block.get('Text', ''),
                            'confidence': block.get('Confidence', 0) / 100.0,
                            'source': 'textract_query'
                        }
            
            return results
            
        except Exception as e:
            print(f"ERROR: Failed to extract query answers: {str(e)}")
            return {}
    
    def _find_block_by_id(self, response: Dict[str, Any], block_id: str) -> Optional[Dict[str, Any]]:
        """Find a block by its ID"""
        for block in response.get('Blocks', []):
            if block.get('Id') == block_id:
                return block
        return None