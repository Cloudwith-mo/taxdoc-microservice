import boto3
import os
from typing import Dict, Any, Optional, Tuple

class ComprehendService:
    def __init__(self):
        self.client = boto3.client('comprehend')
        self.endpoint_arn = os.environ.get('COMPREHEND_ENDPOINT', '')
        self.confidence_threshold = float(os.environ.get('COMPREHEND_CONFIDENCE_THRESHOLD', '0.8'))
    
    def classify_document(self, text: str) -> Tuple[Optional[str], float]:
        """
        Classify document using Comprehend custom classifier
        Returns (predicted_label, confidence) or (None, 0.0) if failed/disabled
        """
        if not self.endpoint_arn:
            print("Comprehend endpoint not configured, skipping ML classification")
            return None, 0.0
        
        try:
            # Truncate text if too long (Comprehend has limits)
            max_chars = 5000
            if len(text) > max_chars:
                text = text[:max_chars]
                print(f"Truncated text to {max_chars} characters for Comprehend")
            
            response = self.client.classify_document(
                Text=text,
                EndpointArn=self.endpoint_arn
            )
            
            # Get top prediction
            classes = response.get('Classes', [])
            if classes:
                top_class = classes[0]
                predicted_label = top_class['Name']
                confidence = top_class['Score']
                
                print(f"Comprehend prediction: {predicted_label} (confidence: {confidence:.3f})")
                return predicted_label, confidence
            else:
                print("No classification results from Comprehend")
                return None, 0.0
                
        except Exception as e:
            print(f"Comprehend classification failed: {e}")
            return None, 0.0
    
    def should_use_ml_result(self, confidence: float) -> bool:
        """Check if ML confidence is above threshold"""
        return confidence >= self.confidence_threshold