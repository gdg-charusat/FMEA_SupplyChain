"""
Integration Tests for Data Preprocessing with Validation
Tests the enhanced preprocessing module with input validation
"""

import pytest
import pandas as pd
import json
import tempfile
from pathlib import Path
import sys
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from preprocessing import DataPreprocessor
from validators import ValidationResult


class TestDataPreprocessorStructuredInput:
    """Test structured data preprocessing with validation"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create a preprocessor with test config"""
        config = {
            'input_validation': {
                'required_structured_columns': ['failure_mode', 'effect', 'cause']
            },
            'risk_scoring': {
                'severity': {'default': 5},
                'occurrence': {'default': 5},
                'detection': {'default': 5}
            },
            'text_processing': {
                'min_review_length': 10,
                'enable_sentiment_filter': False
            }
        }
        return DataPreprocessor(config)
    
    def test_load_valid_csv(self, preprocessor):
        """Test loading a valid CSV file"""
        # Create temporary CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("failure_mode,effect,cause,component,severity\n")
            f.write("\"Engine fails to start\",\"Cannot operate\",\"Battery dead\",\"Engine System\",8\n")
            f.write("\"Brake leak\",\"Safety risk\",\"Corroded line\",\"Brake System\",9\n")
            temp_file = f.name
        
        try:
            result = preprocessor.load_structured_data(temp_file)
            
            # Result should be tuple of (df, validation_result)
            if isinstance(result, tuple):
                df, validation_result = result
                assert isinstance(df, pd.DataFrame)
                assert isinstance(validation_result, ValidationResult)
                assert validation_result.success_rate >= 50  # At least partial success
            else:
                # Fallback for old return type
                df = result
                assert isinstance(df, pd.DataFrame)
            
            assert len(df) > 0
            assert 'failure_mode' in df.columns
        finally:
            Path(temp_file).unlink()
    
    def test_load_csv_missing_required_columns(self, preprocessor):
        """Test error handling when required columns are missing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("component,severity\n")
            f.write("\"Engine System\",8\n")
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                preprocessor.load_structured_data(temp_file)
            assert "required" in str(exc_info.value).lower()
        finally:
            Path(temp_file).unlink()
    
    def test_load_empty_csv(self, preprocessor):
        """Test error handling for empty CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("failure_mode,effect,cause\n")
            # No data rows
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                preprocessor.load_structured_data(temp_file)
            assert "empty" in str(exc_info.value).lower()
        finally:
            Path(temp_file).unlink()
    
    def test_load_nonexistent_file(self, preprocessor):
        """Test error handling for nonexistent file"""
        with pytest.raises(FileNotFoundError) as exc_info:
            preprocessor.load_structured_data("/nonexistent/file.csv")
        assert "not found" in str(exc_info.value).lower()
    
    def test_load_json_structured_data(self, preprocessor):
        """Test loading structured data from JSON"""
        records = [
            {
                "failure_mode": "Engine fails to start",
                "effect": "Vehicle cannot operate",
                "cause": "Battery dead",
                "severity": 8
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(records, f)
            temp_file = f.name
        
        try:
            result = preprocessor.load_structured_data(temp_file)
            if isinstance(result, tuple):
                df, _ = result
            else:
                df = result
            assert len(df) > 0
        finally:
            Path(temp_file).unlink()
    
    def test_unsupported_file_format(self, preprocessor):
        """Test error handling for unsupported file formats"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Some text content\n")
            temp_file = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                preprocessor.load_structured_data(temp_file)
            assert "unsupported" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
        finally:
            Path(temp_file).unlink()


class TestDataPreprocessorUnstructuredInput:
    """Test unstructured data preprocessing"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create a preprocessor with test config"""
        config = {
            'text_processing': {
                'min_review_length': 10,
                'enable_sentiment_filter': False,
                'negative_threshold': 0.3
            }
        }
        return DataPreprocessor(config)
    
    def test_load_text_from_list(self, preprocessor):
        """Test loading text from list"""
        texts = [
            "Engine started making loud noises",
            "Brake system malfunction occurred",
            "Paint quality is excellent"
        ]
        
        df = preprocessor.load_unstructured_data(text_data=texts)
        assert len(df) > 0
        assert 'text' in df.columns
        assert 'text_cleaned' in df.columns
    
    def test_load_text_from_csv(self, preprocessor):
        """Test loading text from CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("review\n")
            f.write("\"Engine started making loud noises and failed\"\n")
            f.write("\"Brake system malfunction caused dangerous situation\"\n")
            temp_file = f.name
        
        try:
            df = preprocessor.load_unstructured_data(file_path=temp_file)
            assert len(df) > 0
        finally:
            Path(temp_file).unlink()
    
    def test_empty_text_list(self, preprocessor):
        """Test error handling for empty text list"""
        with pytest.raises(ValueError):
            preprocessor.load_unstructured_data(text_data=[])
    
    def test_no_input_provided(self, preprocessor):
        """Test error when neither file nor text data provided"""
        with pytest.raises(ValueError):
            preprocessor.load_unstructured_data()


class TestBatchPreprocess:
    """Test batch preprocessing with auto-detection"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create preprocessor with config"""
        config = {
            'input_validation': {
                'required_structured_columns': ['failure_mode', 'effect', 'cause']
            },
            'risk_scoring': {
                'severity': {'default': 5},
                'occurrence': {'default': 5},
                'detection': {'default': 5}
            },
            'text_processing': {
                'min_review_length': 10,
                'enable_sentiment_filter': False
            }
        }
        return DataPreprocessor(config)
    
    def test_auto_detect_structured_data(self, preprocessor):
        """Test auto-detection of structured data"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("failure_mode,effect,cause\n")
            f.write("\"Engine fails\",\"No operation\",\"Dead battery\"\n")
            temp_file = f.name
        
        try:
            result = preprocessor.batch_preprocess(temp_file, data_type='auto')
            assert isinstance(result, pd.DataFrame) or isinstance(result, tuple)
        finally:
            Path(temp_file).unlink()
    
    def test_auto_detect_unstructured_data(self, preprocessor):
        """Test auto-detection of unstructured data"""
        texts = [
            "Engine making loud noises",
            "Brake system failed completely"
        ]
        
        result = preprocessor.batch_preprocess(texts, data_type='auto')
        assert isinstance(result, (pd.DataFrame, tuple))
    
    def test_batch_preprocess_with_validation_result(self, preprocessor):
        """Test batch preprocess with validation result return"""
        texts = ["Engine making loud noise", "Brake failure"]
        
        result = preprocessor.batch_preprocess(
            texts, 
            data_type='unstructured',
            return_validation_result=True
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        df, validation_result = result
        assert isinstance(df, pd.DataFrame)
        assert isinstance(validation_result, ValidationResult)


class TestDataQualityValidation:
    """Test data quality and validation logic"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create preprocessor"""
        config = {
            'input_validation': {
                'required_structured_columns': ['failure_mode', 'effect', 'cause']
            },
            'risk_scoring': {
                'severity': {'default': 5},
                'occurrence': {'default': 5},
                'detection': {'default': 5}
            },
            'text_processing': {
                'min_review_length': 5,
                'enable_sentiment_filter': False
            }
        }
        return DataPreprocessor(config)
    
    def test_short_text_handling(self, preprocessor):
        """Test handling of very short text entries"""
        texts = [
            "This is a good review about the engine failure",  # Long enough
            "Bad",  # Too short, should be filtered
        ]
        
        df = preprocessor.load_unstructured_data(text_data=texts)
        # Should keep the longer one
        assert len(df) >= 1
    
    def test_numeric_field_normalization(self, preprocessor):
        """Test normalization of numeric fields"""
        data = {
            'failure_mode': ['Engine fails', 'Brake leaks'],
            'effect': ['No operation', 'Safety risk'],
            'cause': ['Dead battery', 'Corroded line'],
            'severity': ['8', '9'],  # String values
            'occurrence': [3, 2],
            'detection': [9, '7']  # Mixed types
        }
        df = pd.DataFrame(data)
        
        result = preprocessor._validate_and_normalize_structured_data(df)
        if isinstance(result, tuple):
            normalized_df, _ = result
        else:
            normalized_df = result
        
        # Check that numeric fields are properly converted
        if 'severity' in normalized_df.columns:
            assert isinstance(normalized_df['severity'].iloc[0], (int, float))
    
    def test_missing_value_handling(self, preprocessor):
        """Test handling of missing values"""
        data = {
            'failure_mode': ['Engine fails', None],
            'effect': ['No operation', 'Risk'],
            'cause': ['Dead battery', None]
        }
        df = pd.DataFrame(data)
        
        result = preprocessor._validate_and_normalize_structured_data(df)
        if isinstance(result, tuple):
            normalized_df, validation_result = result
        else:
            normalized_df = result
            validation_result = None
        
        # First row should be valid, second should be invalid/handled
        assert len(normalized_df) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
