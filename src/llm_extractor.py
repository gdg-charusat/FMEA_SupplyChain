"""
LLM-Based Information Extraction Module
Uses transformer models to extract FMEA-relevant information from text
"""

import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    pipeline,
    BitsAndBytesConfig
)
from typing import Dict, List, Optional, Union
import json
import re
import logging
from pathlib import Path
from tqdm import tqdm

logger = logging.getLogger(__name__)


class LLMExtractor:
    """
    Uses LLM to extract failure mode, effect, cause, and related information from text
    """
    
    def __init__(self, config: Dict):
        """
        Initialize LLM extractor with model configuration
        
        Args:
            config: Configuration dictionary with model settings
        """
        self.config = config
        self.model_config = config.get('model', {})
        self.prompts = config.get('prompts', {})
        
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the LLM model and tokenizer"""
        model_name = self.model_config.get('name', 'mistralai/Mistral-7B-Instruct-v0.2')
        
        logger.info(f"Loading model: {model_name}")
        
        try:
            # Configure quantization for memory efficiency
            quantization_config = None
            if self.model_config.get('quantization', True):
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Determine device
            device = self.model_config.get('device', 'auto')
            if device == 'auto':
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map=device if device == 'auto' else None,
                trust_remote_code=True,
                torch_dtype=torch.float16 if device != 'cpu' else torch.float32
            )
            
            if device not in ['auto', 'cuda'] and device == 'cpu':
                self.model = self.model.to(device)
            
            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=self.model_config.get('max_length', 512),
                temperature=self.model_config.get('temperature', 0.3),
                top_p=self.model_config.get('top_p', 0.9),
                do_sample=True,
            )
            
            logger.info(f"Model loaded successfully on {device}")
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.warning("Falling back to rule-based extraction")
            self.pipeline = None
    
    def extract_failure_info(self, text: str) -> Dict[str, str]:
        """
        Extract FMEA components from text using LLM
        
        Args:
            text: Input text (review, report, complaint)
            
        Returns:
            Dictionary with extracted information:
            {
                'failure_mode': str,
                'effect': str,
                'cause': str,
                'component': str,
                'existing_controls': str
            }
        """
        if self.pipeline is None:
            # Fallback to rule-based extraction
            return self._rule_based_extraction(text)
        
        try:
            # Format prompt
            prompt = self.prompts.get('failure_extraction', '').format(text=text)
            
            # Generate response
            response = self.pipeline(
                prompt,
                max_new_tokens=self.model_config.get('max_length', 512),
                return_full_text=False
            )[0]['generated_text']
            
            # Parse JSON response
            extracted_info = self._parse_llm_response(response)
            
            # Validate and clean
            extracted_info = self._validate_extraction(extracted_info)
            
            return extracted_info
            
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}")
            return self._rule_based_extraction(text)
    
    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        """
        Parse LLM response to extract structured information
        
        Args:
            response: Raw LLM output
            
        Returns:
            Parsed dictionary
        """
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Fallback: parse key-value pairs
        result = {
            'failure_mode': 'Unknown',
            'effect': 'Unknown',
            'cause': 'Unknown',
            'component': 'Unknown',
            'existing_controls': 'Unknown'
        }
        
        for key in result.keys():
            pattern = rf'{key}["\']?\s*:\s*["\']?(.*?)["\']?(?:,|\n|\}})'
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                result[key] = match.group(1).strip()
        
        return result
    
    def _validate_extraction(self, extracted: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and clean extracted information
        
        Args:
            extracted: Raw extracted dictionary
            
        Returns:
            Validated dictionary
        """
        required_keys = ['failure_mode', 'effect', 'cause', 'component', 'existing_controls']
        
        for key in required_keys:
            if key not in extracted or not extracted[key] or extracted[key].lower() in ['unknown', 'none', 'n/a', '']:
                extracted[key] = 'Not specified'
        
        return extracted
    
    def _rule_based_extraction(self, text: str) -> Dict[str, str]:
        """
        Fallback rule-based extraction when LLM is unavailable
        
        Args:
            text: Input text
            
        Returns:
            Extracted information dictionary
        """
        logger.info("Using rule-based extraction")
        
        text_lower = text.lower()
        
        # Identify failure mode keywords
        failure_keywords = ['fail', 'broke', 'malfunction', 'problem', 'issue', 'defect', 
                           'not work', 'stopped', 'error', 'fault']
        
        effect_keywords = ['result', 'consequence', 'impact', 'caused', 'led to', 'unable']
        
        cause_keywords = ['because', 'due to', 'caused by', 'reason', 'from']
        
        component_keywords = ['engine', 'brake', 'transmission', 'steering', 'suspension',
                            'electrical', 'battery', 'tire', 'wheel', 'door', 'window']
        
        # Extract failure mode
        failure_mode = self._extract_with_keywords(text, failure_keywords)
        
        # Extract effect
        effect = self._extract_with_keywords(text, effect_keywords)
        
        # Extract cause
        cause = self._extract_with_keywords(text, cause_keywords)
        
        # Extract component
        component = self._extract_with_keywords(text, component_keywords)
        
        return {
            'failure_mode': failure_mode if failure_mode else text[:100],
            'effect': effect if effect else 'Functionality impacted',
            'cause': cause if cause else 'Under investigation',
            'component': component if component else 'General',
            'existing_controls': 'Not specified'
        }
    
    def _extract_with_keywords(self, text: str, keywords: List[str]) -> str:
        """
        Extract sentence containing keywords
        
        Args:
            text: Input text
            keywords: List of keywords to search for
            
        Returns:
            Extracted sentence or empty string
        """
        sentences = text.split('.')
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                return sentence.strip()
        return ''
    
    def batch_extract(self, texts: List[str]) -> List[Dict[str, str]]:
        """
        Extract failure information from multiple texts
        
        Args:
            texts: List of input texts
            
        Returns:
            List of extracted information dictionaries
        """
        logger.info(f"Batch extracting from {len(texts)} texts")
        
        results = []
        
        # Use tqdm for progress bar 
        for text in tqdm(texts, desc="Extracting FMEA information", unit="text"):
            extracted = self.extract_failure_info(text)
            results.append(extracted)
        
        return results


if __name__ == "__main__":
    # Example usage
    import yaml
    
    with open('../config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    extractor = LLMExtractor(config)
    
    # Test extraction
    sample_text = """
    The brake system failed completely while driving on the highway at 70 mph.
    This resulted in a dangerous situation where I couldn't stop the car properly.
    The failure was caused by worn brake pads that were not detected during
    the last maintenance check.
    """
    
    result = extractor.extract_failure_info(sample_text)
    print("\nExtracted Information:")
    print(json.dumps(result, indent=2))
