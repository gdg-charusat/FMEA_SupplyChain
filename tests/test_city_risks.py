"""
Pytest tests for CityRiskChecker (check_city_risks module).
Run with: pytest tests/test_city_risks.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_city_risks import CityRiskChecker


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def indian_csv(tmp_path: Path) -> str:
    """Small CSV with two Indian cities and one non-Indian city."""
    df = pd.DataFrame({
        "City": ["Mumbai", "Mumbai", "Pune", "Boston"],
        "RPN": [250, 150, 90, 300],
        "Cost_USD": [1000, 2000, 500, 4000],
    })
    path = tmp_path / "indian.csv"
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def no_indian_csv(tmp_path: Path) -> str:
    """CSV with zero Indian cities."""
    df = pd.DataFrame({
        "City": ["Boston", "Chicago"],
        "RPN": [100, 200],
        "Cost_USD": [500, 600],
    })
    path = tmp_path / "no_indian.csv"
    df.to_csv(path, index=False)
    return str(path)


# ------------------------------------------------------------------ #
# 1) INDIAN_CITIES list completeness
# ------------------------------------------------------------------ #

class TestIndianCitiesList:
    EXPECTED = {
        "Mumbai", "Delhi", "Chennai", "Pune", "Bangalore",
        "Hyderabad", "Ahmedabad", "Kolkata", "Surat", "Jaipur",
        "Vadodara", "Nagpur", "Coimbatore", "Indore", "Bhopal",
    }

    def test_all_15_cities_present(self) -> None:
        assert set(CityRiskChecker.INDIAN_CITIES) == self.EXPECTED

    def test_count(self) -> None:
        assert len(CityRiskChecker.INDIAN_CITIES) == 15


# ------------------------------------------------------------------ #
# 2) INR formatting with Indian commas
# ------------------------------------------------------------------ #

class TestFormatCostINR:

    def test_indian_commas(self, indian_csv: str) -> None:
        """format_cost_inr(123456, usd_to_inr=1) must produce ₹1,23,456."""
        checker = CityRiskChecker(indian_csv)
        assert checker.format_cost_inr(123456, usd_to_inr=1) == "₹1,23,456"

    def test_small_number(self, indian_csv: str) -> None:
        checker = CityRiskChecker(indian_csv)
        assert checker.format_cost_inr(100, usd_to_inr=1) == "₹100"

    def test_default_rate(self, indian_csv: str) -> None:
        checker = CityRiskChecker(indian_csv)
        result = checker.format_cost_inr(1000)  # 1000 * 83 = 83000
        assert "83,000" in result
        assert result.startswith("₹")

    def test_zero(self, indian_csv: str) -> None:
        checker = CityRiskChecker(indian_csv)
        assert checker.format_cost_inr(0) == "₹0"


# ------------------------------------------------------------------ #
# 3) get_highest_risk_city
# ------------------------------------------------------------------ #

class TestHighestRiskCity:

    def test_returns_dict_with_keys(self, indian_csv: str) -> None:
        result = CityRiskChecker(indian_csv).get_highest_risk_city()
        assert isinstance(result, dict)
        assert "city" in result
        assert "rpn" in result

    def test_top_city_is_mumbai(self, indian_csv: str) -> None:
        """Mumbai avg = (250+150)/2 = 200, Pune = 90 → Mumbai wins."""
        result = CityRiskChecker(indian_csv).get_highest_risk_city()
        assert result["city"] == "Mumbai"
        assert result["rpn"] == 200.0


# ------------------------------------------------------------------ #
# 4) Graceful handling — no Indian city rows
# ------------------------------------------------------------------ #

class TestGracefulHandling:

    def test_empty_summary_columns(self, no_indian_csv: str) -> None:
        checker = CityRiskChecker(no_indian_csv)
        summary = checker.get_city_risk_summary()
        assert summary.empty
        assert list(summary.columns) == [
            "city", "avg_severity", "total_failures", "risk_level", "cost_inr",
        ]

    def test_highest_risk_none(self, no_indian_csv: str) -> None:
        result = CityRiskChecker(no_indian_csv).get_highest_risk_city()
        assert result == {"city": None, "rpn": 0}

    def test_missing_file(self) -> None:
        checker = CityRiskChecker("nonexistent_file.csv")
        assert checker.get_city_risk_summary().empty
        assert checker.get_highest_risk_city() == {"city": None, "rpn": 0}


# ------------------------------------------------------------------ #
# 5) Substring-based city extraction
# ------------------------------------------------------------------ #

class TestSubstringCityExtraction:

    def test_comma_separated(self, tmp_path: Path) -> None:
        """'Mumbai, India' should match Mumbai."""
        df = pd.DataFrame({
            "City": ["Mumbai, India", "Delhi, IN"],
            "RPN": [150, 200],
        })
        path = tmp_path / "comma.csv"
        df.to_csv(path, index=False)
        summary = CityRiskChecker(str(path)).get_city_risk_summary()
        assert set(summary["city"]) == {"Mumbai", "Delhi"}

    def test_embedded_city_name(self, tmp_path: Path) -> None:
        """'IN-MUMBAI-PLANT' should match Mumbai."""
        df = pd.DataFrame({
            "Location": ["IN-MUMBAI-PLANT", "Plant: Delhi NCR"],
            "Severity": [180, 220],
        })
        path = tmp_path / "embedded.csv"
        df.to_csv(path, index=False)
        summary = CityRiskChecker(str(path)).get_city_risk_summary()
        assert "Mumbai" in summary["city"].values
        assert "Delhi" in summary["city"].values

    def test_case_insensitive(self, tmp_path: Path) -> None:
        """'mumbai' (lowercase) should match Mumbai."""
        df = pd.DataFrame({
            "City": ["mumbai", "PUNE"],
            "RPN": [100, 200],
        })
        path = tmp_path / "case.csv"
        df.to_csv(path, index=False)
        summary = CityRiskChecker(str(path)).get_city_risk_summary()
        assert set(summary["city"]) == {"Mumbai", "Pune"}