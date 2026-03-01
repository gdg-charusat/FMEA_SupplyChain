"""
Unit Tests for Input Validation Module
Tests Pydantic models, validators, and error handling
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from validators import (
    FMEARecord,
    StructuredCSVInput,
    UnstructuredTextInput,
    ValidationError,
    ValidationResult,
    SeverityLevel,
    validate_fmea_record,
    validate_csv_headers,
    get_user_friendly_error,
    CSVTemplate
)


class TestFMEARecord:
    """Test FMEARecord Pydantic model validation"""
    
    def test_valid_minimal_record(self):
        """Test creating a valid record with only required fields"""
        record = FMEARecord(
            failure_mode="Engine fails to start",
            effect="Vehicle cannot be operated",
            cause="Battery dead"
        )
        assert record.failure_mode == "Engine fails to start"
        assert record.severity is None  # Optional
        assert record.component is None  # Optional
    
    def test_valid_complete_record(self):
        """Test creating a complete record with all fields"""
        record = FMEARecord(
            failure_mode="Engine fails to start",
            effect="Vehicle cannot operate",
            cause="Battery dead or starter malfunction",
            component="Engine Starter System",
            process="Engine Start Sequence",
            severity=8,
            occurrence=3,
            detection=9,
            existing_controls="Visual inspection",
            recommended_action="Replace battery",
            responsibility="Maintenance Team",
            target_completion_date="2024-03-15",
            additional_notes="Common in winter conditions",
            source="customer_review"
        )
        assert record.failure_mode == "Engine fails to start"
        assert record.severity == 8
        assert record.occurrence == 3
        assert record.detection == 9
        assert record.source == "customer_review"
    
    def test_missing_required_field(self):
        """Test that missing required fields raise validation error"""
        with pytest.raises(Exception):
            FMEARecord(
                failure_mode="Engine fails",
                # Missing 'effect' and 'cause'
            )
    
    def test_short_text_field(self):
        """Test that text fields below minimum length are rejected"""
        with pytest.raises(Exception):
            FMEARecord(
                failure_mode="fail",  # Too short (< 5 chars)
                effect="Vehicle cannot operate",
                cause="Battery dead"
            )
    
    def test_long_text_field(self):
        """Test that text fields exceeding maximum length are rejected"""
        long_text = "x" * 501  # Exceeds 500 char limit
        with pytest.raises(Exception):
            FMEARecord(
                failure_mode=long_text,
                effect="Vehicle cannot operate",
                cause="Battery dead"
            )
    
    def test_invalid_severity_score(self):
        """Test that severity scores outside 1-10 range are rejected"""
        with pytest.raises(Exception):
            FMEARecord(
                failure_mode="Engine fails",
                effect="Vehicle cannot operate",
                cause="Battery dead",
                severity=15  # Invalid, must be 1-10
            )
    
    def test_numeric_string_conversion(self):
        """Test that numeric strings are converted to integers"""
        record = FMEARecord(
            failure_mode="Engine fails",
            effect="Vehicle cannot operate",
            cause="Battery dead",
            severity="8",  # String, should convert to int
            occurrence="3",
            detection="9"
        )
        assert record.severity == 8
        assert isinstance(record.severity, int)
    
    def test_invalid_date_format(self):
        """Test that invalid date formats are rejected"""
        with pytest.raises(Exception):
            FMEARecord(
                failure_mode="Engine fails",
                effect="Vehicle cannot operate",
                cause="Battery dead",
                target_completion_date="15/03/2024"  # Wrong format
            )
    
    def test_valid_date_format(self):
        """Test that valid date format is accepted"""
        record = FMEARecord(
            failure_mode="Engine fails",
            effect="Vehicle cannot operate",
            cause="Battery dead",
            target_completion_date="2024-03-15"
        )
        assert record.target_completion_date == "2024-03-15"
    
    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from string fields"""
        record = FMEARecord(
            failure_mode="  Engine fails to start  ",
            effect="  Vehicle cannot operate  ",
            cause="  Battery dead  "
        )
        assert record.failure_mode == "Engine fails to start"
        assert record.effect == "Vehicle cannot operate"
        assert record.cause == "Battery dead"
    
    def test_none_values_for_optional_fields(self):
        """Test that None values are allowed for optional fields"""
        record = FMEARecord(
            failure_mode="Engine fails",
            effect="Vehicle cannot operate",
            cause="Battery dead",
            severity=None,
            component=None,
            existing_controls=None
        )
        assert record.severity is None
        assert record.component is None
        assert record.existing_controls is None


