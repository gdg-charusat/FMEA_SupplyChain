"""
Data Preprocessing Module for FMEA Generator
Handles both structured (CSV/Excel) and unstructured (text) inputs with validation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Tuple
import re
from pathlib import Path
import logging
from tqdm import tqdm
from pydantic import ValidationError as PydanticValidationError

# Text processing libraries
from textblob import TextBlob
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

# Import validators
from validators import (
    FMEARecord, 
    ValidationResult, 
    ValidationError as ValidatorError,
    validate_fmea_record,
    validate_csv_headers,
    get_user_friendly_error
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """
    Preprocesses both structured and unstructured data for FMEA generation
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the preprocessor with configuration
        
        Args:
            config: Configuration dictionary containing preprocessing parameters
        """
        self.config = config
        self._initialize_nltk()
        self.stop_words = set(stopwords.words('english'))
        
    def _initialize_nltk(self):
        """Download required NLTK data"""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading required NLTK data...")
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
    
    def load_structured_data(self, file_path: str) -> Tuple[pd.DataFrame, ValidationResult]:
        """
        Load and validate structured data from CSV or Excel
        
        Args:
            file_path: Path to the CSV or Excel file
            
        Returns:
            Tuple of (validated DataFrame, ValidationResult with details)
            
        Raises:
            ValueError: If file format is unsupported or validation fails
        """
        logger.info(f"Loading structured data from: {file_path}")
        
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            error_msg = get_user_friendly_error(
                "MISSING_FILE",
                {"file_path": str(file_path)}
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Load based on file extension
        try:
            if file_path.suffix.lower() == '.csv':
                logger.info("Loading CSV file...")
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                logger.info("Loading Excel file...")
                df = pd.read_excel(file_path)
            elif file_path.suffix.lower() == '.json':
                logger.info("Loading JSON file...")
                df = pd.read_json(file_path)
            else:
                error_msg = get_user_friendly_error(
                    "UNSUPPORTED_FORMAT",
                    {"format": file_path.suffix}
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            if "No columns to parse from file" in str(e) or len(df) == 0:
                error_msg = get_user_friendly_error("EMPTY_FILE")
                logger.error(error_msg)
                raise ValueError(error_msg)
            raise
        
        # Check for empty file
        if len(df) == 0:
            error_msg = get_user_friendly_error("EMPTY_FILE")
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate headers
        logger.info(f"Validating headers...")
        header_validation = validate_csv_headers(df.columns.tolist())
        if header_validation.suggestions:
            for suggestion in header_validation.suggestions:
                logger.warning(f"📋 {suggestion}")
        
        if not header_validation.success:
            error_msg = get_user_friendly_error(
                "MISSING_REQUIRED_FIELD",
                {"field": ", ".join(header_validation.missing_columns)}
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validate and normalize data
        logger.info(f"Validating {len(df)} records...")
        validated_df, validation_result = self._validate_and_normalize_structured_data(df)
        
        # Check validation results
        if not validation_result.is_valid and validation_result.valid_records == 0:
            error_summary = get_user_friendly_error("ZERO_VALID_RECORDS")
            logger.error(error_summary)
            # Print detailed errors
            for error in validation_result.errors[:5]:  # Show first 5 errors
                logger.error(f"  Row {error.row_number}: {error.message}")
            raise ValueError(f"{error_summary}. See logs for details.")
        
        logger.info(
            f"✅ Loaded and validated {validation_result.valid_records}/{validation_result.total_records} "
            f"records ({validation_result.success_rate:.1f}% success rate)"
        )
        
        if validation_result.warnings:
            for warning in validation_result.warnings[:10]:
                logger.warning(f"⚠️ {warning}")
        
        return validated_df, validation_result
    
    def _validate_and_normalize_structured_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, ValidationResult]:
        """
        Validate each record using Pydantic schemas and normalize data
        
        Args:
            df: Input DataFrame
            
        Returns:
            Tuple of (normalized DataFrame, ValidationResult)
        """
        # Normalize column names
        df.columns = (df.columns
                      .str.lower()
                      .str.strip()
                      .str.replace(' ', '_')
                      .str.replace('-', '_')
                      .str.replace('maintenance_strategy', 'existing_controls'))
        
        valid_records = []
        errors = []
        warnings = []
        
        # Validate each row
        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 because 1-indexed and includes header
            row_dict = row.to_dict()
            
            # Convert NaN and None to empty string for validation
            row_dict = {k: (v if pd.notna(v) else None) for k, v in row_dict.items()}
            
            # Try to validate using Pydantic
            is_valid, error_msg, validated_record = validate_fmea_record(row_dict)
            
            if is_valid:
                valid_records.append(validated_record)
            else:
                # Parse error message to extract field name
                error_obj = ValidatorError(
                    error_code="VALIDATION_ERROR",
                    message=error_msg,
                    row_number=row_num,
                    field=self._extract_field_from_error(error_msg),
                    suggested_fix=self._generate_fix_suggestion(error_msg)
                )
                errors.append(error_obj)
                logger.warning(f"Row {row_num}: {error_msg}")
        
        # Convert valid records to DataFrame
        if valid_records:
            validated_df = pd.DataFrame([
                {
                    'failure_mode': r.failure_mode,
                    'effect': r.effect,
                    'cause': r.cause,
                    'component': r.component or "Not specified",
                    'process': r.process or "Not specified",
                    'function': r.function or "Not specified",
                    'severity': r.severity or 5,
                    'occurrence': r.occurrence or 5,
                    'detection': r.detection or 5,
                    'existing_controls': r.existing_controls or "Not specified",
                    'recommended_action': r.recommended_action or "Not specified",
                    'responsibility': r.responsibility or "Not assigned",
                    'target_completion_date': r.target_completion_date,
                    'additional_notes': r.additional_notes or "",
                    'source': r.source or "other"
                }
                for r in valid_records
            ])
        else:
            validated_df = pd.DataFrame()
        
        # Create validation result
        total = len(df)
        valid = len(valid_records)
        invalid = total - valid
        
        validation_result = ValidationResult(
            is_valid=invalid == 0,
            total_records=total,
            valid_records=valid,
            invalid_records=invalid,
            errors=errors,
            warnings=warnings,
            success_rate=(valid / total * 100) if total > 0 else 0
        )
        
        return validated_df, validation_result
    
    def _extract_field_from_error(self, error_msg: str) -> Optional[str]:
        """Extract field name from validation error message"""
        import re
        # Try to find "field_name" in error message
        match = re.search(r"'(\w+)'", error_msg)
        return match.group(1) if match else None
    
    def _generate_fix_suggestion(self, error_msg: str) -> Optional[str]:
        """Generate a fix suggestion based on error message"""
        if "too short" in error_msg.lower():
            return "Ensure field contains at least 5 characters"
        elif "too long" in error_msg.lower():
            return "Reduce field length to meet requirements"
        elif "integer" in error_msg.lower():
            return "Ensure numeric fields (severity, occurrence, detection) are integers 1-10"
        elif "date" in error_msg.lower():
            return "Use YYYY-MM-DD format for dates (e.g., 2024-02-24)"
        elif "required" in error_msg.lower():
            return "Ensure this required field is not empty"
        return "Check field format and try again"
    
    def _validate_structured_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Legacy method - now wrapped by load_structured_data
        
        Args:
            df: Input DataFrame
            
        Returns:
            Validated DataFrame
        """
        required_cols = self.config.get('input_validation', {}).get(
            'required_structured_columns', ['failure_mode', 'effect', 'cause']
        )
        
        # Normalize column names (lowercase, strip spaces)
        df.columns = (df.columns
                      .str.lower()
                      .str.strip()
                      .str.replace(' ', '_')
                      .str.replace('maintenance_strategy', 'existing_controls'))
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.warning(f"Missing columns: {missing_cols}. Adding empty columns.")
            for col in missing_cols:
                df[col] = "Not specified"
        
        return df
    
    
    def _normalize_structured_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize and clean structured data
        
        Args:
            df: Input DataFrame (already validated)
            
        Returns:
            Cleaned DataFrame
        """
        if len(df) == 0:
            return df
        
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Fill missing values
        text_columns = ['failure_mode', 'effect', 'cause', 'component', 
                       'process', 'existing_controls', 'recommended_action']
        
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna("Not specified")
                df[col] = df[col].astype(str).str.strip()
        
        # Normalize severity, occurrence, detection if present
        numeric_columns = ['severity', 'occurrence', 'detection']
        for col in numeric_columns:
            if col in df.columns:
                # Try to get default from config, otherwise use 5
                try:
                    default_val = self.config['risk_scoring'].get(col.split('_')[0], {}).get('default', 5)
                except:
                    default_val = 5
                
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(default_val)
                df[col] = df[col].clip(1, 10)  # Ensure values are between 1-10
                df[col] = df[col].astype(int)
        
        logger.info("Structured data normalized successfully")
        return df
    
    
    def load_unstructured_data(self, file_path: Optional[str] = None, 
                               text_data: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load and preprocess unstructured text data (reviews, reports, etc.)
        
        Args:
            file_path: Path to file containing text data (CSV with reviews)
            text_data: List of text strings (alternative to file_path)
            
        Returns:
            DataFrame with preprocessed text
            
        Raises:
            ValueError: If no input is provided or file doesn't exist
        """
        logger.info("Loading unstructured data...")
        
        try:
            if file_path:
                if not Path(file_path).exists():
                    error_msg = get_user_friendly_error(
                        "MISSING_FILE",
                        {"file_path": file_path}
                    )
                    raise FileNotFoundError(error_msg)
                df = self._load_text_from_file(file_path)
            elif text_data:
                # Validate text data
                if not text_data or len(text_data) == 0:
                    error_msg = get_user_friendly_error("EMPTY_FILE")
                    raise ValueError(error_msg)
                df = pd.DataFrame({'text': text_data})
            else:
                error_msg = "Either file_path or text_data must be provided"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            if not isinstance(e, (FileNotFoundError, ValueError)):
                error_msg = get_user_friendly_error(
                    "UNSUPPORTED_FORMAT",
                    {"format": Path(file_path).suffix if file_path else "unknown"}
                )
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            raise
        
        # Preprocess and filter
        try:
            df = self._preprocess_text(df)
            if len(df) > 0:
                df = self._filter_negative_reviews(df)
            
            if len(df) == 0:
                logger.warning("⚠️ No valid text entries after preprocessing")
            else:
                logger.info(f"✅ Loaded and preprocessed {len(df)} text entries")
            
            return df
        except Exception as e:
            logger.error(f"❌ Error during text preprocessing: {str(e)}")
            raise
    
    def _load_text_from_file(self, file_path: str) -> pd.DataFrame:
        """
        Load text data from file (CSV with review column)
        
        Args:
            file_path: Path to the file
            
        Returns:
            DataFrame with text column
        """
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.csv':
            # Try multiple encoding and error handling strategies
            try:
                logger.info("Loading CSV file...")
                df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip', low_memory=False)
            except:
                try:
                    logger.info("Retrying with latin-1 encoding...")
                    df = pd.read_csv(file_path, encoding='latin-1', on_bad_lines='skip', low_memory=False)
                except:
                    logger.info("Retrying with iso-8859-1 encoding...")
                    df = pd.read_csv(file_path, encoding='iso-8859-1', on_bad_lines='skip', engine='python')
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            # Assume plain text file
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            df = pd.DataFrame({'text': lines})
        
        # Try to identify the text column
        text_columns = ['Review', 'review', 'text', 'comment', 'description', 'feedback']
        
        for col in text_columns:
            if col in df.columns:
                df = df.rename(columns={col: 'text'})
                break
        
        if 'text' not in df.columns:
            # If no recognized column, take the first text column
            text_col = df.select_dtypes(include=['object']).columns[0]
            df = df.rename(columns={text_col: 'text'})
        
        return df[['text']].copy()
    
    def _preprocess_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and preprocess text data
        
        Args:
            df: DataFrame with 'text' column
            
        Returns:
            DataFrame with cleaned text
        """
        logger.info("Preprocessing text data...")
        
        # Remove null values
        df = df.dropna(subset=['text'])
        df['text'] = df['text'].astype(str)
        
        # Remove very short texts
        min_length = self.config.get('text_processing', {}).get('min_review_length', 10)
        df = df[df['text'].str.len() >= min_length]
        
        # Clean text 
        tqdm.pandas(desc="Cleaning text")
        df['text_cleaned'] = df['text'].progress_apply(self._clean_text)
        
        # Calculate sentiment 
        tqdm.pandas(desc="Analyzing sentiment")
        df['sentiment'] = df['text_cleaned'].progress_apply(self._get_sentiment)
        
        return df
    
    def _clean_text(self, text: str) -> str:
        """
        Clean individual text entry
        
        Args:
            text: Input text string
            
        Returns:
            Cleaned text
        """
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but keep punctuation for sentence structure
        text = re.sub(r'[^a-z0-9\s.,!?;:\'-]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _get_sentiment(self, text: str) -> float:
        """
        Calculate sentiment polarity of text using TextBlob
        
        Args:
            text: Input text
            
        Returns:
            Polarity score (-1 to 1)
        """
        try:
            return TextBlob(text).sentiment.polarity
        except:
            return 0.0
    
    def _filter_negative_reviews(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to prioritize negative reviews (likely to contain failure info)
        
        Args:
            df: DataFrame with sentiment scores
            
        Returns:
            Filtered DataFrame
        """
        if not self.config.get('text_processing', {}).get('enable_sentiment_filter', True):
            return df
        
        threshold = self.config.get('text_processing', {}).get('negative_threshold', 0.3)
        
        initial_count = len(df)
        df_negative = df[df['sentiment'] < threshold].copy()
        
        logger.info(f"Filtered {initial_count} texts to {len(df_negative)} negative/critical ones")
        
        return df_negative if len(df_negative) > 0 else df
    
    def extract_sentences_with_keywords(self, text: str, 
                                       keywords: List[str] = None) -> List[str]:
        """
        Extract sentences containing failure-related keywords
        
        Args:
            text: Input text
            keywords: List of failure-related keywords
            
        Returns:
            List of relevant sentences
        """
        if keywords is None:
            # Default failure-related keywords
            keywords = [
                'fail', 'problem', 'issue', 'defect', 'broken', 'malfunction',
                'error', 'fault', 'damage', 'not work', 'stopped', 'crash',
                'leak', 'overheat', 'noise', 'vibration', 'wear'
            ]
        
        sentences = sent_tokenize(text)
        relevant_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in keywords):
                relevant_sentences.append(sentence)
        
        return relevant_sentences
    
    def batch_preprocess(self, input_data: Union[str, List[str], pd.DataFrame],
                        data_type: str = 'auto', return_validation_result: bool = False) -> Union[pd.DataFrame, Tuple]:
        """
        Unified preprocessing for any input type
        
        Args:
            input_data: File path, list of texts, or DataFrame
            data_type: 'structured', 'unstructured', or 'auto'
            return_validation_result: If True, returns tuple with ValidationResult
            
        Returns:
            Preprocessed DataFrame or tuple of (DataFrame, ValidationResult) if return_validation_result=True
        """
        logger.info(f"Starting batch preprocessing with data_type={data_type}")
        
        # Auto-detect data type
        if data_type == 'auto':
            if isinstance(input_data, pd.DataFrame):
                data_type = 'structured' if 'failure_mode' in input_data.columns else 'unstructured'
            elif isinstance(input_data, str):
                try:
                    # Check file extension or content
                    if input_data.lower().endswith('.json'):
                        data_type = 'structured'
                    else:
                        test_df = pd.read_csv(input_data, nrows=1)
                        if any(col in test_df.columns.str.lower() 
                              for col in ['failure_mode', 'effect', 'cause']):
                            data_type = 'structured'
                        else:
                            data_type = 'unstructured'
                except:
                    data_type = 'unstructured'
            else:
                data_type = 'unstructured'
        
        logger.info(f"Detected data type: {data_type}")
        
        # Process based on type
        validation_result = None
        try:
            if data_type == 'structured':
                if isinstance(input_data, str):
                    result = self.load_structured_data(input_data)
                    if isinstance(result, tuple):
                        processed_df, validation_result = result
                    else:
                        processed_df = result
                else:
                    processed_df, validation_result = self._validate_and_normalize_structured_data(input_data)
            else:  # unstructured
                if isinstance(input_data, str):
                    processed_df = self.load_unstructured_data(file_path=input_data)
                else:
                    processed_df = self.load_unstructured_data(text_data=input_data)
                # Create a default validation result for unstructured
                validation_result = ValidationResult(
                    is_valid=len(processed_df) > 0,
                    total_records=len(processed_df),
                    valid_records=len(processed_df),
                    invalid_records=0,
                    errors=[],
                    warnings=[],
                    success_rate=100.0 if len(processed_df) > 0 else 0
                )
        except Exception as e:
            logger.error(f"❌ Error during batch preprocessing: {str(e)}")
            raise
        
        if return_validation_result:
            return processed_df, validation_result
        return processed_df

if __name__ == "__main__":
    # Example usage
    import yaml
    
    with open('../config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    preprocessor = DataPreprocessor(config)
    
    # Test with sample data
    sample_texts = [
        "The engine started making loud noises and eventually failed completely.",
        "Brake system malfunction caused dangerous situation on highway.",
        "Paint quality is excellent, very satisfied with the finish."
    ]
    
    df = preprocessor.load_unstructured_data(text_data=sample_texts)
    print("\nPreprocessed Data:")
    print(df)
