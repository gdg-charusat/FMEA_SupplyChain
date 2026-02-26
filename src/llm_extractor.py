"""
LLM-Based Information Extraction Module
Uses transformer models to extract FMEA-relevant information from text
"""

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
    BitsAndBytesConfig,
)
from typing import Dict, List, Optional, Union
import json
import re
import logging
import datetime
import os
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
        self.model_config = config.get("model", {})
        self.prompts = config.get("prompts", {})

        self.model = None
        self.tokenizer = None
        self.pipeline = None

        self._load_model()

    def _load_model(self):
        """Load the LLM model and tokenizer"""
        model_name = self.model_config.get("name", "mistralai/Mistral-7B-Instruct-v0.2")

        logger.info(f"Loading model: {model_name}")

        try:
            # Configure quantization for memory efficiency
            quantization_config = None
            if self.model_config.get("quantization", True):
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Determine device
            device_config = self.model_config.get("device", "auto")

            # Set device_map and actual device for model loading
            device_map = None
            actual_device = device_config

            if device_config == "auto":
                # Use automatic device mapping for efficient GPU utilization
                device_map = "auto"
                actual_device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                # Explicit device set by user (e.g., 'cpu' or 'cuda')
                actual_device = device_config

            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map=device_map,
                trust_remote_code=True,
                torch_dtype=torch.float16 if actual_device != "cpu" else torch.float32,
            )

            # Manually move to device only if device_map was not used
            if device_map is None and actual_device in ["cpu", "cuda"]:
                self.model = self.model.to(actual_device)

            # Create pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=self.model_config.get("max_length", 512),
                temperature=self.model_config.get("temperature", 0.3),
                top_p=self.model_config.get("top_p", 0.9),
                do_sample=True,
            )

            logger.info(
                f"Model loaded successfully on {actual_device} (device_map: {device_map})"
            )

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.warning("Falling back to rule-based extraction")
            self.pipeline = None

    def extract_failure_info(self, text: str) -> Dict[str, str]:
        """
        Extract FMEA components from text using LLM with retry logic
        
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
        
        # First attempt with detailed prompt
        try:
            prompt = self._build_extraction_prompt(text)
            response = self._generate_llm_response(prompt)
            extracted_info = self._parse_llm_response(response)
            
            # Validate extraction
            if self._is_valid_extraction(extracted_info):
                return self._validate_extraction(extracted_info)
            else:
                # Log and retry with stricter prompt
                self._log_extraction_failure(text, response, "Invalid extraction - retrying")
                raise ValueError("Invalid extraction format")
                
        except Exception as e:
            logger.warning(f"First extraction attempt failed: {e}")
            
        # Retry attempt with stricter prompt  
        try:
            strict_prompt = self._build_strict_retry_prompt(text)
            response = self._generate_llm_response(strict_prompt)
            extracted_info = self._parse_llm_response(response)
            
            if self._is_valid_extraction(extracted_info):
                return self._validate_extraction(extracted_info)
            else:
                self._log_extraction_failure(text, response, "Retry also failed")
                raise ValueError("Retry extraction also invalid")
                
        except Exception as e:
            logger.error(f"Both extraction attempts failed: {e}")
            self._log_extraction_failure(text, "", f"Complete failure: {e}")
            return self._rule_based_extraction(text)
    
    def _build_extraction_prompt(self, text: str) -> str:
        """
        Build structured extraction prompt with clear definitions and examples
        
        Args:
            text: Input text to analyze
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert in Failure Mode and Effects Analysis (FMEA). 
Analyze the following text and extract failure-related information.

IMPORTANT DEFINITIONS:
- FAILURE MODE: What physically fails or deviates from normal operation (e.g., "Gearbox oil leakage", "Motor overheating")
- EFFECT: The consequence experienced by the end user or downstream system (e.g., "Reduced transmission life", "System shutdown")
- CAUSE: The root originating mechanism that triggers the failure (e.g., "Seal ring damage", "Inadequate ventilation")
- COMPONENT: The specific physical system or subsystem affected (e.g., "Gearbox", "Power Supply")

