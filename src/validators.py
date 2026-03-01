"""
Input Validation Module for FMEA Generator
Provides Pydantic models and validation logic for CSV/JSON imports
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SeverityLevel(str, Enum):
    """Severity classification levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OccurrenceLevel(str, Enum):
    """Occurrence probability levels"""
    VERY_LIKELY = "very_likely"
    LIKELY = "likely"
    OCCASIONAL = "occasional"
    RARE = "rare"


class DetectionLevel(str, Enum):
    """Detection difficulty levels"""
    NOT_DETECTABLE = "not_detectable"
    REMOTE = "remote"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ActionPriority(str, Enum):
    """Action priority classification"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FMEARecord(BaseModel):
    """
    Single FMEA record validation schema
    Represents one failure mode entry with all required and optional fields
    """
    
    # Required fields
    failure_mode: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Description of the failure mode (how the component/process could fail)"
    )
    
    effect: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="The effect or consequence of the failure on the end user"
    )
    
    cause: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Root cause(s) of the failure mode"
    )
    
    # Optional identification fields
    component: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Component, subsystem, or assembly affected"
    )
    
    process: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Process or operation where failure occurs"
    )
    
    function: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Function or purpose of the component/process"
    )
    
    # Risk scoring fields
    severity: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Severity score (1-10): Impact of failure on customer"
    )
    
    occurrence: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Occurrence score (1-10): Likelihood of failure occurring"
    )
    
    detection: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Detection score (1-10): Ability to detect failure before impact"
    )
    
    # Controls and actions
    existing_controls: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Current preventive and detective controls"
    )
    
    recommended_action: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Recommended action to eliminate or reduce failure risk"
    )
    
    responsibility: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Person/department responsible for implementation"
    )
    
    target_completion_date: Optional[str] = Field(
        default=None,
        description="Target date for completing recommended action (YYYY-MM-DD)"
    )
    
    # Additional fields
    additional_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Additional context or remarks"
    )
    
    source: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Source of the failure information (review, complaint, etc.)"
    )
    
    @field_validator('severity', 'occurrence', 'detection', mode='before')
    @classmethod
    def validate_numeric_fields(cls, v):
        """Convert string numbers to integers"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return int(v.strip())
            except ValueError:
                raise ValueError(f"Must be a valid integer between 1-10")
        return v
    
    @field_validator('target_completion_date', mode='before')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format YYYY-MM-DD"""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            from datetime import datetime
            try:
                datetime.strptime(v.strip(), '%Y-%m-%d')
                return v.strip()
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v
    
    @field_validator('failure_mode', 'effect', 'cause', 'component', 'process', mode='before')
    @classmethod
    def strip_whitespace(cls, v):
        """Strip whitespace from string fields"""
        if isinstance(v, str):
            return v.strip()
        return v
    
    @model_validator(mode='after')
    def validate_record_completeness(self):
        """Ensure record has sufficient data for FMEA analysis"""
        # At least one of component or process should be specified
        if not self.component and not self.process:
            logger.warning(
                "Record lacks both component and process information. "
                "Consider specifying at least one for better analysis."
            )
        
        return self
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "examples": [
                {
                    "failure_mode": "Engine does not start",
                    "effect": "Vehicle cannot be operated, customer unable to use car",
                    "cause": "Battery failure or starter motor malfunction",
                    "component": "Engine Starter System",
                    "severity": 8,
                    "occurrence": 3,
                    "detection": 9
                }
            ]
        }


class StructuredCSVInput(BaseModel):
    """
    Validates structured CSV input with basic schema expectations
    """
    
    file_path: str = Field(..., description="Path to CSV file")
    
    rows: List[FMEARecord] = Field(
        ...,
        min_items=1,
        description="List of validated FMEA records from CSV"
    )
    
    total_records: int = Field(..., description="Total number of records processed")
    valid_records: int = Field(..., description="Number of successfully validated records")
    invalid_records: int = Field(..., description="Number of invalid records")
    
    class Config:
        """Pydantic configuration"""
        arbitrary_types_allowed = True


class UnstructuredTextInput(BaseModel):
    """
    Validates unstructured text input
    """
    
    source_type: str = Field(
        ...,
        description="Type of source (review, complaint, incident_report, etc.)"
    )
    
    texts: List[str] = Field(
        ...,
        min_items=1,
        description="List of text entries for analysis"
    )
    
    total_entries: int = Field(..., description="Total number of text entries")
    average_length: float = Field(..., description="Average text length in characters")
    
    @field_validator('texts')
    @classmethod
    def validate_text_entries(cls, v):
        """Validate that all texts meet minimum requirements"""
        for text in v:
            if not isinstance(text, str):
                raise ValueError("All text entries must be strings")
            if len(text.strip()) < 5:
                raise ValueError(
                    f"Text entries must be at least 5 characters. Got: '{text}'"
                )
        return v
    
    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v):
        """Validate source type"""
        valid_types = [
            'review', 'complaint', 'incident_report', 'customer_feedback',
            'qa_report', 'warranty_claim', 'field_report', 'test_report', 'other'
        ]
        if v.lower() not in valid_types:
            raise ValueError(
                f"source_type must be one of: {', '.join(valid_types)}"
            )
        return v.lower()


class ValidationError(BaseModel):
    """
    Structured validation error response
    """
    
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(default=None, description="Field that failed validation")
    row_number: Optional[int] = Field(default=None, description="Row number in file (if applicable)")
    suggested_fix: Optional[str] = Field(default=None, description="Suggestion to fix the error")
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "examples": [
                {
                    "error_code": "MISSING_REQUIRED_FIELD",
                    "message": "Missing required field 'failure_mode'",
                    "field": "failure_mode",
                    "row_number": 3,
                    "suggested_fix": "Ensure 'failure_mode' column is present with non-empty values"
                }
            ]
        }


class ValidationResult(BaseModel):
    """
    Complete validation result response
    """
    
    is_valid: bool = Field(..., description="Whether input is valid")
    total_records: int = Field(..., description="Total records processed")
    valid_records: int = Field(..., description="Valid records count")
    invalid_records: int = Field(..., description="Invalid records count")
    errors: List[ValidationError] = Field(
        default=[],
        description="List of validation errors"
    )
    warnings: List[str] = Field(
        default=[],
        description="List of non-critical warnings"
    )
    success_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of valid records"
    )
    
    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "examples": [
                {
                    "is_valid": True,
                    "total_records": 100,
                    "valid_records": 98,
                    "invalid_records": 2,
                    "errors": [],
                    "warnings": ["Record 5 lacks component information"],
                    "success_rate": 98.0
                }
            ]
        }


class CSVTemplate(BaseModel):
    """
    CSV template specification
    """
    
    success: bool = Field(..., description="Whether template matches expected structure")
    missing_columns: List[str] = Field(
        default=[],
        description="Critical columns that are missing"
    )
    extra_columns: List[str] = Field(
        default=[],
        description="Extra columns not in standard template"
    )
    suggestions: List[str] = Field(
        default=[],
        description="Suggestions for improving the CSV structure"
    )


# Validation helper functions

def validate_fmea_record(record: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[FMEARecord]]:
    """
    Validate a single FMEA record
    
    Args:
        record: Dictionary containing record data
    
    Returns:
        Tuple of (is_valid, error_message, validated_record)
    """
    try:
        fmea_record = FMEARecord(**record)
        return True, None, fmea_record
    except Exception as e:
        return False, str(e), None


def validate_csv_headers(df_columns: List[str]) -> CSVTemplate:
    """
    Validate CSV headers match expected structure
    
    Args:
        df_columns: List of column names from DataFrame
    
    Returns:
        CSVTemplate with validation results
    """
    required_columns = {'failure_mode', 'effect', 'cause'}
    optional_columns = {
        'component', 'process', 'function', 'severity', 'occurrence',
        'detection', 'existing_controls', 'recommended_action', 'responsibility',
        'target_completion_date', 'additional_notes', 'source'
    }
    
    normalized_columns = set(col.lower().replace(' ', '_').replace('-', '_') for col in df_columns)
    
    missing_columns = list(required_columns - normalized_columns)
    extra_columns = list(normalized_columns - required_columns - optional_columns)
    
    suggestions = []
    if missing_columns:
        suggestions.append(f"Add required columns: {', '.join(missing_columns)}")
    if extra_columns:
        suggestions.append(f"Extra columns found (will be ignored): {', '.join(extra_columns)}")
    
    return CSVTemplate(
        success=len(missing_columns) == 0,
        missing_columns=missing_columns,
        extra_columns=extra_columns,
        suggestions=suggestions
    )


def get_user_friendly_error(error_code: str, details: Dict[str, Any] = None) -> str:
    """
    Convert validation error code to user-friendly message
    
    Args:
        error_code: Error code identifier
        details: Additional error details
    
    Returns:
        User-friendly error message
    """
    error_messages = {
        "MISSING_REQUIRED_FIELD": (
            "Missing required field: {field}\n"
            "📋 Required fields are: failure_mode, effect, cause"
        ),
        "INVALID_FORMAT": (
            "Invalid format detected: {field}\n"
            "💡 Expected format: {expected}"
        ),
        "INVALID_NUMERIC_RANGE": (
            "Invalid {field} value: {value}\n"
            "📊 Must be between 1-10 for risk scoring fields"
        ),
        "INVALID_DATE_FORMAT": (
            "Invalid date format in {field}: {value}\n"
            "📅 Expected format: YYYY-MM-DD (e.g., 2024-02-24)"
        ),
        "TEXT_TOO_SHORT": (
            "Field '{field}' is too short\n"
            "✏️ Minimum 5 characters required"
        ),
        "TEXT_TOO_LONG": (
            "Field '{field}' exceeds maximum length\n"
            "✏️ Maximum {max_length} characters allowed"
        ),
        "MISSING_FILE": (
            "File not found: {file_path}\n"
            "📁 Please check the file path and try again"
        ),
        "UNSUPPORTED_FORMAT": (
            "Unsupported file format: {format}\n"
            "✅ Supported formats: CSV (.csv), Excel (.xlsx, .xls), JSON (.json)"
        ),
        "EMPTY_FILE": (
            "Input file is empty\n"
            "📊 File must contain at least 1 data record"
        ),
        "ZERO_VALID_RECORDS": (
            "No valid records found in input\n"
            "🔍 Check that all required fields are present and correctly formatted"
        ),
    }
    
    if error_code not in error_messages:
        return f"Validation error: {error_code}"
    
    message = error_messages[error_code]
    if details:
        try:
            message = message.format(**details)
        except KeyError:
            pass
    
    return message
