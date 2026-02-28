"""
Unit tests for report_generator.py with focus on decimal/fractional flows
Tests for Issue #60: Fractional shipment quantities are truncated in mitigation reports
"""

import sys
from pathlib import Path
import pytest

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from mitigation_module.report_generator import (
    generate_impact_report,
    _determine_status,
    get_route_change_summary,
    _generate_impact_table
)


# Test fixtures
SIMPLE_ROUTE_MAP = {
    1: ("Warehouse_A", "Client_NYC"),
    2: ("Warehouse_B", "Client_NYC"),
    3: ("Warehouse_A", "Client_LA"),
    4: ("Warehouse_B", "Client_LA"),
}


class TestDecimalQuantityPreservation:
    """Test that decimal quantities are preserved in report outputs."""
    
    def test_decimal_flows_preserved_in_impact_table(self):
        """Decimal quantities should appear in impact table, not truncated."""
        initial_flows = {1: 12.9, 2: 0, 3: 5.5}
        new_flows = {1: 8.3, 2: 4.6, 3: 5.5}
        
        impact_table = _generate_impact_table(
            initial_flows,
            new_flows,
            SIMPLE_ROUTE_MAP,
            disrupted_routes=[]
        )
        
        # Check that decimals are present in the string representation
        table_str = impact_table.to_string()
        
        # Should contain decimal values, not integers
        assert "12.9" in table_str or "12.90" in table_str, "Original 12.9 should be preserved"
        assert "8.3" in table_str or "8.30" in table_str, "New 8.3 should be preserved"
        assert "4.6" in table_str or "4.60" in table_str, "New 4.6 should be preserved"
        
        # Should NOT show truncated integer values where decimals exist
        assert "Route 1: 12 Units" not in table_str, "12.9 should not be truncated to 12"
        assert "Route 2: 4 Units" not in table_str, "4.6 should not be truncated to 4"
    
    def test_small_decimal_not_shown_as_zero(self):
        """Very small decimals like 0.8 should not become 0."""
        initial_flows = {1: 0}
        new_flows = {1: 0.8}
        
        impact_table = _generate_impact_table(
            initial_flows,
            new_flows,
            SIMPLE_ROUTE_MAP,
            disrupted_routes=[]
        )
        
        table_str = impact_table.to_string()
        
        # 0.8 should be preserved
        assert "0.8" in table_str or "0.80" in table_str, "0.8 should be preserved"
        # Should be marked as ACTIVATED, not remain at 0
        assert "🟢 ACTIVATED" in table_str, "0.8 units should show as ACTIVATED"
    
    def test_integer_flows_still_display_cleanly(self):
        """Integer flows should display without unnecessary decimals."""
        initial_flows = {1: 10.0, 2: 0.0}
        new_flows = {1: 5.0, 2: 15.0}
        
        impact_table = _generate_impact_table(
            initial_flows,
            new_flows,
            SIMPLE_ROUTE_MAP,
            disrupted_routes=[]
        )
        
        table_str = impact_table.to_string()
        
        # Integer values should display cleanly (10, 5, 15, not 10.00, 5.00, 15.00)
        assert "Route 1: 10 Units" in table_str, "10.0 should display as 10"
        assert "Route 2: 15 Units" in table_str, "15.0 should display as 15"
        assert "Route 1: 5 Units" in table_str, "5.0 should display as 5"


class TestStatusDeterminationWithDecimals:
    """Test that status logic works correctly with decimal quantities."""
    
    def test_stopped_status_with_decimal(self):
        """Route with 12.5 → 0 should be STOPPED."""
        status = _determine_status(12.5, 0)
        assert status == "🔴 STOPPED"
    
    def test_activated_status_with_small_decimal(self):
        """Route with 0 → 0.8 should be ACTIVATED, not UNCHANGED."""
        status = _determine_status(0, 0.8)
        assert status == "🟢 ACTIVATED"
    
    def test_activated_status_with_large_decimal(self):
        """Route with 0 → 15.75 should be ACTIVATED."""
        status = _determine_status(0, 15.75)
        assert status == "🟢 ACTIVATED"
    
    def test_unchanged_status_with_nearly_same_decimal(self):
        """Route with 10.005 → 10.003 should be UNCHANGED (within tolerance)."""
        status = _determine_status(10.005, 10.003)
        assert status == "⚪ UNCHANGED"
    
    def test_balanced_status_with_decimal_change(self):
        """Route with 12.9 → 8.3 should be BALANCED."""
        status = _determine_status(12.9, 8.3)
        assert status == "🟡 BALANCED"
    
    def test_very_small_flow_treated_as_zero(self):
        """Route with 0.005 → 0.003 should be UNCHANGED (both below tolerance)."""
        status = _determine_status(0.005, 0.003)
        assert status == "⚪ UNCHANGED"
    
    def test_tolerance_boundary_activated(self):
        """Route with 0.005 → 0.05 should be ACTIVATED (crosses tolerance)."""
        status = _determine_status(0.005, 0.05)
        assert status == "🟢 ACTIVATED"


