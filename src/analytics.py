"""
Analytics Module for FMEA Multi-Model Disagreement Heatmap & Variance Analysis
Provides functions to calculate variance, standard deviation, and disagreement matrices
across multiple LLM model outputs.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_fmea_variance(multi_model_results: Dict[str, pd.DataFrame],
                            metrics: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Calculates variance across different LLM scores for the same failure mode.
    
    Args:
        multi_model_results: Dict mapping model_name -> FMEA DataFrame
        metrics: List of metric column names to compare (default: Severity, Occurrence, Detection, RPN)
    
    Returns:
        DataFrame with variance scores per failure mode per metric
    """
    if metrics is None:
        metrics = ["Severity", "Occurrence", "Detection", "RPN"]
    
    model_names = list(multi_model_results.keys())
    if len(model_names) < 2:
        logger.warning("Need at least 2 models to calculate variance.")
        return pd.DataFrame()
    
    # Build a combined frame: rows = failure modes, columns = model scores per metric
    variance_records = []
    
    # Use the first model's failure modes as the reference index
    ref_df = multi_model_results[model_names[0]]
    
    for idx in range(len(ref_df)):
        record = {
            "failure_mode": ref_df.iloc[idx].get("Failure Mode", ref_df.iloc[idx].get("failure_mode", f"FM-{idx}")),
        }
        
        for metric in metrics:
            scores = []
            for model_name in model_names:
                model_df = multi_model_results[model_name]
                if idx < len(model_df):
                    val = model_df.iloc[idx].get(metric, None)
                    if val is not None and pd.notna(val):
                        try:
                            scores.append(float(val))
                        except (ValueError, TypeError):
                            pass
            
            if len(scores) >= 2:
                record[f"{metric}_mean"] = np.mean(scores)
                record[f"{metric}_variance"] = np.var(scores, ddof=1)
                record[f"{metric}_std"] = np.std(scores, ddof=1)
                record[f"{metric}_range"] = max(scores) - min(scores)
                record[f"{metric}_min"] = min(scores)
                record[f"{metric}_max"] = max(scores)
            else:
                record[f"{metric}_mean"] = scores[0] if scores else 0
                record[f"{metric}_variance"] = 0
                record[f"{metric}_std"] = 0
                record[f"{metric}_range"] = 0
                record[f"{metric}_min"] = scores[0] if scores else 0
                record[f"{metric}_max"] = scores[0] if scores else 0
        
        variance_records.append(record)
    
    return pd.DataFrame(variance_records)


def generate_disagreement_matrix(multi_model_results: Dict[str, pd.DataFrame],
                                  metrics: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Formats data for a heatmap showing where models disagree most.
    Returns a matrix with rows = failure modes, columns = metrics,
    and cell values = standard deviation across models.
    
    Args:
        multi_model_results: Dict mapping model_name -> FMEA DataFrame
        metrics: List of metric column names to compare
    
    Returns:
        DataFrame suitable for heatmap visualization (rows=failure modes, cols=metrics, values=std)
    """
    if metrics is None:
        metrics = ["Severity", "Occurrence", "Detection", "RPN"]
    
    model_names = list(multi_model_results.keys())
    if len(model_names) < 2:
        logger.warning("Need at least 2 models to generate disagreement matrix.")
        return pd.DataFrame()
    
    ref_df = multi_model_results[model_names[0]]
    rows = []
    labels = []
    
    for idx in range(len(ref_df)):
        fm_name = ref_df.iloc[idx].get("Failure Mode", ref_df.iloc[idx].get("failure_mode", f"FM-{idx}"))
        labels.append(fm_name)
        
        row_stds = []
        for metric in metrics:
            scores = []
            for model_name in model_names:
                model_df = multi_model_results[model_name]
                if idx < len(model_df):
                    val = model_df.iloc[idx].get(metric, None)
                    if val is not None and pd.notna(val):
                        try:
                            scores.append(float(val))
                        except (ValueError, TypeError):
                            pass
            
            if len(scores) >= 2:
                row_stds.append(np.std(scores, ddof=1))
            else:
                row_stds.append(0.0)
        
        rows.append(row_stds)
    
    disagreement_df = pd.DataFrame(rows, columns=metrics, index=labels)
    disagreement_df.index.name = "Failure Mode"
    
    return disagreement_df


def generate_model_score_matrix(multi_model_results: Dict[str, pd.DataFrame],
                                 metric: str = "RPN") -> pd.DataFrame:
    """
    Creates a matrix of model scores for a single metric.
    Rows = failure modes, Columns = model names, Values = scores.
    
    Args:
        multi_model_results: Dict mapping model_name -> FMEA DataFrame
        metric: The metric to extract (e.g., "Severity", "Occurrence", "Detection", "RPN")
    
    Returns:
        DataFrame with rows=failure modes, cols=model names, values=metric scores
    """
    model_names = list(multi_model_results.keys())
    ref_df = multi_model_results[model_names[0]]
    
    labels = []
    data = {model: [] for model in model_names}
    
    for idx in range(len(ref_df)):
        fm_name = ref_df.iloc[idx].get("Failure Mode", ref_df.iloc[idx].get("failure_mode", f"FM-{idx}"))
        labels.append(fm_name)
        
        for model_name in model_names:
            model_df = multi_model_results[model_name]
            if idx < len(model_df):
                val = model_df.iloc[idx].get(metric, None)
                try:
                    data[model_name].append(float(val) if val is not None and pd.notna(val) else 0)
                except (ValueError, TypeError):
                    data[model_name].append(0)
            else:
                data[model_name].append(0)
    
    score_df = pd.DataFrame(data, index=labels)
    score_df.index.name = "Failure Mode"
    
    return score_df


def identify_high_variance_items(variance_df: pd.DataFrame,
                                  threshold_std: float = 2.0,
                                  metric: str = "RPN") -> pd.DataFrame:
    """
    Filter failure modes where model disagreement exceeds a threshold.
    
    Args:
        variance_df: Output of calculate_fmea_variance
        threshold_std: Minimum std to flag as high-variance
        metric: Metric to use for filtering
    
    Returns:
        Filtered DataFrame of high-variance failure modes
    """
    std_col = f"{metric}_std"
    if std_col not in variance_df.columns:
        return pd.DataFrame()
    
    return variance_df[variance_df[std_col] >= threshold_std].sort_values(
        by=std_col, ascending=False
    )
