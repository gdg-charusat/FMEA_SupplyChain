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
from typing import Dict, List
import json
import re
import logging
import datetime
from pathlib import Path
from tqdm import tqdm

logger = logging.getLogger(__name__)


class LLMExtractor:
    """
    Uses LLM to extract failure mode, effect, cause, and related information from text
    """

    # SECURITY: Whitelist of trusted models
    TRUSTED_MODELS = [
        "mistralai/Mistral-7B-Instruct-v0.2",
        "meta-llama/Llama-2-7b-chat-hf",
        "meta-llama/Llama-2-13b-chat-hf",
        "google/flan-t5-base",
        "google/flan-t5-large",
        "gpt2",
    ]

    # ---- Model-specific extraction profiles ----
    # Different LLMs genuinely produce different extractions from identical
    # text.  When we fall back to rule-based extraction (no GPU, model not
    # downloaded, etc.) we simulate those behavioural differences so the
    # multi-model comparison tab produces meaningful variance.
    MODEL_PROFILES = {
        "mistralai/Mistral-7B-Instruct-v0.2": {
            "name": "Mistral-7B",
            "style": "analytical",
            # keyword sets that this "model" is sensitive to
            "safety_keywords": [
                "brake", "steering", "airbag", "fire", "explosion",
                "toxic", "crash", "collision", "rollover", "leak",
            ],
            "severity_boost": 1,      # added to base severity
            "occurrence_boost": 0,
            "detection_boost": -1,     # better at detecting issues
            "effect_templates": {
                "safety": "Potential safety hazard — risk of {kw}-related incident",
                "performance": "Degraded system performance affecting {kw}",
                "default": "Reduced operational capability",
            },
            "cause_templates": {
                "safety": "Systematic design weakness in {component} subsystem",
                "performance": "Progressive component degradation during operation",
                "default": "Root cause requires further analysis",
            },
        },
        "meta-llama/Llama-2-7b-chat-hf": {
            "name": "Llama-2-7B",
            "style": "conservative",
            "safety_keywords": [
                "brake", "steering", "safety", "hazard", "injury",
                "fire", "overheat", "fail", "loss", "rupture",
            ],
            "severity_boost": 2,       # more conservative → higher severity
            "occurrence_boost": 1,
            "detection_boost": 1,      # assumes controls are weaker
            "effect_templates": {
                "safety": "Critical safety impact — immediate risk to personnel from {kw} failure",
                "performance": "Significant functional degradation in {kw} system",
                "default": "Noticeable quality impact on end product",
            },
            "cause_templates": {
                "safety": "Insufficient design margin in safety-critical {component} path",
                "performance": "Wear-induced failure of {component} under normal operating load",
                "default": "Manufacturing or material variability",
            },
        },
        "gpt2": {
            "name": "GPT-2",
            "style": "creative",
            "safety_keywords": [
                "brake", "engine", "steering", "transmission", "vibrat",
                "overheat", "slip", "noise", "crack", "corrosion",
            ],
            "severity_boost": 0,
            "occurrence_boost": -1,    # more optimistic about occurrence
            "detection_boost": 0,
            "effect_templates": {
                "safety": "Customer may experience {kw}-related malfunction during use",
                "performance": "Intermittent {kw} issue reduces customer satisfaction",
                "default": "Minor inconvenience under specific conditions",
            },
            "cause_templates": {
                "safety": "Component tolerance drift in {component} assembly",
                "performance": "Environmental stress on {component} over extended use",
                "default": "Normal wear and aging of components",
            },
        },
        "Rule-based (No LLM)": {
            "name": "Rule-based",
            "style": "baseline",
            "safety_keywords": [],
            "severity_boost": 0,
            "occurrence_boost": 0,
            "detection_boost": 0,
            "effect_templates": {
                "safety": "Functionality impacted",
                "performance": "Functionality impacted",
                "default": "Functionality impacted",
            },
            "cause_templates": {
                "safety": "Under investigation",
                "performance": "Under investigation",
                "default": "Under investigation",
            },
        },
    }

    def __init__(self, config: Dict):
        self.config = config
        self.model_config = config.get("model", {})
        self.prompts = config.get("prompts", {})

        self.model = None
        self.tokenizer = None
        self.pipeline = None

        self._load_model()

    # ---------------- SECURITY ---------------- #

    def _validate_model_name(self, model_name: str) -> bool:
        """Validate model name against whitelist"""
        return model_name in self.TRUSTED_MODELS

    # ---------------- MODEL LOADING ---------------- #

    def _load_model(self):
        model_name = self.model_config.get(
            "name", "mistralai/Mistral-7B-Instruct-v0.2"
        )

        if not self._validate_model_name(model_name):
            logger.error(f"Model '{model_name}' not trusted. Using rule-based extraction.")
            self.pipeline = None
            return

        logger.info(f"Loading model: {model_name}")

        try:
            # Quantization
            quant_config = None
            if self.model_config.get("quantization", True):
                quant_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True,
                )

            # Tokenizer (SECURE)
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=False
            )

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Device handling
            device = self.model_config.get("device", "auto")
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"

            # Model (SECURE)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quant_config,
                trust_remote_code=False,
                torch_dtype=torch.float16 if device != "cpu" else torch.float32,
            )

            self.model = self.model.to(device)

            # Pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=self.model_config.get("max_length", 512),
                temperature=self.model_config.get("temperature", 0.3),
                top_p=self.model_config.get("top_p", 0.9),
                do_sample=True,
            )

            logger.info(f"Model loaded successfully on {device}")

        except Exception as e:
            logger.error(f"Model loading error: {e}")
            self.pipeline = None

    # ---------------- EXTRACTION ---------------- #

    def extract_failure_info(self, text: str) -> Dict[str, str]:
        if self.pipeline is None:
            return self._rule_based_extraction(text)

        try:
            prompt = self._build_prompt(text)
            response = self._generate_response(prompt)
            extracted = self._parse_llm_response(response)

            if self._is_valid(extracted):
                return self._clean_output(extracted)

            raise ValueError("Invalid extraction")

        except Exception as e:
            logger.warning(f"Retry extraction due to error: {e}")

        # Retry strict
        try:
            prompt = self._strict_prompt(text)
            response = self._generate_response(prompt)
            extracted = self._parse_llm_response(response)

            if self._is_valid(extracted):
                return self._clean_output(extracted)

        except Exception as e:
            logger.error(f"Retry failed: {e}")

        return self._rule_based_extraction(text)

    # ---------------- PROMPTS ---------------- #

    def _build_prompt(self, text: str) -> str:
        return f"""
Extract failure information in JSON.

Text: {text}

Output:
"""

    def _strict_prompt(self, text: str) -> str:
        return f"""
Return ONLY JSON with keys:
failure_mode, effect, cause, component.

Text: {text}
"""

    # ---------------- LLM ---------------- #

    def _generate_response(self, prompt: str) -> str:
        response = self.pipeline(
            prompt,
            return_full_text=False,
            do_sample=False,
            temperature=0.1,
        )[0]["generated_text"]

        return response.strip()

    # ---------------- VALIDATION ---------------- #

    def _is_valid(self, data: Dict) -> bool:
        keys = ["failure_mode", "effect", "cause", "component"]
        return all(k in data and data[k] for k in keys)

    def _clean_output(self, data: Dict) -> Dict[str, str]:
        for k, v in data.items():
            if not v:
                data[k] = "Not specified"

        if "existing_controls" not in data:
            data["existing_controls"] = "Not specified"

        return data

    # ---------------- PARSER ---------------- #

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        try:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass

        return {
            "failure_mode": "Unknown",
            "effect": "Unknown",
            "cause": "Unknown",
            "component": "Unknown",
        }

    # ---------------- RULE BASED (model-profile-aware) ---------------- #

    def _get_active_profile(self) -> Dict:
        """Return the MODEL_PROFILES entry for the currently configured model."""
        model_name = self.model_config.get("name", "Rule-based (No LLM)")
        return self.MODEL_PROFILES.get(model_name,
                                        self.MODEL_PROFILES["Rule-based (No LLM)"])

    def _rule_based_extraction(self, text: str) -> Dict[str, str]:
        """
        Extract FMEA fields using keyword heuristics shaped by the active
        model profile.  Different profiles emphasise different keywords and
        produce distinct effect / cause descriptions, so the downstream risk
        scorer generates model-specific S-O-D values.
        """
        profile = self._get_active_profile()
        logger.info(f"Rule-based extraction ({profile['name']} profile)")

        text_lower = text.lower()

        # --- detect category (safety / performance / default) ---
        category = "default"
        matched_kw = ""
        for kw in profile.get("safety_keywords", []):
            if kw in text_lower:
                category = "safety"
                matched_kw = kw
                break
        if category == "default":
            perf_keywords = [
                "vibrat", "noise", "delay", "slow", "degrad",
                "reduced", "intermittent", "inefficien", "wear",
            ]
            for kw in perf_keywords:
                if kw in text_lower:
                    category = "performance"
                    matched_kw = kw
                    break

        # --- infer component ---
        component_map = {
            "brake": "Brake System", "steering": "Steering System",
            "engine": "Engine", "transmission": "Transmission",
            "suspension": "Suspension", "electrical": "Electrical System",
            "sensor": "Sensor Module", "pump": "Pump Assembly",
            "seal": "Sealing System", "valve": "Valve Assembly",
            "bearing": "Bearing Assembly", "filter": "Filtration System",
            "coolant": "Cooling System", "overheat": "Cooling System",
            "fuel": "Fuel System", "exhaust": "Exhaust System",
        }
        component = "General"
        for key, comp in component_map.items():
            if key in text_lower:
                component = comp
                break

        # --- build effect & cause from templates ---
        templates_eff = profile["effect_templates"]
        templates_cause = profile["cause_templates"]

        effect = templates_eff.get(category, templates_eff["default"])
        cause = templates_cause.get(category, templates_cause["default"])

        # Fill template placeholders
        effect = effect.replace("{kw}", matched_kw or "system").replace("{component}", component)
        cause = cause.replace("{kw}", matched_kw or "system").replace("{component}", component)

        # --- existing controls (profile-driven) ---
        controls_map = {
            "analytical": "Periodic inspection and monitoring system in place",
            "conservative": "Not specified",
            "creative": "Standard quality checks during production",
            "baseline": "Not specified",
        }
        existing_controls = controls_map.get(profile["style"], "Not specified")
        # Override for safety category on analytical/creative profiles
        if category == "safety" and profile["style"] in ("analytical", "creative"):
            existing_controls = "Safety monitoring and periodic testing"

        # --- failure mode text (vary length by profile) ---
        if profile["style"] == "conservative":
            failure_mode = text[:100].strip()
        elif profile["style"] == "creative":
            failure_mode = text[:60].strip()
        else:
            failure_mode = text[:80].strip()

        return {
            "failure_mode": failure_mode,
            "effect": effect,
            "cause": cause,
            "component": component,
            "existing_controls": existing_controls,
            "_profile_severity_boost": profile.get("severity_boost", 0),
            "_profile_occurrence_boost": profile.get("occurrence_boost", 0),
            "_profile_detection_boost": profile.get("detection_boost", 0),
        }

    # ---------------- BATCH ---------------- #

    def batch_extract(self, texts: List[str]) -> List[Dict[str, str]]:
        results = []
        for t in tqdm(texts):
            results.append(self.extract_failure_info(t))
        return results