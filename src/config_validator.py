"""
Configuration Validator Module
Validates YAML configuration against schema to prevent injection attacks
"""

import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Whitelist of allowed model names
ALLOWED_MODEL_NAMES = {
    "mistralai/Mistral-7B-Instruct-v0.2",
    "mistralai/Mistral-7B-Instruct-v0.1",
    "meta-llama/Llama-2-7b-chat-hf",
    "meta-llama/Llama-2-13b-chat-hf",
    "google/flan-t5-base",
    "google/flan-t5-large",
    "gpt2",
    "gpt2-medium",
    "gpt2-large",
}


class ConfigValidator:
    """Validates configuration against strict schema"""
    
    @staticmethod
    def validate_model_config(model_config: Dict[str, Any]) -> bool:
        """Validate model configuration section"""
        if not isinstance(model_config, dict):
            raise ValueError("model config must be a dictionary")
        
        # Validate model name against whitelist
        model_name = model_config.get("name", "")
        if model_name not in ALLOWED_MODEL_NAMES:
            raise ValueError(
                f"Model '{model_name}' not in whitelist. "
                f"Allowed: {', '.join(sorted(ALLOWED_MODEL_NAMES))}"
            )
        
        # Validate numeric parameters
        if "max_length" in model_config:
            max_length = model_config["max_length"]
            if not isinstance(max_length, int) or not (1 <= max_length <= 2048):
                raise ValueError("max_length must be integer between 1 and 2048")
        
        if "temperature" in model_config:
            temp = model_config["temperature"]
            if not isinstance(temp, (int, float)) or not (0.0 <= temp <= 2.0):
                raise ValueError("temperature must be number between 0.0 and 2.0")
        
        if "top_p" in model_config:
            top_p = model_config["top_p"]
            if not isinstance(top_p, (int, float)) or not (0.0 <= top_p <= 1.0):
                raise ValueError("top_p must be number between 0.0 and 1.0")
        
        if "inference_timeout" in model_config:
            timeout = model_config["inference_timeout"]
            if not isinstance(timeout, int) or not (1 <= timeout <= 300):
                raise ValueError("inference_timeout must be integer between 1 and 300 seconds")
        
        # Validate device
        device = model_config.get("device", "auto")
        if device not in ["auto", "cpu", "cuda"]:
            raise ValueError("device must be 'auto', 'cpu', or 'cuda'")
        
        # Validate quantization
        if "quantization" in model_config:
            if not isinstance(model_config["quantization"], bool):
                raise ValueError("quantization must be boolean")
        
        return True
    
    @staticmethod
    def validate_text_processing(text_config: Dict[str, Any]) -> bool:
        """Validate text processing configuration"""
        if not isinstance(text_config, dict):
            raise ValueError("text_processing config must be a dictionary")
        
        if "max_reviews_per_batch" in text_config:
            batch_size = text_config["max_reviews_per_batch"]
            if not isinstance(batch_size, int) or not (1 <= batch_size <= 1000):
                raise ValueError("max_reviews_per_batch must be integer between 1 and 1000")
        
        return True
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate entire configuration"""
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        # Validate model section
        if "model" in config:
            ConfigValidator.validate_model_config(config["model"])
        
        # Validate text_processing section
        if "text_processing" in config:
            ConfigValidator.validate_text_processing(config["text_processing"])
        
        return True


def load_config_safe(config_path: str) -> Dict[str, Any]:
    """
    Safely load and validate YAML configuration
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ValueError: If configuration is invalid
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate against schema
    ConfigValidator.validate_config(config)
    
    logger.info("Configuration validated successfully")
    return config
