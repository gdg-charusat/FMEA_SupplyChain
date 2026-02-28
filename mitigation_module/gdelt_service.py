"""
GDELT Real-Time News Service
Fetches latest 15-minute GKG updates from GDELT Project
Filters for supply chain disruption themes
"""

import requests
import zipfile
import io
import pandas as pd
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime, timedelta, UTC

logger = logging.getLogger(__name__)

# GDELT Master File List URL
GDELT_MASTER_URL = "http://data.gdeltproject.org/gdeltv2/masterfilelist-translation.txt"

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
    
    Live news fetcher from GDELT Project with graceful fallback semantics.
    """

    def __init__(
        self,
        master_url: str = GDELT_MASTER_URL,
        request_timeout: int = 5,
        max_retries: int = 2,
        cache_ttl_seconds: int = 900,
        session: Optional[requests.Session] = None,
    ):
        """Initialize GDELT service."""
        self.master_url = master_url
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.cache_ttl_seconds = cache_ttl_seconds
        self.session = session or requests.Session()

        self.last_fetch_time: Optional[datetime] = None
        self._cached_gkg_df: Optional[pd.DataFrame] = None
        self._cached_disruptions: Optional[List[Dict[str, Any]]] = None
        self._cache_expires_at: Optional[datetime] = None

    @staticmethod
    def _to_bool_env(value: str) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _is_cache_valid(self) -> bool:
        return self._cache_expires_at is not None and datetime.now(UTC) < self._cache_expires_at

    def _set_cache_expiry(self) -> None:
        self._cache_expires_at = datetime.now(UTC) + timedelta(seconds=self.cache_ttl_seconds)

    @staticmethod
    def _extract_latest_gkg_url(master_text: str) -> Optional[str]:
        """Extract latest GKG zip URL from GDELT masterfile list."""
        lines = [line.strip() for line in master_text.splitlines() if line.strip()]
        for line in reversed(lines):
            parts = line.split()
            if len(parts) < 3:
                continue
            candidate = parts[2]
            if "gkg" in candidate.lower() and candidate.lower().endswith(".zip"):
                return candidate
        return None

    @staticmethod
    def _get_column(df: pd.DataFrame, candidates: List[str], fallback_index: Optional[int] = None) -> pd.Series:
        for column_name in candidates:
            if column_name in df.columns:
                return df[column_name]
        if fallback_index is not None and fallback_index < len(df.columns):
            return df.iloc[:, fallback_index]
        return pd.Series(dtype="object")

    @staticmethod
    def _extract_locations(v2_locations: str) -> List[str]:
        """Parse V2Locations format into a list of city/location names."""
        if not isinstance(v2_locations, str) or not v2_locations.strip():
            return []

        locations: List[str] = []
        entries = [entry.strip() for entry in v2_locations.split(";") if entry.strip()]
        for entry in entries:
            parts = entry.split("#")
            if len(parts) >= 2 and parts[1].strip():
                locations.append(parts[1].strip())
        return locations

    @staticmethod
    def _compute_multiplier(theme_text: str) -> float:
        theme_text = (theme_text or "").upper()
        if any(token in theme_text for token in ["NATURAL_DISASTER", "ENV_FLOOD", "ENV_STORM"]):
            return 20.0
        if any(token in theme_text for token in ["TRANSPORTATION", "PORT", "SHIPPING", "LOGISTICS"]):
            return 10.0
        if "STRIKE" in theme_text:
            return 5.0
        return 2.0

    def _http_get_with_retry(self, url: str) -> requests.Response:
        last_error: Optional[Exception] = None
        attempts = max(self.max_retries, 1)
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.get(url, timeout=self.request_timeout)
                response.raise_for_status()
                return response
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("GDELT request failed (%s/%s): %s", attempt, attempts, exc)

        raise RuntimeError(f"Failed to fetch URL after {attempts} attempt(s): {url}") from last_error

    def fetch_latest_gkg(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch the latest GKG (Global Knowledge Graph) file
        
        Process:
        1. Ping Master File List URL
        2. Read last line to get latest gkg.csv.zip
        3. Download and extract in-memory
        4. Return DataFrame
        
        Returns:
            DataFrame with GKG data
        """
        if not force_refresh and self._is_cache_valid() and self._cached_gkg_df is not None:
            return self._cached_gkg_df.copy()

        master_response = self._http_get_with_retry(self.master_url)
        gkg_url = self._extract_latest_gkg_url(master_response.text)
        if not gkg_url:
            raise RuntimeError("Could not find latest GKG zip URL in GDELT master file list")

        zip_response = self._http_get_with_retry(gkg_url)
        with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zip_file:
            members = zip_file.namelist()
            if not members:
                raise RuntimeError("Downloaded GKG zip archive is empty")

            csv_member = next((name for name in members if name.lower().endswith((".csv", ".txt"))), members[0])
            with zip_file.open(csv_member) as file_handle:
                try:
                    df = pd.read_csv(file_handle, sep='\t', low_memory=False)
                except Exception:
                    file_handle.seek(0)
                    df = pd.read_csv(file_handle, sep='\t', low_memory=False, header=None)

        self.last_fetch_time = datetime.now(UTC)
        self._cached_gkg_df = df.copy()
        self._set_cache_expiry()
        return df
    
    def filter_disruption_themes(self, gkg_df: pd.DataFrame) -> List[Dict]:
        """
        Filter GKG data for supply chain disruption themes
        
        Args:
            gkg_df: GKG DataFrame
            
        Returns:
            List of relevant disruption records
        """
        if gkg_df is None or gkg_df.empty:
            return []

        themes_series = self._get_column(gkg_df, ["V2Themes", "Themes"], fallback_index=8).fillna("")
        locations_series = self._get_column(gkg_df, ["V2Locations", "Locations"], fallback_index=10).fillna("")
        source_series = self._get_column(gkg_df, ["DocumentIdentifier", "SOURCEURL", "sourceurl"], fallback_index=4).fillna("")
        date_series = self._get_column(gkg_df, ["DATE", "Date"], fallback_index=1).fillna("")

        target_tokens = [theme.upper() for theme in TARGET_THEMES]
        disruptions: List[Dict[str, Any]] = []

        for idx in range(len(gkg_df)):
            theme_text = str(themes_series.iloc[idx])
            if not theme_text:
                continue

            upper_theme = theme_text.upper()
            matched = [token for token in target_tokens if token in upper_theme]
            if not matched:
                continue

            locations = self._extract_locations(str(locations_series.iloc[idx]))
            multiplier = self._compute_multiplier(upper_theme)

            disruptions.append(
                {
                    "themes": matched,
                    "raw_themes": theme_text,
                    "locations": locations,
                    "multiplier": multiplier,
                    "reason": f"{matched[0]} signal from GDELT",
                    "source": "gdelt",
                    "article_url": str(source_series.iloc[idx]),
                    "event_time": str(date_series.iloc[idx]),
                }
            )

        return disruptions

    def get_disruptions_from_gdelt(self, force_refresh: bool = False) -> List[Dict]:
        """
        Complete pipeline: Fetch → Filter → Extract
        
        Returns:
            List of disruption events ready for optimizer
        """
        if not force_refresh and self._is_cache_valid() and self._cached_disruptions is not None:
            return list(self._cached_disruptions)

        gkg_df = self.fetch_latest_gkg(force_refresh=force_refresh)
        disruptions = self.filter_disruption_themes(gkg_df)

        self._cached_disruptions = list(disruptions)
        self._set_cache_expiry()
        return disruptions

    def get_city_risk(self, city_name: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Return the highest-severity risk for a specific city based on latest GDELT events.
        """
        if not city_name:
            return None

        disruptions = self.get_disruptions_from_gdelt(force_refresh=force_refresh)
        city_lower = city_name.lower()

        matched_events = []
        for event in disruptions:
            locations = event.get("locations", []) or []
            if any(city_lower in str(location).lower() for location in locations):
                matched_events.append(event)

        if not matched_events:
            return None

        top_event = max(matched_events, key=lambda item: float(item.get("multiplier", 1.0)))
        return {
            "city": city_name,
            "multiplier": float(top_event.get("multiplier", 1.0)),
            "reason": str(top_event.get("reason", "GDELT disruption detected")),
            "source": "gdelt",
            "themes": top_event.get("themes", []),
            "article_url": top_event.get("article_url"),
        }


def test_gdelt_connection() -> bool:
    """
    Test GDELT Master File List accessibility
    
    Check if GDELT master endpoint is reachable.
    """
    try:
        response = requests.head(GDELT_MASTER_URL, timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"GDELT connection test failed: {e}")
        return False
