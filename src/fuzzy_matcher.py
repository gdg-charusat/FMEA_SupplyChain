"""
Fuzzy matching and clustering utilities for FMEA deduplication

Uses difflib.SequenceMatcher to cluster similar failure mode strings
and merge their rows into a single canonical entry.
"""
from difflib import SequenceMatcher
from typing import List
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0

    # Basic normalization: lowercase and remove non-alpha characters
    def normalize(text: str):
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        tokens = [t.strip() for t in text.split() if t.strip()]
        # crude stemming: strip common suffixes
        def stem(tok):
            for suf in ('ing', 'ed', 's'):
                if tok.endswith(suf) and len(tok) > len(suf) + 1:
                    return tok[:-len(suf)]
            return tok
        tokens = [stem(t) for t in tokens]
        return tokens

    a_tokens = normalize(a)
    b_tokens = normalize(b)

    # Word-overlap similarity (Jaccard-like using smaller-set normalization)
    set_a = set(a_tokens)
    set_b = set(b_tokens)
    if not set_a or not set_b:
        token_sim = 0.0
    else:
        token_sim = len(set_a & set_b) / max(len(set_a), len(set_b))

    seq_ratio = SequenceMatcher(None, a, b).ratio()

    # Use the higher of the two similarity heuristics
    return max(seq_ratio, token_sim)


def cluster_and_merge(fmea_df: pd.DataFrame, threshold: float = 0.85) -> pd.DataFrame:
    """
    Cluster similar `Failure Mode` strings and merge associated rows.

    Args:
        fmea_df: DataFrame with Title Case FMEA columns (e.g. 'Failure Mode', 'Effect',
                 'Severity', 'Occurrence', 'Detection', 'Rpn', etc.)
        threshold: Similarity threshold (0-1) above which two failure modes are
                   considered the same.

    Returns:
        Merged DataFrame with aggregated `Occurrence`, max `Severity`, max `Detection`.
        The `Failure Mode` for a cluster is chosen as the most descriptive (longest) string.
    """
    # Work on a copy
    df = fmea_df.copy().reset_index(drop=True)

    if 'Failure Mode' not in df.columns:
        logger.warning("DataFrame has no 'Failure Mode' column; skipping fuzzy merge")
        return df

    # Prepare list of indices to process, prioritize by Rpn (desc) to preserve high-risk representatives
    if 'Rpn' in df.columns:
        df['_rpn_val'] = pd.to_numeric(df['Rpn'], errors='coerce').fillna(0)
    else:
        df['_rpn_val'] = 0

    indices = df.sort_values('_rpn_val', ascending=False).index.tolist()

    clusters: List[List[int]] = []
    reps: List[str] = []

    failure_texts = df['Failure Mode'].fillna('').astype(str).str.strip().str.lower()

    for idx in indices:
        text = failure_texts.loc[idx]
        placed = False
        for ci, rep_idx in enumerate(clusters):
            # rep_idx is a list of member indices; pick first member as representative
            rep_text = failure_texts.loc[rep_idx[0]]
            if similarity(text, rep_text) >= threshold:
                clusters[ci].append(idx)
                placed = True
                break
        if not placed:
            clusters.append([idx])

    # Build merged rows
    merged_rows = []
    for members in clusters:
        sub = df.loc[members]

        # Choose the most descriptive failure mode (longest string)
        fm_candidates = sub['Failure Mode'].astype(str)
        representative = fm_candidates.loc[fm_candidates.str.len().idxmax()]

        # Aggregate fields
        occurrence_sum = 0
        if 'Occurrence' in sub.columns:
            occurrence_sum = pd.to_numeric(sub['Occurrence'], errors='coerce').fillna(0).sum()
        else:
            occurrence_sum = len(sub)

        severity_max = None
        detection_max = None
        if 'Severity' in sub.columns:
            severity_max = pd.to_numeric(sub['Severity'], errors='coerce').fillna(0).max()
        if 'Detection' in sub.columns:
            detection_max = pd.to_numeric(sub['Detection'], errors='coerce').fillna(0).max()

        # Take first non-null value for Effect, Cause, Component, Existing Controls
        def first_non_null(col_name):
            if col_name in sub.columns:
                vals = sub[col_name].dropna().astype(str)
                if not vals.empty:
                    return vals.iloc[0]
            return ''

        merged = {
            'Failure Mode': representative,
            'Effect': first_non_null('Effect'),
            'Cause': first_non_null('Cause'),
            'Component': first_non_null('Component'),
            'Existing Controls': first_non_null('Existing Controls')
        }

        # Add aggregated numeric fields back
        if severity_max is not None:
            merged['Severity'] = int(severity_max)
        if occurrence_sum is not None:
            merged['Occurrence'] = float(occurrence_sum)
        if detection_max is not None:
            merged['Detection'] = int(detection_max)

        merged_rows.append(merged)

    merged_df = pd.DataFrame(merged_rows)

    # Preserve other columns where possible by merging first row metadata for each cluster
    # e.g., Action Priority / Recommended Action - carry from highest RPN member
    extra_cols = [c for c in df.columns if c not in merged_df.columns and c not in ['_rpn_val']]
    for col in extra_cols:
        values = []
        for members in clusters:
            sub = df.loc[members]
            # pick value from highest RPN member
            sub = sub.sort_values('_rpn_val', ascending=False)
            values.append(sub.iloc[0].get(col, None))
        merged_df[col] = values

    return merged_df
