"""
FMEA History Tracker Module
Tracks and manages historical FMEA runs for trend analysis
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FMEAHistoryTracker:
    """
    Manages persistent FMEA run history with comparison capabilities
    """
    
    def __init__(self, history_dir: str = "history"):
        """
        Initialize FMEAHistoryTracker
        
        Args:
            history_dir: Directory to store history files (default: "history")
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(exist_ok=True)
        
        logger.info(f"FMEAHistoryTracker initialized with directory: {self.history_dir}")
    
    def save_run(self, fmea_df: pd.DataFrame, label: Optional[str] = None) -> str:
        """
        Save an FMEA run with metadata
        
        Args:
            fmea_df: DataFrame containing the FMEA analysis
            label: Optional label for the run (e.g., "Brake System Jan2025")
        
        Returns:
            str: Run ID (timestamp-based unique identifier)
        """
        # Generate run ID from timestamp
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        # Calculate metadata
        metadata = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "label": label or f"Run {run_id}",
            "row_count": len(fmea_df),
            "average_rpn": float(fmea_df.get('Rpn', pd.Series()).mean()) if 'Rpn' in fmea_df.columns else 0,
            "critical_count": int((fmea_df.get('Action Priority', pd.Series()) == 'Critical').sum()) if 'Action Priority' in fmea_df.columns else 0
        }
        
        # Prepare data for JSON serialization
        run_data = {
            "metadata": metadata,
            "fmea_data": fmea_df.to_dict(orient='records')
        }
        
        # Save to file
        file_path = self.history_dir / f"{run_id}.json"
        try:
            with open(file_path, 'w') as f:
                json.dump(run_data, f, indent=2, default=str)
            logger.info(f"Saved run {run_id} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save run {run_id}: {e}")
            raise
        
        return run_id
    
    def list_runs(self) -> List[Dict]:
        """
        Get metadata for all saved runs
        
        Returns:
            List of dictionaries containing run metadata
        """
        runs = []
        
        # Find all JSON files in history directory
        json_files = sorted(self.history_dir.glob("*.json"), reverse=True)
        
        for file_path in json_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    runs.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to load metadata from {file_path}: {e}")
        
        return runs
    
    def load_run(self, run_id: str) -> Optional[pd.DataFrame]:
        """
        Load the full FMEA data for a specific run
        
        Args:
            run_id: The run ID to load
        
        Returns:
            DataFrame containing the FMEA data, or None if not found
        """
        file_path = self.history_dir / f"{run_id}.json"
        
        if not file_path.exists():
            logger.warning(f"Run {run_id} not found")
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                fmea_data = data.get("fmea_data", [])
                df = pd.DataFrame(fmea_data)
                logger.info(f"Loaded run {run_id} with {len(df)} rows")
                return df
        except Exception as e:
            logger.error(f"Failed to load run {run_id}: {e}")
            return None
    
    def compare_runs(self, run_id_1: str, run_id_2: str) -> Optional[pd.DataFrame]:
        """
        Compare two FMEA runs and return detailed comparison
        
        Args:
            run_id_1: First run ID (baseline/earlier run)
            run_id_2: Second run ID (comparison/later run)
        
        Returns:
            DataFrame with comparison results including status column:
            - "improved": RPN decreased
            - "worsened": RPN increased
            - "new": Failure mode only in run 2
            - "resolved": Failure mode only in run 1
        """
        # Load both runs
        df1 = self.load_run(run_id_1)
        df2 = self.load_run(run_id_2)
        
        if df1 is None or df2 is None:
            logger.error(f"Could not load runs {run_id_1} or {run_id_2}")
            return None
        
        # Ensure we have Failure Mode and Rpn columns
        if 'Failure Mode' not in df1.columns or 'Failure Mode' not in df2.columns:
            logger.warning("Failure Mode column not found in one or both runs")
            return None
        
        # Use Rpn for comparison (case-insensitive search for column name)
        rpn_col1 = None
        rpn_col2 = None
        for col in df1.columns:
            if col.lower() == 'rpn':
                rpn_col1 = col
                break
        for col in df2.columns:
            if col.lower() == 'rpn':
                rpn_col2 = col
                break
        
        if rpn_col1 is None or rpn_col2 is None:
            logger.warning("RPN column not found in one or both runs")
            return None
        
        # Create a comparison dataframe
        comparison_data = []
        
        # Get all unique failure modes from both runs
        all_modes = set(df1['Failure Mode'].unique()) | set(df2['Failure Mode'].unique())
        
        for mode in all_modes:
            record = {"Failure Mode": mode}
            
            # Get RPN from run 1
            run1_row = df1[df1['Failure Mode'] == mode]
            if len(run1_row) > 0:
                rpn1 = run1_row.iloc[0][rpn_col1]
                record[f"RPN ({run_id_1[:8]})"] = rpn1
            else:
                rpn1 = None
                record[f"RPN ({run_id_1[:8]})"] = None
            
            # Get RPN from run 2
            run2_row = df2[df2['Failure Mode'] == mode]
            if len(run2_row) > 0:
                rpn2 = run2_row.iloc[0][rpn_col2]
                record[f"RPN ({run_id_2[:8]})"] = rpn2
            else:
                rpn2 = None
                record[f"RPN ({run_id_2[:8]})"] = None
            
            # Determine status
            if rpn1 is None:
                status = "new"
            elif rpn2 is None:
                status = "resolved"
            elif rpn2 < rpn1:
                status = "improved"
            elif rpn2 > rpn1:
                status = "worsened"
            else:
                status = "unchanged"
            
            record["Status"] = status
            comparison_data.append(record)
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # Sort by status priority: worsened first, then improved, etc.
        status_priority = {"worsened": 0, "new": 1, "unchanged": 2, "improved": 3, "resolved": 4}
        comparison_df["status_order"] = comparison_df["Status"].map(status_priority)
        comparison_df = comparison_df.sort_values("status_order").drop("status_order", axis=1)
        
        logger.info(f"Compared runs {run_id_1} and {run_id_2}: {len(comparison_df)} failure modes")
        
        return comparison_df
    
    def get_trend_data(self, failure_modes: Optional[List[str]] = None, 
                      limit: int = 5) -> Dict[str, List]:
        """
        Get RPN trend data across all runs for specified failure modes
        
        Args:
            failure_modes: List of failure modes to track (None = top failure modes)
            limit: Maximum number of failure modes to include
        
        Returns:
            Dictionary with trend data for plotting
        """
        runs = self.list_runs()
        if not runs:
            return {"runs": [], "data": {}}
        
        # Collect all failure modes and their RPNs across all runs
        all_modes = {}
        run_timestamps = []
        run_labels = []
        
        for run_meta in runs:
            run_id = run_meta.get("run_id")
            run_label = run_meta.get("label", run_id[:8])
            run_timestamp = run_meta.get("timestamp")
            
            if run_id and run_timestamp:
                run_timestamps.append(run_timestamp)
                run_labels.append(run_label)
                
                df = self.load_run(run_id)
                if df is not None:
                    for _, row in df.iterrows():
                        mode = row.get("Failure Mode", "Unknown")
                        rpn_col = None
                        for col in df.columns:
                            if col.lower() == 'rpn':
                                rpn_col = col
                                break
                        
                        if rpn_col and mode not in ["Unknown", None]:
                            rpn = row[rpn_col]
                            if mode not in all_modes:
                                all_modes[mode] = []
                            all_modes[mode].append(rpn)
        
        # If no failure modes specified, get the top ones
        if failure_modes is None:
            # Calculate average RPN for each mode
            avg_rpns = {}
            for mode, rpn_list in all_modes.items():
                avg_rpns[mode] = sum(rpn_list) / len(rpn_list)
            
            # Sort by average RPN (descending) and take top
            sorted_modes = sorted(avg_rpns.items(), key=lambda x: x[1], reverse=True)
            failure_modes = [mode for mode, _ in sorted_modes[:limit]]
        
        # Build trend data
        trend_data = {}
        for mode in failure_modes:
            if mode in all_modes:
                trend_data[mode] = all_modes[mode]
        
        return {
            "run_labels": run_labels,
            "run_timestamps": run_timestamps,
            "failure_modes": failure_modes,
            "trend_data": trend_data
        }