class TestRouteChangeSummaryWithDecimals:
    """Test change summary counts with decimal flows."""
    
    def test_summary_counts_decimal_flows_correctly(self):
        """Summary should count decimal flows correctly, not treat 0.8 as 0."""
        initial_flows = {
            1: 12.9,  # Will be balanced
            2: 0,     # Will be activated with 0.8
            3: 5.0,   # Will be stopped
            4: 10.0,  # Will be unchanged
        }
        new_flows = {
            1: 8.3,   # Balanced (was 12.9)
            2: 0.8,   # Activated (was 0)
            3: 0,     # Stopped (was 5.0)
            4: 10.005, # Unchanged (within tolerance)
        }
        
        summary = get_route_change_summary(initial_flows, new_flows, SIMPLE_ROUTE_MAP)
        
        assert summary['activated'] == 1, "Route 2 (0 → 0.8) should count as activated"
        assert summary['stopped'] == 1, "Route 3 (5.0 → 0) should count as stopped"
        assert summary['balanced'] == 1, "Route 1 (12.9 → 8.3) should count as balanced"
        assert summary['unchanged'] == 1, "Route 4 (10.0 → 10.005) should count as unchanged"
    
    def test_summary_with_only_decimal_flows(self):
        """Summary should work when all flows are fractional."""
        initial_flows = {1: 2.5, 2: 3.7}
        new_flows = {1: 1.2, 2: 4.9}
        
        summary = get_route_change_summary(initial_flows, new_flows, SIMPLE_ROUTE_MAP)
        
        # Both routes changed significantly
        assert summary['balanced'] == 2
        assert summary['stopped'] == 0
        assert summary['activated'] == 0


class TestFullReportWithDecimalFlows:
    """Integration tests for full report generation with decimal quantities."""
    
    def test_generate_report_preserves_decimals(self):
        """Full report generation should preserve decimal quantities throughout."""
        initial_solution = {
            'flows': {1: 12.9, 2: 0, 3: 5.5},
            'total_cost': 1000.0
        }
        new_solution = {
            'flows': {1: 8.3, 2: 4.6, 3: 5.5},
            'total_cost': 1200.0
        }
        
        summary_text, impact_table, cost_delta_pct = generate_impact_report(
            initial_solution,
            new_solution,
            SIMPLE_ROUTE_MAP,
            disruptions=[]
        )
        
        # Check impact table preserves decimals
        table_str = impact_table.to_string()
        assert "12.9" in table_str or "12.90" in table_str
        assert "8.3" in table_str or "8.30" in table_str
        assert "4.6" in table_str or "4.60" in table_str
        
        # Check that cost delta is calculated correctly
        assert abs(cost_delta_pct - 20.0) < 0.1, "Cost delta should be 20%"
    
    def test_report_with_disrupted_decimal_flow(self):
        """Report should handle disrupted routes with decimal flows."""
        initial_solution = {
            'flows': {1: 12.9, 2: 0},
            'total_cost': 800.0
        }
        new_solution = {
            'flows': {1: 8.3, 2: 4.6},
            'total_cost': 1600.0
        }
        disruptions = [
            {'target_route_id': 1, 'cost_multiplier': 2.0, 'severity_score': 8}
        ]
        
        summary_text, impact_table, cost_delta_pct = generate_impact_report(
            initial_solution,
            new_solution,
            SIMPLE_ROUTE_MAP,
            disruptions=disruptions
        )
        
        # Should mention the disruption
        assert "ALERT" in summary_text or "Route 1" in summary_text
        
        # Table should show decimal quantities
        table_str = impact_table.to_string()
        assert "12.9" in table_str or "12.90" in table_str
        assert "8.3" in table_str or "8.30" in table_str


class TestEdgeCases:
    """Test edge cases with very small or very large decimal values."""
    
    def test_very_small_decimal_near_zero(self):
        """Decimals smaller than tolerance should be treated as zero."""
        status = _determine_status(0.005, 0.007)
        assert status == "⚪ UNCHANGED", "Values below tolerance should be treated as zero"
    
    def test_mixed_integer_and_decimal_flows(self):
        """Report should handle mix of integer and decimal flows."""
        initial_flows = {1: 10, 2: 5.5, 3: 0}
        new_flows = {1: 10, 2: 3.2, 3: 7.8}
        
        impact_table = _generate_impact_table(
            initial_flows,
            new_flows,
            SIMPLE_ROUTE_MAP,
            disrupted_routes=[]
        )
        
        table_str = impact_table.to_string()
        
        # Integer should display cleanly
        assert "Route 1: 10 Units" in table_str
        # Decimals should be preserved
        assert "5.5" in table_str or "5.50" in table_str
        assert "3.2" in table_str or "3.20" in table_str
        assert "7.8" in table_str or "7.80" in table_str
    
    def test_large_decimal_values(self):
        """Report should handle large decimal values correctly."""
        initial_flows = {1: 999.75}
        new_flows = {1: 1234.50}
        
        status = _determine_status(999.75, 1234.50)
        assert status == "🟡 BALANCED"
        
        impact_table = _generate_impact_table(
            initial_flows,
            new_flows,
            SIMPLE_ROUTE_MAP,
            disrupted_routes=[]
        )
        
        table_str = impact_table.to_string()
        assert "999.75" in table_str or "999.8" in table_str
        assert "1234.5" in table_str or "1234.50" in table_str


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
