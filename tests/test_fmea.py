"""
Unit tests for FMEA Generator components
Run with: pytest tests/test_fmea.py
"""

import pytest
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from preprocessing import DataPreprocessor
from risk_scoring import RiskScoringEngine
from fmea_generator import FMEAGenerator
import yaml


@pytest.fixture
def config():
    """Load test configuration"""
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


@pytest.fixture
def sample_texts():
    """Sample text data for testing"""
    return [
        "The brake system failed completely during highway driving.",
        "Engine overheated and caused severe damage.",
        "Airbag did not deploy during collision."
    ]


@pytest.fixture
def sample_structured_data():
    """Sample structured data for testing"""
    return pd.DataFrame({
        'failure_mode': ['Brake failure', 'Engine overheating'],
        'effect': ['Cannot stop', 'Engine damage'],
        'cause': ['Worn brake pads', 'Coolant leak'],
        'component': ['Brake system', 'Engine'],
        'existing_controls': ['Regular inspection', 'Temperature monitoring']
    })


class TestDataPreprocessor:
    """Tests for DataPreprocessor class"""
    
    def test_initialization(self, config):
        """Test preprocessor initialization"""
        preprocessor = DataPreprocessor(config)
        assert preprocessor.config == config
        assert preprocessor.stop_words is not None
    
    def test_clean_text(self, config):
        """Test text cleaning"""
        preprocessor = DataPreprocessor(config)
        
        dirty_text = "This is a TEST!!! With   extra spaces   and CAPS"
        clean_text = preprocessor._clean_text(dirty_text)
        
        assert clean_text.islower()
        assert '!!!' not in clean_text
        assert '   ' not in clean_text
    
    def test_sentiment_calculation(self, config):
        """Test sentiment analysis"""
        preprocessor = DataPreprocessor(config)
        
        positive_text = "excellent quality, very satisfied, great product"
        negative_text = "terrible quality, failed completely, dangerous situation"
        
        pos_sentiment = preprocessor._get_sentiment(positive_text)
        neg_sentiment = preprocessor._get_sentiment(negative_text)
        
        assert pos_sentiment > 0
        assert neg_sentiment < 0
    
    def test_load_unstructured_data(self, config, sample_texts):
        """Test loading unstructured data"""
        preprocessor = DataPreprocessor(config)
        
        df = preprocessor.load_unstructured_data(text_data=sample_texts)
        
        assert len(df) > 0
        assert 'text_cleaned' in df.columns
        assert 'sentiment' in df.columns
    
    def test_structured_data_validation(self, config, sample_structured_data):
        """Test structured data validation"""
        preprocessor = DataPreprocessor(config)
        
        validated_df = preprocessor._validate_structured_data(sample_structured_data)
        
        assert 'failure_mode' in validated_df.columns
        assert 'effect' in validated_df.columns
        assert 'cause' in validated_df.columns


class TestRiskScoringEngine:
    """Tests for RiskScoringEngine class"""
    
    def test_initialization(self, config):
        """Test scorer initialization"""
        scorer = RiskScoringEngine(config)
        assert scorer.config == config
        assert scorer.severity_keywords is not None
    
    def test_severity_calculation(self, config):
        """Test severity score calculation"""
        scorer = RiskScoringEngine(config)
        
        # Critical failure
        severity_critical = scorer.calculate_severity(
            "Complete brake failure",
            "Unable to stop, life-threatening situation"
        )
        
        # Minor failure
        severity_minor = scorer.calculate_severity(
            "Paint chip",
            "Cosmetic issue only"
        )
        
        assert severity_critical > severity_minor
        assert 1 <= severity_critical <= 10
        assert 1 <= severity_minor <= 10
    
    def test_occurrence_calculation(self, config):
        """Test occurrence score calculation"""
        scorer = RiskScoringEngine(config)
        
        # Frequent failure
        occurrence_high = scorer.calculate_occurrence(
            "Frequently occurs, happens constantly"
        )
        
        # Rare failure
        occurrence_low = scorer.calculate_occurrence(
            "Very rare, only happened once"
        )
        
        assert occurrence_high > occurrence_low
        assert 1 <= occurrence_high <= 10
    
    def test_detection_calculation(self, config):
        """Test detection score calculation"""
        scorer = RiskScoringEngine(config)
        
        # Hard to detect (high score)
        detection_hard = scorer.calculate_detection(
            "Hidden internal failure",
            "No controls in place"
        )
        
        # Easy to detect (low score)
        detection_easy = scorer.calculate_detection(
            "Obvious failure with warning light",
            "Sensor monitoring, visual inspection"
        )
        
        assert detection_hard > detection_easy
        assert 1 <= detection_hard <= 10
    
    def test_rpn_calculation(self, config):
        """Test RPN calculation"""
        scorer = RiskScoringEngine(config)
        
        rpn = scorer.calculate_rpn(8, 7, 6)
        assert rpn == 336
        
        rpn_max = scorer.calculate_rpn(10, 10, 10)
        assert rpn_max == 1000
        
        rpn_min = scorer.calculate_rpn(1, 1, 1)
        assert rpn_min == 1
    
    def test_action_priority(self, config):
        """Test action priority classification"""
        scorer = RiskScoringEngine(config)
        
        # Critical
        priority = scorer.calculate_action_priority(10, 9, 8)
        assert priority == 'Critical'
        
        # Low
        priority = scorer.calculate_action_priority(2, 2, 2)
        assert priority == 'Low'


