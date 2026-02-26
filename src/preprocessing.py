"""
Data Preprocessing Module for FMEA Generator
Handles both structured (CSV/Excel) and unstructured (text) inputs
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional
import re
from pathlib import Path
import logging
from tqdm import tqdm

# Text processing libraries
from textblob import TextBlob
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

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
    
    def load_structured_data(self, file_path: str) -> pd.DataFrame:
        """
        Load and validate structured data from CSV or Excel
        
        Args:
            file_path: Path to the CSV or Excel file
            
        Returns:
            Validated DataFrame
        """
        logger.info(f"Loading structured data from: {file_path}")
        
        file_path = Path(file_path)
        
        # Load based on file extension
        if file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        elif file_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Validate and normalize
        df = self._validate_structured_data(df)
        df = self._normalize_structured_data(df)
        
        logger.info(f"Loaded {len(df)} records from structured file")
        return df
    
    def _validate_structured_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate that required columns exist in structured data
        
        Args:
            df: Input DataFrame
            
        Returns:
            Validated DataFrame
        """
        required_cols = self.config.get('input_validation', {}).get(
            'required_structured_columns', ['failure_mode', 'effect', 'cause']
        )
        
        # Normalize column names (lowercase, strip spaces)
        df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_').str.replace('maintenance_strategy', 'existing_controls')
        
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
            df: Input DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Fill missing values
        text_columns = ['failure_mode', 'effect', 'cause', 'component', 
                       'process', 'existing_controls']
        
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna("Not specified")
                df[col] = df[col].astype(str).str.strip()
        
        # Normalize severity, occurrence, detection if present
        numeric_columns = ['severity', 'occurrence', 'detection']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(self.config['risk_scoring'][col.split('_')[0]]['default'])
                df[col] = df[col].clip(1, 10)  # Ensure values are between 1-10
        
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
        """
        logger.info("Loading unstructured data...")
        
        if file_path:
            df = self._load_text_from_file(file_path)
        elif text_data:
            df = pd.DataFrame({'text': text_data})
        else:
            raise ValueError("Either file_path or text_data must be provided")
        
        # Preprocess and filter
        df = self._preprocess_text(df)
        df = self._filter_negative_reviews(df)
        
        logger.info(f"Loaded and filtered {len(df)} text entries")
        return df
    
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
                        data_type: str = 'auto') -> pd.DataFrame:
        """
        Unified preprocessing for any input type
        
        Args:
            input_data: File path, list of texts, or DataFrame
            data_type: 'structured', 'unstructured', or 'auto'
            
        Returns:
            Preprocessed DataFrame
        """
        logger.info(f"Starting batch preprocessing with data_type={data_type}")
        
        # Auto-detect data type
        if data_type == 'auto':
            if isinstance(input_data, pd.DataFrame):
                data_type = 'structured' if 'failure_mode' in input_data.columns else 'unstructured'
            elif isinstance(input_data, str):
                # Check file extension or content
                if any(col in pd.read_csv(input_data, nrows=1).columns.str.lower() 
                      for col in ['failure_mode', 'effect', 'cause']):
                    data_type = 'structured'
                else:
                    data_type = 'unstructured'
            else:
                data_type = 'unstructured'
        
        # Process based on type
        if data_type == 'structured':
            if isinstance(input_data, str):
                return self.load_structured_data(input_data)
            else:
                return self._normalize_structured_data(input_data)
        else:  # unstructured
            if isinstance(input_data, str):
                return self.load_unstructured_data(file_path=input_data)
            else:
                return self.load_unstructured_data(text_data=input_data)


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