RULES:
1. If the cause is genuinely unknown, output "Unknown" rather than guessing
2. Distinguish failure mode (what breaks) from effect (what happens after)
3. Output ONLY valid JSON with no explanation or preamble

EXAMPLES:

Input: "The hydraulic cylinder is leaking fluid due to a damaged seal ring. This is causing the hydraulic system to fail."
Output: {{"failure_mode": "Hydraulic cylinder leakage", "effect": "Hydraulic system failure", "cause": "Seal ring damage", "component": "Hydraulic cylinder"}}

Input: "Motor temperature is extremely high, probably due to bearing damage or fan failure. The motor will be damaged if this continues."
Output: {{"failure_mode": "Excessively high motor temperature", "effect": "Motor damage", "cause": "Bearing damage or motor fan damage", "component": "Motor"}}

Input: "The gas turbine starter has low efficiency and fails to turn the engine when starting."
Output: {{"failure_mode": "Function failure when not turning the engine on starting", "effect": "Function failure", "cause": "Starter low efficiency", "component": "Gas turbine starter"}}

Now analyze this text:
Text: {text}

Output:"""
        return prompt
    
    def _build_strict_retry_prompt(self, text: str) -> str:
        """
        Build stricter prompt for retry attempt
        
        Args:
            text: Input text to analyze
            
        Returns:
            Strict retry prompt
        """
        prompt = f"""Your previous response was not valid JSON. 

Analyze this text and output ONLY a JSON object with these exact keys:
{{"failure_mode": "what physically fails", "effect": "consequence to user", "cause": "root mechanism", "component": "affected system"}}

Text: {text}

