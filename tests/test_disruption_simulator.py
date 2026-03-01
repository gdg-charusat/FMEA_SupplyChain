"""
Tests for src/disruption_simulator.py

Coverage:
  TestDownstreamComponents  - dependency graph and component routing
  TestScoreCapping          - escalation rules and MAX_SCORE cap
  TestDeltaColumn           - Disruption_Delta_RPN accuracy
  TestExcelExport           - two-sheet workbook structure
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Make sure the src directory is importable during pytest runs
_SRC_DIR = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(_SRC_DIR))

from disruption_simulator import DisruptionSimulator  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

DATASET_PATH = Path(__file__).parent.parent / "Dataset_AI_Supply_Optimization.csv"


@pytest.fixture(scope="module")
def sim() -> DisruptionSimulator:
    """Module-scoped simulator (dataset is large; load only once)."""
    if not DATASET_PATH.exists():
        pytest.skip(
            f"Supply chain dataset not found at {DATASET_PATH}; skipping tests."
        )
    return DisruptionSimulator(str(DATASET_PATH))


@pytest.fixture()
def sample_fmea() -> pd.DataFrame:
    """A minimal six-row FMEA DataFrame with Title-Case column names."""
    return pd.DataFrame(
        {
            "Component": [
                "Engine",
                "Brake",
                "Fuel Pump",
                "Transmission",
                "Exhaust",
                "Cooling",
            ],
            "Failure Mode": [
                "Overheating",
                "Brake failure",
                "Fuel leak",
                "Gear slip",
                "Emission spike",
                "Coolant loss",
            ],
            "Effect": ["Shutdown"] * 6,
            "Severity":   [5, 7, 6, 4, 5, 6],
            "Occurrence": [4, 5, 6, 3, 4, 5],
            "Detection":  [3, 4, 5, 2, 3, 4],
            "Rpn":        [60, 140, 180, 24, 60, 120],
            "Action Priority": ["Medium"] * 6,
            "Recommended Action": ["Review"] * 6,
        }
    )


# ===========================================================================
# TestDownstreamComponents
# ===========================================================================


class TestDownstreamComponents:
    """Verify that get_downstream_components returns correct, disjoint index sets."""

    def test_level1_indices_are_nonempty_for_valid_route(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """A valid numeric Route ID must produce at least one Level-1 index."""
        route_id = str(sim._all_routes[0])
        l1, _ = sim.get_downstream_components(sample_fmea, route_id)
        assert len(l1) > 0, f"Expected Level-1 indices for route {route_id}"

    def test_level1_and_level2_are_disjoint(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Level-1 and Level-2 index sets must not overlap."""
        route_id = str(sim._all_routes[0])
        l1, l2 = sim.get_downstream_components(sample_fmea, route_id)
        assert set(l1).isdisjoint(set(l2)), "Level-1 and Level-2 indices overlap"

    def test_indices_in_valid_range(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Every returned index must be a valid row index for the FMEA DataFrame."""
        route_id = str(sim._all_routes[0])
        l1, l2 = sim.get_downstream_components(sample_fmea, route_id)
        n = len(sample_fmea)
        for idx in l1 + l2:
            assert 0 <= idx < n, f"Index {idx} out of range [0, {n})"

    def test_category_node_returns_indices(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """A Product Category node name must resolve to component indices."""
        known_category = next(iter(sim._category_to_routes))
        l1, l2 = sim.get_downstream_components(sample_fmea, known_category)
        assert len(l1) + len(l2) > 0, (
            f"No components found for category '{known_category}'"
        )

    def test_unknown_node_returns_all_level2(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """An unrecognised node must return an empty Level-1 list and all rows as
        Level-2 (conservative treatment)."""
        l1, l2 = sim.get_downstream_components(sample_fmea, "TOTALLY_UNKNOWN_NODE_XYZ")
        assert l1 == [], "Expected empty Level-1 for unknown node"
        assert len(l2) == len(sample_fmea), (
            "Expected all rows as Level-2 for unknown node"
        )

    def test_route_prefix_formats_parsed(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Both 'Route_5' and '5' forms should resolve to the same route."""
        first_route = sim._all_routes[0]
        l1_plain, l2_plain = sim.get_downstream_components(
            sample_fmea, str(first_route)
        )
        l1_prefix, l2_prefix = sim.get_downstream_components(
            sample_fmea, f"Route_{first_route}"
        )
        assert l1_plain == l1_prefix, (
            "Plain and prefixed route IDs should give same Level-1 components"
        )
        assert l2_plain == l2_prefix, (
            "Plain and prefixed route IDs should give same Level-2 components"
        )


# ===========================================================================
# TestScoreCapping
# ===========================================================================


class TestScoreCapping:
    """Verify that escalation is applied correctly and scores never exceed 10."""

    def test_no_score_exceeds_max(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Severity, Occurrence, and Detection must not exceed MAX_SCORE after
        escalation."""
        route_id = str(sim._all_routes[0])
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        for col in ("Severity", "Occurrence", "Detection"):
            assert result[col].max() <= DisruptionSimulator.MAX_SCORE, (
                f"Column '{col}' exceeds MAX_SCORE={DisruptionSimulator.MAX_SCORE}"
            )

    def test_level1_occurrence_increases(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Level-1 components must have Occurrence >= their original value."""
        route_id = str(sim._all_routes[0])
        l1, _ = sim.get_downstream_components(sample_fmea, route_id)
        if not l1:
            pytest.skip("No Level-1 components with this FMEA size")
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        for idx in l1:
            orig = sample_fmea.loc[idx, "Occurrence"]
            new = result.loc[idx, "Occurrence"]
            assert new >= orig, (
                f"Row {idx}: Occurrence decreased ({orig} -> {new})"
            )

    def test_level1_severity_increases(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Level-1 components must have Severity >= their original value."""
        route_id = str(sim._all_routes[0])
        l1, _ = sim.get_downstream_components(sample_fmea, route_id)
        if not l1:
            pytest.skip("No Level-1 components with this FMEA size")
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        for idx in l1:
            orig = sample_fmea.loc[idx, "Severity"]
            new = result.loc[idx, "Severity"]
            assert new >= orig, (
                f"Row {idx}: Severity decreased ({orig} -> {new})"
            )

    def test_unaffected_rows_stay_the_same(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Rows not in Level-1 or Level-2 must be identical to the original."""
        route_id = str(sim._all_routes[0])
        l1, l2 = sim.get_downstream_components(sample_fmea, route_id)
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        affected = set(l1 + l2)
        for idx in range(len(sample_fmea)):
            if idx not in affected:
                for col in ("Severity", "Occurrence", "Detection"):
                    assert sample_fmea.loc[idx, col] == result.loc[idx, col], (
                        f"Unaffected row {idx}, column '{col}' changed unexpectedly"
                    )

    def test_original_fmea_not_mutated(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """apply_risk_escalation must not modify the original DataFrame."""
        original_rpn = sample_fmea["Rpn"].copy()
        route_id = str(sim._all_routes[0])
        _ = sim.apply_risk_escalation(sample_fmea, route_id)
        pd.testing.assert_series_equal(
            sample_fmea["Rpn"],
            original_rpn,
            check_names=True,
        )


# ===========================================================================
# TestDeltaColumn
# ===========================================================================


class TestDeltaColumn:
    """Verify the Disruption_Delta_RPN column semantics."""

    def test_delta_column_present(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Result DataFrame must contain the Disruption_Delta_RPN column."""
        route_id = str(sim._all_routes[0])
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        assert "Disruption_Delta_RPN" in result.columns

    def test_delta_is_rpn_difference(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Disruption_Delta_RPN must equal updated RPN minus original RPN for each row."""
        route_id = str(sim._all_routes[0])
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        original_rpn = pd.to_numeric(sample_fmea["Rpn"], errors="coerce").fillna(0)
        expected_delta = result["Rpn"] - original_rpn
        pd.testing.assert_series_equal(
            result["Disruption_Delta_RPN"].reset_index(drop=True),
            expected_delta.reset_index(drop=True),
            check_names=False,
        )

    def test_unaffected_rows_have_zero_delta(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Rows outside Level-1 and Level-2 must have a zero RPN delta."""
        route_id = str(sim._all_routes[0])
        l1, l2 = sim.get_downstream_components(sample_fmea, route_id)
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        affected = set(l1 + l2)
        for idx in range(len(result)):
            if idx not in affected:
                delta = result.loc[idx, "Disruption_Delta_RPN"]
                assert delta == 0, (
                    f"Unaffected row {idx} has non-zero delta: {delta}"
                )

    def test_affected_rows_have_positive_delta(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Affected rows where at least one base score is below MAX_SCORE must
        have a positive RPN delta (score room available for escalation)."""
        route_id = str(sim._all_routes[0])
        l1, l2 = sim.get_downstream_components(sample_fmea, route_id)
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        escalatable: list[int] = []
        max_s = DisruptionSimulator.MAX_SCORE
        for idx in l1 + l2:
            s = sample_fmea.loc[idx, "Severity"]
            o = sample_fmea.loc[idx, "Occurrence"]
            d = sample_fmea.loc[idx, "Detection"]
            if s < max_s or o < max_s or d < max_s:
                escalatable.append(idx)
        if not escalatable:
            pytest.skip(
                "All affected rows already at MAX_SCORE; delta would be zero."
            )
        for idx in escalatable:
            delta = result.loc[idx, "Disruption_Delta_RPN"]
            assert delta > 0, (
                f"Row {idx} (escalatable) expected positive delta, got {delta}"
            )

    def test_delta_non_negative_for_all_rows(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """Disruption_Delta_RPN must never be negative (scores only increase)."""
        route_id = str(sim._all_routes[0])
        result = sim.apply_risk_escalation(sample_fmea, route_id)
        assert (result["Disruption_Delta_RPN"] >= 0).all(), (
            "Found negative RPN delta values; escalation lowered a score."
        )


# ===========================================================================
# TestExcelExport
# ===========================================================================


class TestExcelExport:
    """Verify the two-sheet Excel workbook written by export_disruption_report."""

    def test_output_file_is_created(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """export_disruption_report must create a file at the specified path."""
        route_id = str(sim._all_routes[0])
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = os.path.join(tmp_dir, "disruption_test.xlsx")
            sim.export_disruption_report(sample_fmea, route_id, out_path)
            assert os.path.exists(out_path), "Disruption report file was not created"

    def test_workbook_has_two_sheets(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """The workbook must contain exactly two sheets."""
        route_id = str(sim._all_routes[0])
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = os.path.join(tmp_dir, "disruption_test.xlsx")
            sim.export_disruption_report(sample_fmea, route_id, out_path)

            with pd.ExcelFile(out_path) as xf:
                sheets = xf.sheet_names
            assert len(sheets) == 2, (
                f"Expected 2 sheets, found {len(sheets)}: {sheets}"
            )

    def test_updated_fmea_sheet_has_delta_column(
        self, sim: DisruptionSimulator, sample_fmea: pd.DataFrame
    ) -> None:
        """The Updated_FMEA sheet must include the Disruption_Delta_RPN column."""
        route_id = str(sim._all_routes[0])
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = os.path.join(tmp_dir, "disruption_test.xlsx")
            sim.export_disruption_report(sample_fmea, route_id, out_path)

            with pd.ExcelFile(out_path) as xf:
                fmea_sheet = pd.read_excel(xf, sheet_name="Updated_FMEA")
            assert "Disruption_Delta_RPN" in fmea_sheet.columns, (
                "Updated_FMEA sheet is missing the Disruption_Delta_RPN column"
            )
