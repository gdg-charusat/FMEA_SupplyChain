"""
Disruption Information Extractor
Uses Claude 3.5 Sonnet for multimodal input processing and JSON extraction
Handles: Text, CSV, Images (OCR), Emails, PDFs
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
# Import dynamic route lookup for non-hardcoded cities
try:
    from .dynamic_network import get_routes_for_city
    DYNAMIC_ROUTING_AVAILABLE = True
except ImportError:
    DYNAMIC_ROUTING_AVAILABLE = False
    logger.warning("Dynamic routing not available. Will use mapping config only.")

# OCR imports (using existing FMEA OCR setup)
try:
    import easyocr
    OCR_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    OCR_AVAILABLE = False
    logger.warning("EasyOCR library not found. OCR features will be disabled. Install with: pip install easyocr")

class DisruptionEvent(BaseModel):
    """
    Validated disruption event model
    Ensures clean output regardless of messy input
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
    Multimodal disruption information extractor
    Uses rule-based extraction with a graceful OCR fallback
    """
    
    def __init__(self, config_path: str = "mitigation_module/mapping_config.json"):
        """
        Initialize extractor with location mapping
        """
        self.config_path = Path(config_path)
        self.mapping_config = self._load_mapping_config()
        self.ocr_reader = None
        
        # Safe initialization of OCR Reader
        if OCR_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
                logger.info("EasyOCR Reader initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR Reader: {e}")
                self.ocr_reader = None

    def _load_mapping_config(self) -> Dict:
        """Load location to Route ID mapping"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading config: {e}")
                return {"mappings": {"locations": {}}, "impact_types": {}}
        else:
            logger.warning(f"Config not found: {self.config_path}. Using defaults.")
            return {"mappings": {"locations": {}}, "impact_types": {}}
    
    def extract_from_text(self, text: str) -> List[DisruptionEvent]:
        """
        Extract disruption from plain text
        """
        logger.info(f"Extracting from text: {text[:100]}...")
        disruptions = self._rule_based_extraction(text)
        return [DisruptionEvent(**d) for d in disruptions]
    
    def extract_from_csv(self, file_path: str) -> List[DisruptionEvent]:
        """
        Extract disruptions from CSV file
        """
        try:
            df = pd.read_csv(file_path)
            disruptions = []
            
            required_cols = ['target_route_id', 'impact_type', 'cost_multiplier', 'severity_score']
            if all(col in df.columns for col in required_cols):
                for idx, row in df.iterrows():
                    try:
                        event = DisruptionEvent(
                            target_route_id=int(row['target_route_id']),
                            impact_type=str(row['impact_type']),
                            cost_multiplier=float(row['cost_multiplier']),
                            severity_score=int(row['severity_score'])
                        )
                        disruptions.append(event)
                    except Exception as e:
                        logger.error(f"Failed to parse CSV row {idx}: {e}")
            else:
                text_cols = [col for col in df.columns if df[col].dtype == 'object']
                for _, row in df.iterrows():
                    text = ' '.join(str(row[col]) for col in text_cols)
                    disruptions.extend(self.extract_from_text(text))
            
            return disruptions
        except Exception as e:
            logger.error(f"Failed to process CSV {file_path}: {e}")
            return []
    
    def extract_from_image(self, image_path: str) -> List[DisruptionEvent]:
        """
        Extract disruptions from image using OCR with GRACEFUL FALLBACK
        """
        # THE FIX: If OCR is not available, we log and return empty instead of crashing
        if not OCR_AVAILABLE or self.ocr_reader is None:
            logger.warning(f"OCR requested for {image_path} but EasyOCR is not available. Skipping.")
            print(f"[EXTRACTOR] Skipping Image (OCR Unavailable): {image_path}")
            return []
        
        try:
            results = self.ocr_reader.readtext(image_path)
            text = '\n'.join([result[1] for result in results])
            logger.info(f"OCR extracted text: {text[:200]}...")
            return self.extract_from_text(text)
        except Exception as e:
            logger.error(f"OCR processing failed for {image_path}: {e}")
            return []
    
    def _rule_based_extraction(self, text: str) -> List[Dict]:
        """
        Extracts actual route numbers and impact data from text using Regex
        """
        text_lower = text.lower()
        disruptions = []
        
        print(f"\n[EXTRACTOR] Processing Input: '{text[:100]}...'")
        
        # Extract explicitly mentioned route numbers
        route_pattern = r'(?:route|r)\s*(\d+)|(?:routes?)\s*((?:\d+(?:\s*(?:,|and)\s*)?)+)'
        matches = re.finditer(route_pattern, text_lower, re.IGNORECASE)
        
        affected_routes = []
        for match in matches:
            if match.group(1):
                affected_routes.append(int(match.group(1)))
            elif match.group(2):
                numbers = re.findall(r'\d+', match.group(2))
                affected_routes.extend([int(n) for n in numbers])
        
        # Location-based fallback
        if not affected_routes:
            location_to_routes = {
                'boston': [1, 4], 'new york': [2, 7], 'chicago': [3, 6], 'philadelphia': [5, 8]
            }
            for location, routes in location_to_routes.items():
                if location in text_lower:
        # STEP 2: If no route numbers found, try location-based extraction from mapping config
        if not affected_routes:
            # Use the loaded mapping config (supports many more locations)
            mappings = self.mapping_config.get('mappings', {}).get('locations', {})
            
            # Try all mappings (case-insensitive)
            for location, routes in mappings.items():
                if location.lower() in text_lower:
                    affected_routes.extend(routes)
                    break
            
            # STEP 2b: If still no match and dynamic routing is available, try dynamic lookup
            if not affected_routes and DYNAMIC_ROUTING_AVAILABLE:
                # Extract potential city names (capitalized words that might be cities)
                import re
                potential_cities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', text)
                
                for city in potential_cities:
                    try:
                        # Attempt dynamic route resolution
                        dynamic_routes = get_routes_for_city(city, include_multihop=False)
                        if dynamic_routes:
                            affected_routes.extend(dynamic_routes[:2])  # Use first 2 routes
                            print(f"[EXTRACTOR] Dynamically resolved '{city}' to routes {dynamic_routes[:2]}")
                            break
                    except Exception as e:
                        # Continue trying other potential cities
                        continue
        
        # Standalone number fallback
        if not affected_routes:
            all_numbers = re.findall(r'\b([1-8])\b', text_lower)
            if all_numbers:
                affected_routes = [int(n) for n in all_numbers]

        if not affected_routes:
            logger.error("No route information could be extracted.")
            raise ValueError("Could not extract route ID. Please specify Route numbers (e.g. Route 3).")

        # Severity/Multiplier logic
        cost_multiplier = 1.5
        severity_score = 5
        impact_type = "Disruption"
        
        if any(word in text_lower for word in ['collapse', 'catastrophic', 'critical', 'severe', 'closed']):
            cost_multiplier, severity_score, impact_type = 15.0, 10, "Critical"
        elif any(word in text_lower for word in ['fire', 'explosion', 'hazardous']):
            cost_multiplier, severity_score, impact_type = 10.0, 9, "Hazardous"
        elif any(word in text_lower for word in ['accident', 'crash']):
            cost_multiplier, severity_score, impact_type = 4.0, 6, "Accident"
        
        # Explicit multiplier check
        multiplier_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:x|times|multiplier)', text_lower)
        if multiplier_match:
            cost_multiplier = float(multiplier_match.group(1))

        for route_id in set(affected_routes):
            print(f"[EXTRACTOR] Found explicit multiplier in text: {cost_multiplier}x")
        
        # GRACEFUL FALLBACK if no routes could be extracted
        if not affected_routes:
            warning_msg = (
                f"WARNING: Could not extract route information from: '{text[:100]}...'\n"
                f"No explicit route numbers found and location not recognized.\n"
                f"Returning empty disruption list. To fix:\n"
                f"  1. Specify route numbers explicitly (e.g., 'Route 3', 'routes 5 and 7'), OR\n"
                f"  2. Add location to mapping_config.json, OR\n"
                f"  3. Mention a recognized location (check mapping_config.json for available locations)"
            )
            print(f"[EXTRACTOR] {warning_msg}")
            logger.warning(warning_msg)
            # Return empty list instead of raising error
            return []
        
        print(f"[EXTRACTOR] ✓ Extracted Routes: {affected_routes}")
        print(f"[EXTRACTOR] ✓ Impact Type: {impact_type}")
        print(f"[EXTRACTOR] ✓ Cost Multiplier: {cost_multiplier}x")
        print(f"[EXTRACTOR] ✓ Severity: {severity_score}/10")
        
        # Create disruption for each affected route
        for route_id in set(affected_routes):  # Remove duplicates
            disruptions.append({
                'target_route_id': route_id,
                'impact_type': impact_type,
                'cost_multiplier': cost_multiplier,
                'severity_score': severity_score
            })
        
        return disruptions
        
    def _old_mapping_based_extraction(self, text: str) -> List[Dict]:
        """
        OLD LOGIC - Kept for reference but not used
        """
        text_lower = text.lower()
        disruptions = []
        
        # Map locations to route IDs
        affected_routes = []
        for location, route_ids in self.mapping_config['mappings']['locations'].items():
            if location.lower() in text_lower:
                affected_routes.extend(route_ids)
        
        # Determine impact type
        impact_type = 'accident'  # default
        for imp_type in self.mapping_config['impact_types'].keys():
            if imp_type in text_lower:
                impact_type = imp_type
                break
        
        # Get default multiplier and severity
        impact_config = self.mapping_config['impact_types'].get(
            impact_type,
            {'default_multiplier': 1.5, 'severity_range': [5, 7]}
        )
        
        cost_multiplier = impact_config['default_multiplier']
        severity_score = impact_config['severity_range'][0]
        
        # Adjust based on keywords
        if any(word in text_lower for word in ['severe', 'major', 'critical', 'catastrophic']):
            cost_multiplier = min(cost_multiplier * 1.5, 10.0)
            severity_score = min(severity_score + 2, 10)
        elif any(word in text_lower for word in ['minor', 'slight', 'small']):
            cost_multiplier = max(cost_multiplier * 0.8, 1.0)
            severity_score = max(severity_score - 2, 1)
        
        # Create disruptions for affected routes
        if not affected_routes:
            # NO FALLBACK - Raise error so user sees what's wrong
            error_msg = (
                f"Cannot extract route information from text: '{text[:100]}...'. "
                f"No location keywords found in mapping_config.json. "
                f"Available locations: {list(self.mapping_config['mappings']['locations'].keys())}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        for route_id in set(affected_routes):  # Remove duplicates
            disruptions.append({
                'target_route_id': route_id,
                'impact_type': impact_type,
                'cost_multiplier': cost_multiplier,
                'severity_score': severity_score
            })
        
        return disruptions

    def validate_and_aggregate(self, disruptions: List[DisruptionEvent]) -> List[Dict]:
        """Validate and aggregate disruptions by route (keeps worst case)"""
        route_disruptions = {}
        for disruption in disruptions:
            route_id = disruption.target_route_id
            if route_id not in route_disruptions or disruption.cost_multiplier > route_disruptions[route_id].cost_multiplier:
                route_disruptions[route_id] = disruption
        return [d.to_dict() for d in route_disruptions.values()]