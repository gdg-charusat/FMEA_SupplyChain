"""
CityRiskChecker — importable class for India supply-chain risk analysis.

Loads a CSV once, detects columns via fuzzy matching, extracts Indian city
names using case-insensitive substring scanning, and returns structured
risk summaries with Indian-style INR formatting.
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Fixed exchange rate
USD_TO_INR = 83.0


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _format_indian_commas(n: int) -> str:
    """
    Format an integer with Indian-style comma grouping.

    Indian numbering: rightmost 3 digits, then groups of 2.
    Example: 123456 -> '1,23,456'
    """
    s = str(abs(n))
    if len(s) <= 3:
        return s if n >= 0 else f"-{s}"

    tail = s[-3:]          # last three digits
    head = s[:-3]          # remaining digits
    # group the head in pairs from the right
    parts: List[str] = []
    while len(head) > 2:
        parts.append(head[-2:])
        head = head[:-2]
    parts.append(head)     # leftover 1-2 digits
    parts.reverse()

    result = ",".join(parts) + "," + tail
    return result if n >= 0 else f"-{result}"


def _fuzzy_find(columns: List[str], keywords: List[str]) -> Optional[str]:
    """Return the first column whose lower-cased name contains any keyword."""
    lower_map = {c.lower().strip(): c for c in columns}
    for kw in keywords:
        for lc, orig in lower_map.items():
            if kw in lc:
                return orig
    return None


class CityRiskChecker:
    """Analyse city-level supply-chain risk from a CSV dataset."""

    INDIAN_CITIES: List[str] = [
        "Mumbai", "Delhi", "Chennai", "Pune", "Bangalore",
        "Hyderabad", "Ahmedabad", "Kolkata", "Surat", "Jaipur",
        "Vadodara", "Nagpur", "Coimbatore", "Indore", "Bhopal",
    ]

    _OUTPUT_COLS = [
        "city", "avg_severity", "total_failures", "risk_level", "cost_inr",
    ]

    def __init__(self, dataset_path: str) -> None:
        """Load the CSV once and detect relevant columns."""
        self.dataset_path = dataset_path
        self.df: Optional[pd.DataFrame] = None
        self.city_col: Optional[str] = None
        self.risk_col: Optional[str] = None
        self.cost_col: Optional[str] = None
        self._load()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _load(self) -> None:
        """Read CSV and detect city / risk / cost columns."""
        try:
            self.df = pd.read_csv(self.dataset_path, encoding="latin1")
            self.df.columns = [c.strip() for c in self.df.columns]
        except Exception as exc:
            logger.warning("Cannot read %s: %s", self.dataset_path, exc)
            return

        cols = self.df.columns.tolist()

        # city column: contains "city" / "location" / "site" / "plant"
        self.city_col = _fuzzy_find(cols, ["city", "location", "site", "plant"])

        # risk column: prefer exact then fuzzy
        self.risk_col = self._detect_risk_col(cols)

        # cost column (optional): contains "cost" / "usd" / "loss"
        self.cost_col = _fuzzy_find(cols, ["cost", "usd", "loss"])

        # Debug (logged, not printed)
        # detected city_col={self.city_col}, risk_col={self.risk_col}, cost_col={self.cost_col}

    @staticmethod
    def _detect_risk_col(cols: List[str]) -> Optional[str]:
        """Prefer exact match among known names, else fuzzy on risk/severity."""
        lower_map = {c.lower().strip(): c for c in cols}
        for exact in ("rpn", "risk_priority_number", "risk_score", "severity"):
            if exact in lower_map:
                return lower_map[exact]
        return _fuzzy_find(cols, ["rpn", "risk", "severity"])

    def _extract_indian_city(self, value) -> Optional[str]:
        """
        Extract an Indian city from *value* using case-insensitive substring
        scanning.  Handles formats like:
            "Mumbai"  /  "mumbai"  /  "Mumbai, India"  /
            "IN-MUMBAI-PLANT"  /  "Plant: Delhi NCR"
        """
        if pd.isna(value):
            return None
        raw = str(value).strip()
        # if contains comma, take the part before the comma first
        if "," in raw:
            raw = raw.split(",")[0].strip()
        lowered = raw.lower()
        for city in self.INDIAN_CITIES:
            if city.lower() in lowered:
                return city
        return None

    def _build_india_column(self) -> pd.DataFrame:
        """
        Add an '_india_city' column to self.df using substring extraction
        and return filtered rows where a city was detected.
        """
        if self.df is None or self.city_col is None:
            return pd.DataFrame()

        self.df["_india_city"] = self.df[self.city_col].map(
            self._extract_indian_city
        )
        return self.df[self.df["_india_city"].notna()].copy()

    @staticmethod
    def _empty_summary() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "city", "avg_severity", "total_failures",
                "risk_level", "cost_inr",
            ]
        )

    @staticmethod
    def _risk_level(avg: float) -> str:
        if avg >= 200:
            return "High"
        if avg >= 100:
            return "Medium"
        return "Low"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @staticmethod
    def format_cost_inr(
        cost_usd: float,
        usd_to_inr: float = USD_TO_INR,
    ) -> str:
        """
        Convert USD to INR and format with Indian-style commas.

        Args:
            cost_usd: Amount in USD.
            usd_to_inr: Exchange rate (default 83.0).

        Returns:
            e.g. '₹1,23,456'
        """
        inr = int(float(cost_usd) * usd_to_inr)
        return f"₹{_format_indian_commas(inr)}"

    def get_city_risk_summary(self) -> pd.DataFrame:
        """
        Per-city risk summary for Indian cities.

        Returns DataFrame with columns:
            city | avg_severity | total_failures | risk_level | cost_inr
        Sorted by avg_severity descending. Empty DF if no data.
        """
        indian = self._build_india_column()
        if indian.empty or not self.risk_col:
            return self._empty_summary()

        rows: List[Dict] = []
        for city_name, grp in indian.groupby("_india_city"):
            rpn_vals = pd.to_numeric(grp[self.risk_col], errors="coerce")
            avg_sev = rpn_vals.mean()
            if np.isnan(avg_sev):
                avg_sev = 0.0

            cost_inr_str = "₹0"
            if self.cost_col and self.cost_col in grp.columns:
                mean_cost = pd.to_numeric(
                    grp[self.cost_col], errors="coerce"
                ).mean()
                if not np.isnan(mean_cost):
                    cost_inr_str = self.format_cost_inr(mean_cost)

            rows.append({
                "city": city_name,
                "avg_severity": round(float(avg_sev), 2),
                "total_failures": len(grp),
                "risk_level": self._risk_level(avg_sev),
                "cost_inr": cost_inr_str,
            })

        if not rows:
            return self._empty_summary()

        return (
            pd.DataFrame(rows, columns=self._OUTPUT_COLS)
            .sort_values("avg_severity", ascending=False)
            .reset_index(drop=True)
        )

    def get_highest_risk_city(self) -> Dict:
        """
        City with the highest average severity/RPN.

        Returns:
            {"city": <str or None>, "rpn": <float>}
        """
        summary = self.get_city_risk_summary()
        if summary.empty:
            return {"city": None, "rpn": 0}
        top = summary.iloc[0]  # already sorted desc
        return {"city": top["city"], "rpn": float(top["avg_severity"])}


if __name__ == "__main__":
    print("CityRiskChecker module loaded successfully.")