class TestFMEAGenerator:
    """Tests for FMEAGenerator class"""
    
    def test_initialization(self, config):
        """Test generator initialization"""
        # Use rule-based mode for faster testing
        config['model']['name'] = None
        generator = FMEAGenerator(config)
        
        assert generator.preprocessor is not None
        assert generator.scorer is not None
    
    def test_generate_from_text(self, config, sample_texts):
        """Test FMEA generation from text"""
        config['model']['name'] = None  # Rule-based for speed
        generator = FMEAGenerator(config)
        
        fmea_df = generator.generate_from_text(sample_texts, is_file=False)
        
        assert len(fmea_df) > 0
        assert 'Failure Mode' in fmea_df.columns
        assert 'Rpn' in fmea_df.columns
        assert 'Action Priority' in fmea_df.columns
    
    def test_generate_from_structured(self, config, sample_structured_data, tmp_path):
        """Test FMEA generation from structured data"""
        config['model']['name'] = None
        generator = FMEAGenerator(config)
        
        # Save to temporary CSV
        csv_path = tmp_path / "test_data.csv"
        sample_structured_data.to_csv(csv_path, index=False)
        
        fmea_df = generator.generate_from_structured(str(csv_path))
        
        assert len(fmea_df) > 0
        assert 'Severity' in fmea_df.columns
        assert 'Occurrence' in fmea_df.columns
        assert 'Detection' in fmea_df.columns
    
    def test_export_fmea(self, config, sample_structured_data, tmp_path):
        """Test FMEA export functionality"""
        config['model']['name'] = None
        generator = FMEAGenerator(config)
        
        # Generate FMEA
        csv_path = tmp_path / "test_data.csv"
        sample_structured_data.to_csv(csv_path, index=False)
        fmea_df = generator.generate_from_structured(str(csv_path))
        
        # Export to Excel
        output_path = tmp_path / "test_output.xlsx"
        generator.export_fmea(fmea_df, str(output_path), format='excel')
        
        assert output_path.exists()
        
        # Verify can read back
        read_df = pd.read_excel(output_path)
        assert len(read_df) == len(fmea_df)


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_end_to_end_unstructured(self, config, sample_texts):
        """Test complete pipeline for unstructured data"""
        config['model']['name'] = None
        generator = FMEAGenerator(config)
        
        # Generate FMEA
        fmea_df = generator.generate_from_text(sample_texts, is_file=False)
        
        # Verify structure
        assert len(fmea_df) > 0
        
        required_columns = [
            'Failure Mode', 'Effect', 'Cause', 'Severity', 
            'Occurrence', 'Detection', 'Rpn', 'Action Priority'
        ]
        
        for col in required_columns:
            assert col in fmea_df.columns
        
        # Verify scores are in valid range
        assert fmea_df['Severity'].between(1, 10).all()
        assert fmea_df['Occurrence'].between(1, 10).all()
        assert fmea_df['Detection'].between(1, 10).all()
        assert fmea_df['Rpn'].between(1, 1000).all()
    
    def test_end_to_end_structured(self, config, sample_structured_data, tmp_path):
        """Test complete pipeline for structured data"""
        config['model']['name'] = None
        generator = FMEAGenerator(config)
        
        # Save and process
        csv_path = tmp_path / "test.csv"
        sample_structured_data.to_csv(csv_path, index=False)
        
        fmea_df = generator.generate_from_structured(str(csv_path))
        
        # Verify all expected columns exist
        assert 'Rpn' in fmea_df.columns
        assert 'Recommended Action' in fmea_df.columns
        
        # Verify recommendations were generated
        assert not fmea_df['Recommended Action'].isna().all()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
