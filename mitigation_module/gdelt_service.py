"""
GDELT Real-Time News Service
⚠️ ON HOLD - Build when instructed

Fetches latest 15-minute GKG updates from GDELT Project
Filters for supply chain disruption themes
"""

import requests
import zipfile
import io
import pandas as pd
from typing import List, Dict
import logging
from datetime import datetime
def enforce_https(url: str) -> str:
    """
    SECURITY FIX:
    Enforce HTTPS-only communication to prevent MITM attacks
    and ensure integrity of external GDELT data.
    """
    if not url.startswith("https://"):
        raise ValueError(f"Insecure URL blocked (HTTPS required): {url}")
    return url

logger = logging.getLogger(__name__)

# GDELT Master File List URL
GDELT_MASTER_URL = "https://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt"

# Themes to filter for supply chain disruptions
TARGET_THEMES = [
    'ENV_FLOOD',
    'STRIKE',
    'NATURAL_DISASTER',
    'TRANSPORTATION',
    'ENV_STORM',
    'PORT',
    'SHIPPING',
    'LOGISTICS'
]


class GDELTService:
    """
    Real-time news fetcher from GDELT Project
    
    ⚠️ STATUS: ON HOLD - DO NOT USE YET
    Build and activate when instructed
    """
    
    def __init__(self):
        """Initialize GDELT service"""
        self.master_url = GDELT_MASTER_URL
        self.last_fetch_time = None
        logger.warning("GDELTService initialized but ON HOLD. Do not use yet.")
    
    def fetch_latest_gkg(self) -> pd.DataFrame:
        """
        Fetch the latest GKG (Global Knowledge Graph) file
        
        Process:
        1. Ping Master File List URL
        2. Read last line to get latest gkg.csv.zip
        3. Download and extract in-memory
        4. Return DataFrame
        
        Returns:
            DataFrame with GKG data
            
        ⚠️ ON HOLD - NOT IMPLEMENTED YET
        """
        logger.warning("fetch_latest_gkg() called but ON HOLD. Returning empty DataFrame.")
        
        # TODO: Implement when instructed
        # Step 1: Fetch master list
        # response = requests.get(self.master_url)
        # lines = response.text.strip().split('\n')
        # last_line = lines[-1]
        
        # Step 2: Extract latest GKG URL
        # parts = last_line.split()
        # gkg_url = parts[2]  # Third column has the URL
        
        # Step 3: Download and extract
        # zip_response = requests.get(gkg_url)
        # with zipfile.ZipFile(io.BytesIO(zip_response.content)) as z:
        #     csv_name = z.namelist()[0]
        #     with z.open(csv_name) as f:
        #         df = pd.read_csv(f, sep='\t', low_memory=False)
        
        # return df
        
        return pd.DataFrame()
    
    def filter_disruption_themes(self, gkg_df: pd.DataFrame) -> List[Dict]:
        """
        Filter GKG data for supply chain disruption themes
        
        Args:
            gkg_df: GKG DataFrame
            
        Returns:
            List of relevant headlines with locations
            
        ⚠️ ON HOLD - NOT IMPLEMENTED YET
        """
        logger.warning("filter_disruption_themes() called but ON HOLD. Returning empty list.")
        
        # TODO: Implement when instructed
        # Filter for TARGET_THEMES in V2Themes column
        # Extract V2Locations and V1Themes
        # Return structured data for LLM mapping
        
        return []
    
    def get_disruptions_from_gdelt(self) -> List[Dict]:
        """
        Complete pipeline: Fetch → Filter → Extract
        
        Returns:
            List of disruption events ready for optimizer
            
        ⚠️ ON HOLD - NOT IMPLEMENTED YET
        """
        logger.warning(
            "get_disruptions_from_gdelt() called but ON HOLD. "
            "This feature will be activated when instructed."
        )
        
        # TODO: Complete pipeline when instructed
        # 1. Fetch latest GKG
        # 2. Filter themes
        # 3. Pass to DisruptionExtractor
        # 4. Map to Route IDs
        
        return []


# Placeholder for future use
def test_gdelt_connection() -> bool:
    """
    Test GDELT Master File List accessibility
    
    ⚠️ ON HOLD
    """
    try:
        secure_url = enforce_https(GDELT_MASTER_URL)
        response = requests.head(secure_url, timeout=5, verify=True)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"GDELT connection test failed: {e}")
        return False