class TestValidateFMEARecord:
    """Test the validate_fmea_record helper function"""
    
    def test_valid_record_validation(self):
        """Test validation of a valid record"""
        record_dict = {
            "failure_mode": "Engine fails to start",
            "effect": "Vehicle cannot operate",
            "cause": "Battery dead",
            "severity": 8
        }
        is_valid, error_msg, validated_record = validate_fmea_record(record_dict)
        assert is_valid is True
        assert error_msg is None
        assert validated_record is not None
    
    def test_invalid_record_validation(self):
        """Test validation of an invalid record"""
        record_dict = {
            "failure_mode": "fail",  # Too short
            "effect": "Vehicle cannot operate",
            "cause": "Battery dead"
        }
        is_valid, error_msg, validated_record = validate_fmea_record(record_dict)
        assert is_valid is False
        assert error_msg is not None
        assert validated_record is None


class TestValidateCSVHeaders:
    """Test CSV header validation"""
    
    def test_valid_headers_with_all_columns(self):
        """Test validation of CSV with all columns"""
        columns = ['failure_mode', 'effect', 'cause', 'component', 'severity']
        result = validate_csv_headers(columns)
        assert result.success is True
        assert len(result.missing_columns) == 0
    
    def test_valid_headers_with_required_only(self):
        """Test validation with only required columns"""
        columns = ['failure_mode', 'effect', 'cause']
        result = validate_csv_headers(columns)
        assert result.success is True
        assert len(result.missing_columns) == 0
    
    def test_missing_required_columns(self):
        """Test validation with missing required columns"""
        columns = ['failure_mode', 'component', 'status']  # Missing 'effect', 'cause'
        result = validate_csv_headers(columns)
        assert result.success is False
        assert 'effect' in result.missing_columns
        assert 'cause' in result.missing_columns
    
    def test_case_insensitive_column_matching(self):
        """Test that column matching is case-insensitive"""
        columns = ['Failure_Mode', 'Effect', 'Cause']  # Different cases
        result = validate_csv_headers(columns)
        assert result.success is True
    
    def test_extra_columns_detection(self):
        """Test detection of extra columns not in standard template"""
        columns = ['failure_mode', 'effect', 'cause', 'custom_field', 'extra_data']
        result = validate_csv_headers(columns)
        assert result.success is True  # Still valid if required columns present
        assert len(result.extra_columns) > 0


class TestUnstructuredTextInput:
    """Test UnstructuredTextInput validation"""
    
    def test_valid_unstructured_input(self):
        """Test valid unstructured text input"""
        input_data = UnstructuredTextInput(
            source_type="customer_review",
            texts=[
                "Engine failed after 6 months of use",
                "Brake system malfunction detected"
            ],
            total_entries=2,
            average_length=35.0
        )
        assert input_data.source_type == "customer_review"
        assert len(input_data.texts) == 2
    
    def test_invalid_source_type(self):
        """Test that invalid source types are rejected"""
        with pytest.raises(Exception):
            UnstructuredTextInput(
                source_type="unknown_source",  # Invalid
                texts=["Sample text"],
                total_entries=1,
                average_length=11.0
            )
    
    def test_text_too_short(self):
        """Test that texts below minimum length are rejected"""
        with pytest.raises(Exception):
            UnstructuredTextInput(
                source_type="review",
                texts=["Bad"],  # Less than 5 characters
                total_entries=1,
                average_length=3.0
            )
    
    def test_empty_text_list(self):
        """Test that empty text list is rejected"""
        with pytest.raises(Exception):
            UnstructuredTextInput(
                source_type="review",
                texts=[],  # Empty
                total_entries=0,
                average_length=0
            )