Response (JSON only):"""
        return prompt
    
    def _generate_llm_response(self, prompt: str) -> str:
        """
        Generate LLM response with error handling
        
        Args:
            prompt: Formatted prompt
            
        Returns:
            Generated response text
        """
        response = self.pipeline(
            prompt,
            max_new_tokens=self.model_config.get('max_length', 512),
            return_full_text=False,
            do_sample=False,  # Use deterministic generation for consistency
            temperature=0.1   # Low temperature for factual extraction
        )[0]['generated_text']
        return response.strip()
    
    def _is_valid_extraction(self, extracted: Dict[str, str]) -> bool:
        """
        Validate if extraction contains required fields
        
        Args:
            extracted: Extracted information dictionary
            
        Returns:
            True if valid extraction
        """
        required_fields = ['failure_mode', 'effect', 'cause', 'component']
        
        # Check all required fields exist
        for field in required_fields:
            if field not in extracted:
                return False
            
            value = extracted[field]
            if not value or value.lower().strip() in ['', 'unknown', 'none', 'n/a', 'not specified']:
                # Allow "Unknown" for cause field only (as per rules)
                if field == 'cause' and value.lower().strip() == 'unknown':
                    continue
                return False
        
        return True
    
    def _log_extraction_failure(self, input_text: str, model_response: str, reason: str):
        """
        Log extraction failures for debugging
        
        Args:
            input_text: Original input text
            model_response: Model's response
            reason: Failure reason
        """
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'input': input_text[:500],  # Truncate long inputs
            'model_response': model_response[:500],
            'reason': reason
        }
        
        log_file = log_dir / "extraction_failures.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + "\n")
    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        """
        Parse LLM response to extract structured information with improved parsing
        
        Args:
            response: Raw LLM output

        Returns:
            Parsed dictionary
        """
        # Clean the response
        response = response.strip()
        
        try:
            # Try direct JSON parsing first
            if response.startswith('{') and response.endswith('}'):
                return json.loads(response)
            
            # Try to find JSON block in response
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, response, re.DOTALL)
            
            for match in json_matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
                    
            # Try to extract JSON from code blocks
            code_block_pattern = r'```(?:json)?\s*({.*?})\s*```'
            code_matches = re.findall(code_block_pattern, response, re.DOTALL)
            
            for match in code_matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}")
        
        # Fallback: try to extract key-value pairs
        result = {
            'failure_mode': 'Unknown',
            'effect': 'Unknown',
            'cause': 'Unknown',
            'component': 'Unknown'
        }
        
        # Try various patterns to extract fields
        patterns = {
            'failure_mode': [r'["\']?failure_mode["\']?\s*[:=]\s*["\']([^"\'\\n}]+)["\']?', 
                           r'failure mode:\s*([^\\n}]+)', 
                           r'what fails\?\s*:\s*([^\\n}]+)'],
            'effect': [r'["\']?effect["\']?\s*[:=]\s*["\']([^"\'\\n}]+)["\']?',
                      r'effect:\s*([^\\n}]+)',
                      r'consequence:\s*([^\\n}]+)'],
            'cause': [r'["\']?cause["\']?\s*[:=]\s*["\']([^"\'\\n}]+)["\']?',
                     r'cause:\s*([^\\n}]+)',
                     r'reason:\s*([^\\n}]+)'],
            'component': [r'["\']?component["\']?\s*[:=]\s*["\']([^"\'\\n}]+)["\']?',
                         r'component:\s*([^\\n}]+)',
                         r'system:\s*([^\\n}]+)']
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    value = match.group(1).strip().rstrip(',"\'')
                    if value and value.lower() not in ['unknown', 'none', 'n/a']:
                        result[field] = value
                    break
        
        return result

    def _validate_extraction(self, extracted: Dict[str, str]) -> Dict[str, str]:
        """
        Validate and clean extracted information

        Args:
            extracted: Raw extracted dictionary

        Returns:
            Validated dictionary with cleaned values
        """
        required_keys = ['failure_mode', 'effect', 'cause', 'component']
        
        # Ensure all required keys exist
        for key in required_keys:
            if key not in extracted:
                extracted[key] = 'Not specified'
        
        # Clean and validate each field
        for key, value in extracted.items():
            if not value or str(value).strip() == '':
                extracted[key] = 'Not specified'
            elif str(value).lower().strip() in ['none', 'n/a', 'not applicable']:
                extracted[key] = 'Not specified'
            else:
                # Clean the value
                cleaned = str(value).strip()
                # Remove quotes if present
                if cleaned.startswith('"') and cleaned.endswith('"'):
                    cleaned = cleaned[1:-1]
                if cleaned.startswith("'") and cleaned.endswith("'"):
                    cleaned = cleaned[1:-1]
                extracted[key] = cleaned
        
        # Add existing_controls if not present for backward compatibility
        if 'existing_controls' not in extracted:
            extracted['existing_controls'] = 'Not specified'
        
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
        failure_keywords = [
            "fail",
            "broke",
            "malfunction",
            "problem",
            "issue",
            "defect",
            "not work",
            "stopped",
            "error",
            "fault",
        ]

        effect_keywords = [
            "result",
            "consequence",
            "impact",
            "caused",
            "led to",
            "unable",
        ]

        cause_keywords = ["because", "due to", "caused by", "reason", "from"]

        component_keywords = [
            "engine",
            "brake",
            "transmission",
            "steering",
            "suspension",
            "electrical",
            "battery",
            "tire",
            "wheel",
            "door",
            "window",
        ]

        # Extract failure mode
        failure_mode = self._extract_with_keywords(text, failure_keywords)

        # Extract effect
        effect = self._extract_with_keywords(text, effect_keywords)

        # Extract cause
        cause = self._extract_with_keywords(text, cause_keywords)

        # Extract component
        component = self._extract_with_keywords(text, component_keywords)

        return {
            "failure_mode": failure_mode if failure_mode else text[:100],
            "effect": effect if effect else "Functionality impacted",
            "cause": cause if cause else "Under investigation",
            "component": component if component else "General",
            "existing_controls": "Not specified",
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
        sentences = text.split(".")
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in keywords):
                return sentence.strip()
        return ""

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

    with open("../config/config.yaml", "r") as f:
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
