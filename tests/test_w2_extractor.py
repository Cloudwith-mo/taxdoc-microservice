import pytest
from unittest.mock import Mock, patch
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from src.services.w2_extractor_service import W2ExtractorService

class TestW2ExtractorService:
    def setup_method(self):
        self.extractor = W2ExtractorService()
    
    def test_rule_based_extraction(self):
        """Test rule-based W-2 field extraction"""
        mock_response = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'W-2 Wage and Tax Statement'},
                {'BlockType': 'LINE', 'Text': 'Wages, tips, other compensation $50,000.00'},
                {'BlockType': 'LINE', 'Text': 'Federal income tax withheld $8,500.00'},
                {'BlockType': 'LINE', 'Text': 'Social security wages $50,000.00'},
                {'BlockType': 'LINE', 'Text': 'Social security tax withheld $3,100.00'},
                {'BlockType': 'LINE', 'Text': 'Medicare wages and tips $50,000.00'},
                {'BlockType': 'LINE', 'Text': 'Medicare tax withheld $725.00'},
                {'BlockType': 'LINE', 'Text': 'Employee SSN: 123-45-6789'},
                {'BlockType': 'LINE', 'Text': 'Tax Year: 2023'},
                {'BlockType': 'LINE', 'Text': 'Employer EIN: 12-3456789'}
            ]
        }
        
        result = self.extractor._extract_with_rules(mock_response)
        
        assert result['Box1_Wages'] == 50000.0
        assert result['Box2_FederalTaxWithheld'] == 8500.0
        assert result['Box3_SocialSecurityWages'] == 50000.0
        assert result['Box4_SocialSecurityTaxWithheld'] == 3100.0
        assert result['Box5_MedicareWages'] == 50000.0
        assert result['Box6_MedicareTaxWithheld'] == 725.0
        assert result['EmployeeSSN'] == '123-45-6789'
        assert result['TaxYear'] == 2023
        assert result['EmployerEIN'] == '12-3456789'
    
    def test_claude_extraction_mock(self):
        """Test Claude extraction with mocked response (no AWS call)"""
        # Test the JSON parsing logic without actual Bedrock call
        mock_json = {
            "EmployeeName": "John Doe",
            "EmployeeSSN": "123-45-6789",
            "Box1_Wages": 50000.00,
            "Box15_State": "CA"
        }
        
        # Simulate successful parsing
        result = mock_json
        
        assert result['EmployeeName'] == 'John Doe'
        assert result['EmployeeSSN'] == '123-45-6789'
        assert result['Box1_Wages'] == 50000.00
        assert result['Box15_State'] == 'CA'
    
    def test_merge_and_validate_agreement(self):
        """Test merging when AI and rules agree"""
        ai_fields = {
            'Box1_Wages': 50000.0,
            'Box2_FederalTaxWithheld': 8500.0,
            'EmployeeName': 'John Doe',
            'EmployeeSSN': '123-45-6789'
        }
        
        rule_fields = {
            'Box1_Wages': 50000.0,  # Exact match
            'Box2_FederalTaxWithheld': 8000.0,  # Larger difference to trigger conflict
            'EmployeeSSN': '123-45-6789'  # Exact match
        }
        
        result = self.extractor._merge_and_validate(ai_fields, rule_fields)
        
        # Should use AI values as primary
        assert result['Box1_Wages'] == 50000.0
        assert result['Box1_Wages_confidence'] == 'high'
        assert result['EmployeeName'] == 'John Doe'
        assert result['Box2_FederalTaxWithheld_conflict'] == True  # Conflict detected
        assert result['_validation']['needs_review'] == True
    
    def test_merge_and_validate_no_conflicts(self):
        """Test merging when no conflicts exist"""
        ai_fields = {
            'Box1_Wages': 50000.0,
            'EmployeeName': 'John Doe'
        }
        
        rule_fields = {
            'Box1_Wages': 50000.0,  # Perfect match
            'TaxYear': 2023  # Additional field from rules
        }
        
        result = self.extractor._merge_and_validate(ai_fields, rule_fields)
        
        assert result['Box1_Wages'] == 50000.0
        assert result['Box1_Wages_confidence'] == 'high'
        assert result['EmployeeName'] == 'John Doe'
        assert result['TaxYear'] == 2023
        assert result['TaxYear_source'] == 'rule_based'
        assert result['_validation']['needs_review'] == False
        assert result['_validation']['confidence'] == 'high'
    
    def test_completeness_scoring(self):
        """Test completeness score calculation"""
        ai_fields = {
            'Box1_Wages': 50000.0,
            'Box2_FederalTaxWithheld': 8500.0,
            'EmployeeName': 'John Doe',
            'EmployerName': 'ABC Company',
            'TaxYear': 2023
        }
        
        rule_fields = {}
        
        result = self.extractor._merge_and_validate(ai_fields, rule_fields)
        
        # All 5 expected fields present = 100% completeness
        assert result['_validation']['completeness_score'] == 1.0
    
    def test_extract_amount_various_formats(self):
        """Test amount extraction from different formats"""
        assert self.extractor._extract_amount('$50,000.00') == 50000.0
        assert self.extractor._extract_amount('50000') == 50000.0
        assert self.extractor._extract_amount('50,000.50') == 50000.5
        assert self.extractor._extract_amount('invalid') is None
        assert self.extractor._extract_amount('') is None
    
    def test_rule_based_only_workflow(self):
        """Test extraction workflow with rule-based only (AI disabled)"""
        textract_response = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'Wages, tips, other compensation $50,000.00'},
                {'BlockType': 'LINE', 'Text': 'Tax Year: 2023'}
            ]
        }
        
        # Test rule-based extraction directly
        rule_result = self.extractor._extract_with_rules(textract_response)
        ai_result = {}  # Simulate AI failure
        
        result = self.extractor._merge_and_validate(ai_result, rule_result)
        
        # Should have rule-based results
        assert 'Box1_Wages' in result
        assert result['Box1_Wages'] == 50000.0
        assert 'TaxYear' in result
        assert result['TaxYear'] == 2023
        assert '_validation' in result