class TestValidationResult:
    """Test ValidationResult model"""
    
    def test_valid_validation_result(self):
        """Test creating a valid validation result"""
        result = ValidationResult(
            is_valid=True,
            total_records=100,
            valid_records=98,
            invalid_records=2,
            errors=[],
            warnings=["Some minor issues"],
            success_rate=98.0
        )
        assert result.is_valid is True
        assert result.success_rate == 98.0
    
    def test_validation_result_with_errors(self):
        """Test validation result with errors"""
        error = ValidationError(
            error_code="MISSING_FIELD",
            message="Missing required field",
            field="failure_mode",
            row_number=3
        )
        result = ValidationResult(
            is_valid=False,
            total_records=10,
            valid_records=8,
            invalid_records=2,
            errors=[error],
            success_rate=80.0
        )
        assert len(result.errors) == 1
        assert result.errors[0].field == "failure_mode"


class TestUserFriendlyErrors:
    """Test user-friendly error message generation"""
    
    def test_missing_required_field_error(self):
        """Test error message for missing required field"""
        msg = get_user_friendly_error(
            "MISSING_REQUIRED_FIELD",
            {"field": "failure_mode"}
        )
        assert "failure_mode" in msg.lower()
        assert "required" in msg.lower()
    
    def test_invalid_format_error(self):
        """Test error message for invalid format"""
        msg = get_user_friendly_error(
            "INVALID_FORMAT",
            {"field": "severity", "expected": "integer 1-10"}
        )
        assert "severity" in msg.lower()
        assert "format" in msg.lower()
    
    def test_unsupported_format_error(self):
        """Test error message for unsupported file format"""
        msg = get_user_friendly_error(
            "UNSUPPORTED_FORMAT",
            {"format": ".txt"}
        )
        assert ".txt" in msg
        assert "csv" in msg.lower() or "excel" in msg.lower()
    
    def test_invalid_date_format_error(self):
        """Test error message for invalid date format"""
        msg = get_user_friendly_error(
            "INVALID_DATE_FORMAT",
            {"field": "target_completion_date", "value": "15/03/2024"}
        )
        assert "date" in msg.lower()
        assert "yyyy-mm-dd" in msg.lower()
    
    def test_empty_file_error(self):
        """Test error message for empty file"""
        msg = get_user_friendly_error("EMPTY_FILE")
        assert "empty" in msg.lower()


class TestValidationIntegration:
    """Integration tests for validation with real data"""
    
    def test_validate_csv_content(self):
        """Test validation of actual CSV content"""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("failure_mode,effect,cause,severity\n")
            f.write("\"Engine fails\",\"Cannot operate\",\"Battery dead\",8\n")
            f.write("\"Brake leak\",\"Safety risk\",\"Corroded lines\",9\n")
            temp_file = f.name
        
        try:
            df = pd.read_csv(temp_file)
            result = validate_csv_headers(df.columns.tolist())
            assert result.success is True
        finally:
            Path(temp_file).unlink()
    
    def test_validate_json_records(self):
        """Test validation of JSON records"""
        records = [
            {
                "failure_mode": "Engine fails to start",
                "effect": "Vehicle cannot operate",
                "cause": "Battery dead",
                "severity": 8
            },
            {
                "failure_mode": "Brake fluid leak",
                "effect": "Loss of braking power",
                "cause": "Corroded brake line",
                "severity": 9
            }
        ]
        
        valid_count = 0
        for record in records:
            is_valid, _, _ = validate_fmea_record(record)
            if is_valid:
                valid_count += 1
        
        assert valid_count == 2


# Pytest fixtures
@pytest.fixture
def sample_fmea_record():
    """Fixture providing a sample FMEA record"""
    return {
        "failure_mode": "Engine fails to start",
        "effect": "Vehicle cannot operate",
        "cause": "Battery dead or starter malfunction",
        "component": "Engine Starter System",
        "severity": 8,
        "occurrence": 3,
        "detection": 9
    }


@pytest.fixture
def sample_csv_headers():
    """Fixture providing sample CSV headers"""
    return ['failure_mode', 'effect', 'cause', 'component', 'severity', 'occurrence', 'detection']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
