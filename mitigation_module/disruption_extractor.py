"""
Disruption Information Extractor - Team 066 Final Version
Unified logic for: Text, CSV, and Images (OCR)
"""

import json
import logging
import re
from typing import Dict, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, validator
import pandas as pd

# Initialize Logger
logger = logging.getLogger(__name__)

# OCR imports with robust fallback logic
try:
    import easyocr
    OCR_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    OCR_AVAILABLE = False
    logger.warning("EasyOCR library not found. OCR features will be disabled.")

class DisruptionEvent(BaseModel):
    """
    Validated disruption event model
    """
    target_route_id: int = Field(..., ge=1, le=10, description="Route ID affected (1-10)")
    impact_type: str = Field(..., description="Type of disruption (flood, strike, accident, etc.)")
    cost_multiplier: float = Field(..., ge=1.0, le=15.0, description="Cost multiplication factor")
    severity_score: int = Field(..., ge=1, le=10, description="Severity rating (1-10)")
    
    @validator('impact_type')
    def normalize_impact_type(cls, v):
        """Normalize impact type to lowercase"""
        return v.lower().strip()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'target_route_id': self.target_route_id,
            'impact_type': self.impact_type,
            'cost_multiplier': self.cost_multiplier,
            'severity_score': self.severity_score
        }

class DisruptionExtractor:
    """
    Unified multimodal disruption information extractor.
    Redundant code bodies removed to ensure logic reachability.
    """
    
    def __init__(self, config_path: str = "mitigation_module/mapping_config.json"):
        """
        Initialize extractor with location mapping
        """
        self.config_path = Path(config_path)
        self.mapping_config = self._load_mapping_config()
        self.ocr_reader = None
        
        if OCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
                self.ocr_reader = None

    def _load_mapping_config(self) -> Dict:
        """Load location to Route ID mapping safely"""
        default_config = {"mappings": {"locations": {}}, "impact_types": {}}
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading config: {e}")
                return default_config
        else:
            logger.warning(f"Config not found: {self.config_path}. Using defaults.")
            return default_config
    
    def extract_from_text(self, text: str) -> List[DisruptionEvent]:
        """
        Extract disruption from plain text
        """
        logger.info(f"Extracting from text: {text[:100]}...")
        disruptions = self._rule_based_extraction(text)
        return [DisruptionEvent(**d) for d in disruptions]

    def _rule_based_extraction(self, text: str) -> List[Dict]:
        """
        Unified extraction logic. 
        Resolves NameError by using self.mapping_config.
        """
        text_lower = text.lower()
        disruptions = []
        affected_routes = []
        
        # 1. Regex for explicitly mentioned route numbers
        route_pattern = r'(?:route|r)\s*(\d+)|(?:routes?)\s*((?:\d+(?:\s*(?:,|and)\s*)?)+)'
        matches = re.finditer(route_pattern, text_lower, re.IGNORECASE)
        
        for match in matches:
            if match.group(1):
                affected_routes.append(int(match.group(1)))
            elif match.group(2):
                numbers = re.findall(r'\d+', match.group(2))
                affected_routes.extend([int(n) for n in numbers])
        
        # 2. Config-based location fallback
        if not affected_routes:
            # Resolves NameError: uses self.mapping_config
            loc_map = self.mapping_config.get('mappings', {}).get('locations', {})
            for location, routes in loc_map.items():
                if location.lower() in text_lower:
                    if isinstance(routes, list):
                        affected_routes.extend(routes)
                    else:
                        affected_routes.append(routes)
                    break
        
        # 3. Final standalone number check (1-8)
        if not affected_routes:
            all_numbers = re.findall(r'\b([1-8])\b', text_lower)
            if all_numbers:
                affected_routes = [int(n) for n in all_numbers]

        # Safety Check
        if not affected_routes:
            logger.warning(f"No route info found in text: {text[:50]}")
            return []

        # Determine severity/multiplier
        cost_multiplier, severity_score, impact_type = 1.5, 5, "Disruption"
        
        if any(w in text_lower for w in ['collapse', 'catastrophic', 'critical', 'severe', 'closed']):
            cost_multiplier, severity_score, impact_type = 15.0, 10, "Critical"
        elif any(w in text_lower for w in ['fire', 'explosion', 'toxic', 'hazardous']):
            cost_multiplier, severity_score, impact_type = 10.0, 9, "Hazardous"
        
        # Extract explicit multiplier if mentioned
        multiplier_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:x|times|multiplier)', text_lower)
        if multiplier_match:
            cost_multiplier = float(multiplier_match.group(1))
        
        for route_id in set(affected_routes):
            disruptions.append({
                'target_route_id': route_id,
                'impact_type': impact_type,
                'cost_multiplier': cost_multiplier,
                'severity_score': severity_score
            })
        
        return disruptions

    def extract_from_image(self, image_path: str) -> List[DisruptionEvent]:
        """
        Extract disruptions from image with OCR fallback
        """
        if not OCR_AVAILABLE or self.ocr_reader is None:
            logger.error(f"OCR requested for {image_path} but EasyOCR is not available.")
            return []
        
        try:
            results = self.ocr_reader.readtext(image_path)
            text = '\n'.join([result[1] for result in results])
            return self.extract_from_text(text)
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return []
    
    def extract_from_csv(self, file_path: str) -> List[DisruptionEvent]:
        """
        Extract disruptions from CSV file
        """
        try:
            df = pd.read_csv(file_path)
            disruptions = []
            required = ['target_route_id', 'impact_type', 'cost_multiplier', 'severity_score']
            
            if all(col in df.columns for col in required):
                for _, row in df.iterrows():
                    disruptions.append(DisruptionEvent(**row.to_dict()))
            else:
                text_cols = [col for col in df.columns if df[col].dtype == 'object']
                for _, row in df.iterrows():
                    text = ' '.join(str(row[col]) for col in text_cols)
                    disruptions.extend(self.extract_from_text(text))
            return disruptions
        except Exception as e:
            logger.error(f"CSV process failed: {e}")
            return []

    def validate_and_aggregate(self, disruptions: List[DisruptionEvent]) -> List[Dict]:
        """
        Validate and aggregate disruptions by route (worst case)
        """
        route_disruptions = {}
        for disruption in disruptions:
            rid = disruption.target_route_id
            if rid not in route_disruptions or disruption.cost_multiplier > route_disruptions[rid].cost_multiplier:
                route_disruptions[rid] = disruption
        
        return [d.to_dict() for d in route_disruptions.values()]
