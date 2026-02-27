"""
Disruption Information Extractor
Uses Claude 3.5 Sonnet for multimodal input processing and JSON extraction
Handles: Text, CSV, Images (OCR), Emails, PDFs
"""

import json
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, validator
import pandas as pd

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
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


class DisruptionEvent(BaseModel):
    """
    Validated disruption event model
    Ensures clean output regardless of messy input
    """
    target_route_id: int = Field(..., ge=1, le=10, description="Route ID affected (1-10)")
    impact_type: str = Field(..., description="Type of disruption (flood, strike, accident, etc.)")
    cost_multiplier: float = Field(..., ge=1.0, le=10.0, description="Cost multiplication factor")
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
    Uses Claude 3.5 Sonnet (via API) or rule-based fallback
    """
    
    def __init__(self, config_path: str = "mitigation_module/mapping_config.json"):
        """
        Initialize extractor with location mapping
        
        Args:
            config_path: Path to mapping configuration JSON
        """
        self.config_path = Path(config_path)
        self.mapping_config = self._load_mapping_config()
        self.ocr_reader = None
        
        if OCR_AVAILABLE:
            self.ocr_reader = easyocr.Reader(['en'], gpu=False)
    
    def _load_mapping_config(self) -> Dict:
        """Load location to Route ID mapping"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Config not found: {self.config_path}. Using defaults.")
            return {"mappings": {"locations": {}}, "impact_types": {}}
    
    def extract_from_text(self, text: str) -> List[DisruptionEvent]:
        """
        Extract disruption from plain text
        
        Args:
            text: Raw text input
            
        Returns:
            List of validated disruption events
        """
        logger.info(f"Extracting from text: {text[:100]}...")
        
        # Rule-based extraction (fallback)
        disruptions = self._rule_based_extraction(text)
        
        # TODO: Add Claude 3.5 Sonnet API call when API key is provided
        # disruptions = self._llm_extraction(text)
        
        return [DisruptionEvent(**d) for d in disruptions]
    
    def extract_from_csv(self, file_path: str) -> List[DisruptionEvent]:
        """
        Extract disruptions from CSV file
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of validated disruption events
        """
        df = pd.read_csv(file_path)
        disruptions = []
        
        # Check if CSV has required columns
        required_cols = ['target_route_id', 'impact_type', 'cost_multiplier', 'severity_score']
        if all(col in df.columns for col in required_cols):
            # Direct mapping from CSV
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
                    error_msg = f"Failed to parse CSV row {idx}: {row.to_dict()}. Error: {e}"
                    logger.error(error_msg)
                    raise ValueError(error_msg) from e
        else:
            # Extract from text columns
            text_cols = [col for col in df.columns if df[col].dtype == 'object']
            for _, row in df.iterrows():
                text = ' '.join(str(row[col]) for col in text_cols)
                disruptions.extend(self.extract_from_text(text))
        
        return disruptions
    
    def extract_from_image(self, image_path: str) -> List[DisruptionEvent]:
        """
        Extract disruptions from image using OCR
        
        Args:
            image_path: Path to image file (PNG, JPG)
            
        Returns:
            List of validated disruption events
        """
        if not OCR_AVAILABLE or not self.ocr_reader:
            raise RuntimeError("OCR not available. Install: pip install easyocr")
        
        # Extract text using OCR
        results = self.ocr_reader.readtext(image_path)
        text = '\n'.join([result[1] for result in results])
        
        logger.info(f"OCR extracted text: {text[:200]}...")
        
        # Process extracted text
        return self.extract_from_text(text)
    
    def _rule_based_extraction(self, text: str) -> List[Dict]:
        """
        TRULY DYNAMIC extraction - Extracts actual route numbers from user text
        NO PREDEFINED SCENARIOS - Responds to what user actually writes
        """
        import re
        
        text_lower = text.lower()
        disruptions = []
        
        print(f"\n[EXTRACTOR] Processing Input: '{text[:100]}...'")
        
        # STEP 1: Extract explicitly mentioned route numbers from text
        # Matches: "Route 3", "route 5", "R3", "routes 2 and 7", "routes 2, 5, and 8"
        route_pattern = r'(?:route|r)\s*(\d+)|(?:routes?)\s*((?:\d+(?:\s*(?:,|and)\s*)?)+)'
        matches = re.finditer(route_pattern, text_lower, re.IGNORECASE)
        
        affected_routes = []
        for match in matches:
            if match.group(1):  # Single route: "Route 3"
                affected_routes.append(int(match.group(1)))
            elif match.group(2):  # Multiple routes: "routes 2, 5, and 8"
                # Extract all numbers from the matched text
                numbers = re.findall(r'\d+', match.group(2))
                affected_routes.extend([int(n) for n in numbers])
        
        # STEP 2: If no route numbers found, try location-based extraction from mapping config
        if not affected_routes:
            # Use the loaded mapping config (supports many more locations)
            mappings = self.mapping_config.get('mappings', {}).get('locations', {})
            
            # Try all mappings (case-insensitive)
            for location, routes in mappings.items():
                if location.lower() in text_lower:
                    affected_routes.extend(routes)
                    print(f"[EXTRACTOR] No explicit routes found, mapped '{location}' to routes {routes}")
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
        
        # STEP 3: If still no routes, extract from specific number patterns
        if not affected_routes:
            # Look for any standalone numbers that might be route IDs (1-8)
            all_numbers = re.findall(r'\b([1-8])\b', text_lower)
            if all_numbers:
                affected_routes = [int(n) for n in all_numbers]
                print(f"[EXTRACTOR] Extracted standalone numbers as routes: {affected_routes}")
        
        # STEP 4: Determine severity/multiplier from keywords (DYNAMIC based on text)
        cost_multiplier = 1.5  # Base default
        severity_score = 5
        impact_type = "Disruption"
        
        # High severity keywords
        if any(word in text_lower for word in ['collapse', 'catastrophic', 'critical', 'severe', 'major', 'closed', 'shutdown']):
            cost_multiplier = 15.0
            severity_score = 10
            impact_type = "Critical"
        elif any(word in text_lower for word in ['fire', 'explosion', 'toxic', 'chemical', 'spill']):
            cost_multiplier = 10.0
            severity_score = 9
            impact_type = "Hazardous"
        elif any(word in text_lower for word in ['strike', 'protest', 'blockade']):
            cost_multiplier = 6.0
            severity_score = 7
            impact_type = "Labor/Civil"
        elif any(word in text_lower for word in ['accident', 'crash', 'collision']):
            cost_multiplier = 4.0
            severity_score = 6
            impact_type = "Accident"
        elif any(word in text_lower for word in ['delay', 'slow', 'congestion', 'traffic']):
            cost_multiplier = 2.0
            severity_score = 4
            impact_type = "Delay"
        
        # Extract explicit multiplier if mentioned (e.g., "10x cost" or "cost increased by 5")
        multiplier_pattern = r'(\d+(?:\.\d+)?)\s*(?:x|times|multiplier)'
        multiplier_match = re.search(multiplier_pattern, text_lower)
        if multiplier_match:
            cost_multiplier = float(multiplier_match.group(1))
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
        
        logger.info(f"Extracted {len(disruptions)} disruptions: {disruptions}")
        return disruptions
    
    def extract_from_news(self, news_df: pd.DataFrame, 
                         categories: List[str] = ['BUSINESS', 'WORLD NEWS']) -> List[DisruptionEvent]:
        """
        Extract disruptions from historical news dataset
        
        Args:
            news_df: DataFrame with 'category', 'headline', 'short_description'
            categories: News categories to filter
            
        Returns:
            List of validated disruption events
        """
        # Filter relevant categories
        filtered = news_df[news_df['category'].isin(categories)]
        
        disruptions = []
        for _, row in filtered.head(50).iterrows():  # Limit to 50 articles
            text = f"{row.get('headline', '')} {row.get('short_description', '')}"
            
            # Check for transportation/logistics keywords
            if any(keyword in text.lower() for keyword in [
                'transport', 'logistics', 'supply', 'shipping', 'port',
                'highway', 'road', 'traffic', 'strike', 'delay'
            ]):
                disruptions.extend(self.extract_from_text(text))
        
        return disruptions
    
    def validate_and_aggregate(self, disruptions: List[DisruptionEvent]) -> List[Dict]:
        """
        Validate and aggregate disruptions by route
        If multiple disruptions affect same route, use worst case
        
        Args:
            disruptions: List of disruption events
            
        Returns:
            Aggregated disruptions (one per route)
        """
        route_disruptions = {}
        
        for disruption in disruptions:
            route_id = disruption.target_route_id
            
            if route_id not in route_disruptions:
                route_disruptions[route_id] = disruption
            else:
                # Keep disruption with higher cost multiplier
                existing = route_disruptions[route_id]
                if disruption.cost_multiplier > existing.cost_multiplier:
                    route_disruptions[route_id] = disruption
        
        return [d.to_dict() for d in route_disruptions.values()]
