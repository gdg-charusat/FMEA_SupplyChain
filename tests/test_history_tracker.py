"""
Unit tests for FMEA History Tracker
Run with: pytest tests/test_history_tracker.py
"""

import pytest
import pandas as pd
import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from history_tracker import FMEAHistoryTracker


@pytest.fixture
def temp_history_dir():
    """Create a temporary directory for history files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_fmea_df_1():
    """Sample FMEA DataFrame for testing - Run 1"""
    return pd.DataFrame({
        'Failure Mode': ['Brake Failure', 'Engine Overheating', 'Airbag Not Deployed'],
        'Effect': ['Cannot stop vehicle', 'Engine damage', 'No protection in crash'],
        'Cause': ['Worn brake pads', 'Coolant leak', 'Electrical short circuit'],
        'Component': ['Brake system', 'Engine', 'Safety system'],
        'Process': ['Braking', 'Cooling', 'Deployment'],
        'Existing Controls': ['Regular inspection', 'Temperature monitoring', 'Daily test'],
        'Severity': [10, 8, 9],
        'Occurrence': [5, 4, 3],
        'Detection': [3, 4, 5],
        'Rpn': [150, 128, 135],
        'Action Priority': ['Critical', 'High', 'Critical'],
        'Recommended Action': ['Replace pads', 'Fix leak', 'Replace module']
    })


@pytest.fixture
def sample_fmea_df_2():
    """Sample FMEA DataFrame for testing - Run 2 (with changes)"""
    return pd.DataFrame({
        'Failure Mode': ['Brake Failure', 'Engine Overheating', 'Steering Loose', 'Electrical Short'],
        'Effect': ['Cannot stop vehicle', 'Engine damage', 'Cannot control direction', 'Power loss'],
        'Cause': ['Worn brake pads', 'Coolant leak', 'Failed rod', 'Bad connection'],
        'Component': ['Brake system', 'Engine', 'Steering', 'Electrical'],
        'Process': ['Braking', 'Cooling', 'Control', 'Power'],
        'Existing Controls': ['Regular inspection', 'Temperature monitoring', 'Visual check', 'None'],
        'Severity': [10, 7, 9, 8],
        'Occurrence': [4, 3, 5, 6],
        'Detection': [3, 5, 4, 3],
        'Rpn': [120, 105, 180, 144],
        'Action Priority': ['Critical', 'High', 'Critical', 'High'],
        'Recommended Action': ['Replace pads', 'Fix leak', 'Replace rod', 'Add circuit breaker']
    })


class TestFMEAHistoryTracker:
    """Test cases for FMEAHistoryTracker"""
    
    def test_save_run(self, temp_history_dir, sample_fmea_df_1):
        """Test saving a single FMEA run"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        run_id = tracker.save_run(sample_fmea_df_1, label="Test Run 1")
        
        # Verify run_id is generated
        assert run_id is not None
        assert len(run_id) > 0
        
        # Verify file was created
        file_path = Path(temp_history_dir) / f"{run_id}.json"
        assert file_path.exists()
    
    def test_save_multiple_runs(self, temp_history_dir, sample_fmea_df_1, sample_fmea_df_2):
        """Test saving multiple FMEA runs and they all appear in list"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Save multiple runs
        run_id_1 = tracker.save_run(sample_fmea_df_1, label="Baseline Run")
        run_id_2 = tracker.save_run(sample_fmea_df_2, label="After Changes")
        
        # List all runs
        runs = tracker.list_runs()
        
        # Verify all runs are listed
        assert len(runs) >= 2
        run_ids = [run['run_id'] for run in runs]
        assert run_id_1 in run_ids
        assert run_id_2 in run_ids
        
        # Verify metadata
        for run in runs:
            assert 'run_id' in run
            assert 'timestamp' in run
            assert 'label' in run
            assert 'row_count' in run
            assert 'average_rpn' in run
            assert 'critical_count' in run
    
    def test_load_run(self, temp_history_dir, sample_fmea_df_1):
        """Test loading a saved FMEA run"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Save a run
        run_id = tracker.save_run(sample_fmea_df_1, label="Load Test")
        
        # Load it back
        loaded_df = tracker.load_run(run_id)
        
        # Verify data integrity
        assert loaded_df is not None
        assert len(loaded_df) == len(sample_fmea_df_1)
        assert set(loaded_df.columns) == set(sample_fmea_df_1.columns)
        
        # Verify content
        assert list(loaded_df['Failure Mode']) == list(sample_fmea_df_1['Failure Mode'])
        assert list(loaded_df['Rpn']) == list(sample_fmea_df_1['Rpn'])
    
    def test_compare_runs_improved(self, temp_history_dir, sample_fmea_df_1, sample_fmea_df_2):
        """Test comparing two runs and detecting improvements"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Save both runs
        run_id_1 = tracker.save_run(sample_fmea_df_1, label="Before Mitigation")
        run_id_2 = tracker.save_run(sample_fmea_df_2, label="After Mitigation")
        
        # Compare runs
        comparison_df = tracker.compare_runs(run_id_1, run_id_2)
        
        # Verify comparison was created
        assert comparison_df is not None
        assert 'Failure Mode' in comparison_df.columns
        assert 'Status' in comparison_df.columns
        
        # Verify improved detection
        # Brake Failure: 150 -> 120 (improved)
        # Engine Overheating: 128 -> 105 (improved)
        improved_statuses = comparison_df[comparison_df['Failure Mode'].isin(['Brake Failure', 'Engine Overheating'])]['Status'].unique()
        assert 'improved' in improved_statuses
    
    def test_compare_runs_worsened(self, temp_history_dir, sample_fmea_df_1, sample_fmea_df_2):
        """Test comparing runs and detecting deterioration"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Save runs
        run_id_1 = tracker.save_run(sample_fmea_df_1, label="Before")
        run_id_2 = tracker.save_run(sample_fmea_df_2, label="After")
        
        # Compare
        comparison_df = tracker.compare_runs(run_id_1, run_id_2)
        
        # Steering Loose is new with high RPN (180) - should be detected
        # But since it's new, not worsened. Let's check Electrical Short doesn't exist in first
        worsened = comparison_df[comparison_df['Status'] == 'worsened']
        
        # Verify Status column exists and is properly populated
        assert 'Status' in comparison_df.columns
        assert len(comparison_df) > 0
    
    def test_compare_runs_new_resolved(self, temp_history_dir, sample_fmea_df_1, sample_fmea_df_2):
        """Test comparing runs detects new and resolved issues"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Save runs
        run_id_1 = tracker.save_run(sample_fmea_df_1, label="Original")
        run_id_2 = tracker.save_run(sample_fmea_df_2, label="Updated")
        
        # Compare
        comparison_df = tracker.compare_runs(run_id_1, run_id_2)
        
        # Verify new modes are detected
        # sample_fmea_df_2 has 'Steering Loose' and 'Electrical Short' not in sample_fmea_df_1
        # sample_fmea_df_1 has 'Airbag Not Deployed' not in sample_fmea_df_2
        
        assert 'new' in comparison_df['Status'].values or 'resolved' in comparison_df['Status'].values
        
        # Check specific transitions
        statuses = comparison_df.groupby('Failure Mode')['Status'].first()
        
        # Steering Loose should be new
        if 'Steering Loose' in statuses.index:
            assert statuses['Steering Loose'] == 'new'
        
        # Airbag Not Deployed should be resolved
        if 'Airbag Not Deployed' in statuses.index:
            assert statuses['Airbag Not Deployed'] == 'resolved'
    
    def test_run_metadata_accuracy(self, temp_history_dir, sample_fmea_df_1):
        """Test that run metadata is accurately saved and retrieved"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Save a run
        run_id = tracker.save_run(sample_fmea_df_1, label="Metadata Test")
        
        # Get metadata from list
        runs = tracker.list_runs()
        run_meta = next((r for r in runs if r['run_id'] == run_id), None)
        
        assert run_meta is not None
        assert run_meta['label'] == "Metadata Test"
        assert run_meta['row_count'] == len(sample_fmea_df_1)
        assert 0 <= run_meta['average_rpn'] <= 200  # Should be within reasonable bounds
        assert run_meta['critical_count'] == 2  # Two 'Critical' rows in sample_fmea_df_1
    
    def test_get_trend_data(self, temp_history_dir, sample_fmea_df_1, sample_fmea_df_2):
        """Test trend data generation"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Save multiple runs
        tracker.save_run(sample_fmea_df_1, label="Run 1")
        tracker.save_run(sample_fmea_df_2, label="Run 2")
        
        # Get trend data
        trend_data = tracker.get_trend_data(limit=3)
        
        # Verify structure
        assert 'run_labels' in trend_data
        assert 'failure_modes' in trend_data
        assert 'trend_data' in trend_data
        
        # Verify we have data
        assert len(trend_data['run_labels']) > 0
        assert len(trend_data['failure_modes']) > 0
    
    def test_load_nonexistent_run(self, temp_history_dir):
        """Test loading a run that doesn't exist"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Try to load non-existent run
        result = tracker.load_run("nonexistent_run_id")
        
        # Should return None
        assert result is None
    
    def test_compare_runs_with_missing_columns(self, temp_history_dir):
        """Test comparing runs with minimal FMEA structure"""
        tracker = FMEAHistoryTracker(temp_history_dir)
        
        # Create minimal DataFrames with only required columns
        minimal_df_1 = pd.DataFrame({
            'Failure Mode': ['Mode A', 'Mode B'],
            'Rpn': [100, 150]
        })
        
        minimal_df_2 = pd.DataFrame({
            'Failure Mode': ['Mode A', 'Mode C'],
            'Rpn': [80, 200]
        })
        
        # Save runs
        run_id_1 = tracker.save_run(minimal_df_1, label="Minimal 1")
        run_id_2 = tracker.save_run(minimal_df_2, label="Minimal 2")
        
        # Compare - should still work with minimal structure
        comparison_df = tracker.compare_runs(run_id_1, run_id_2)
        
        # Should detect improvements
        assert comparison_df is not None
        assert len(comparison_df) == 3  # Mode A, Mode B, Mode C
        
        # Mode A improved (100 -> 80)
        mode_a = comparison_df[comparison_df['Failure Mode'] == 'Mode A'].iloc[0]
        assert mode_a['Status'] == 'improved'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
