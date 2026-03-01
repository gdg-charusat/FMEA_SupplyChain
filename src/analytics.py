"""
Analytics Module for FMEA Multi-Model Comparison
Provides variance analysis, disagreement detection, consensus scoring,
radar chart generation, and benchmarking support.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def normalize_model_results(multi_model_results: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Normalize column names and data types across model results so downstream
    analytics work on a consistent schema.
    """
    score_columns = ['Severity', 'Occurrence', 'Detection', 'RPN']
    normalized: Dict[str, pd.DataFrame] = {}

    for model_name, df in multi_model_results.items():
        ndf = df.copy()

        # Ensure standard column names (case-insensitive match)
        col_map = {}
        for col in ndf.columns:
            for std in score_columns:
                if col.lower() == std.lower():
                    col_map[col] = std
        ndf.rename(columns=col_map, inplace=True)

        # Coerce score columns to numeric
        for col in score_columns:
            if col in ndf.columns:
                ndf[col] = pd.to_numeric(ndf[col], errors='coerce').fillna(0)

        # Compute RPN if missing
        if 'RPN' not in ndf.columns and all(c in ndf.columns for c in ['Severity', 'Occurrence', 'Detection']):
            ndf['RPN'] = ndf['Severity'] * ndf['Occurrence'] * ndf['Detection']

        normalized[model_name] = ndf

    return normalized


# ---------------------------------------------------------------------------
# Variance & disagreement
# ---------------------------------------------------------------------------

def calculate_fmea_variance(multi_model_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calculate per-item variance for each score dimension across models.
    Returns a DataFrame indexed by item with columns
    Severity_var, Occurrence_var, Detection_var, RPN_var.
    """
    norm = normalize_model_results(multi_model_results)
    score_cols = ['Severity', 'Occurrence', 'Detection', 'RPN']

    frames = []
    for model, df in norm.items():
        sub = df[score_cols].copy()
        sub['model'] = model
        sub['item_idx'] = range(len(sub))
        frames.append(sub)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True)
    variance_df = combined.groupby('item_idx')[score_cols].var().fillna(0)
    variance_df.columns = [f'{c}_var' for c in score_cols]
    return variance_df


def generate_disagreement_matrix(multi_model_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Build a model × model disagreement matrix based on mean absolute difference
    of RPN scores across shared items.
    """
    norm = normalize_model_results(multi_model_results)
    model_names = list(norm.keys())
    n = len(model_names)
    matrix = pd.DataFrame(0.0, index=model_names, columns=model_names)

    for i in range(n):
        for j in range(i + 1, n):
            m1, m2 = model_names[i], model_names[j]
            rpn1 = norm[m1]['RPN'].values
            rpn2 = norm[m2]['RPN'].values
            min_len = min(len(rpn1), len(rpn2))
            if min_len > 0:
                mad = float(np.mean(np.abs(rpn1[:min_len] - rpn2[:min_len])))
            else:
                mad = 0.0
            matrix.loc[m1, m2] = mad
            matrix.loc[m2, m1] = mad

    return matrix


def generate_model_score_matrix(multi_model_results: Dict[str, pd.DataFrame],
                                 score_col: str = 'RPN') -> pd.DataFrame:
    """
    Create an items × models matrix of a given score column.
    """
    norm = normalize_model_results(multi_model_results)
    data: Dict[str, List[float]] = {}
    max_items = max((len(df) for df in norm.values()), default=0)

    for model, df in norm.items():
        vals = df[score_col].tolist() if score_col in df.columns else []
        vals += [np.nan] * (max_items - len(vals))
        data[model] = vals

    return pd.DataFrame(data, index=[f'Item {i+1}' for i in range(max_items)])


def identify_high_variance_items(multi_model_results: Dict[str, pd.DataFrame],
                                  threshold: float = 50.0) -> pd.DataFrame:
    """
    Return items where RPN variance exceeds *threshold*.
    """
    var_df = calculate_fmea_variance(multi_model_results)
    if var_df.empty:
        return var_df
    return var_df[var_df['RPN_var'] > threshold]


# ---------------------------------------------------------------------------
# Consensus & agreement
# ---------------------------------------------------------------------------

def calculate_consensus_scores(multi_model_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Per-item consensus score = 1 − normalised_std  (0–1 range, 1 = perfect agreement).
    Returned as a DataFrame with columns [consensus, mean_rpn, std_rpn, cv].
    """
    norm = normalize_model_results(multi_model_results)
    score_col = 'RPN'
    model_names = list(norm.keys())

    max_items = max((len(df) for df in norm.values()), default=0)
    rpn_matrix = np.full((max_items, len(model_names)), np.nan)

    for j, m in enumerate(model_names):
        vals = norm[m][score_col].values if score_col in norm[m].columns else []
        rpn_matrix[:len(vals), j] = vals[:max_items]

    mean_rpn = np.nanmean(rpn_matrix, axis=1)
    std_rpn = np.nanstd(rpn_matrix, axis=1)
    # Coefficient of Variation
    with np.errstate(divide='ignore', invalid='ignore'):
        cv = np.where(mean_rpn > 0, std_rpn / mean_rpn, 0.0)
    consensus = np.clip(1 - cv, 0, 1)

    return pd.DataFrame({
        'consensus': consensus,
        'mean_rpn': mean_rpn,
        'std_rpn': std_rpn,
        'cv': cv
    }, index=[f'Item {i+1}' for i in range(max_items)])


def calculate_average_agreement(multi_model_results: Dict[str, pd.DataFrame]) -> float:
    """
    Return the average consensus across all items (0–1).
    """
    cs = calculate_consensus_scores(multi_model_results)
    if cs.empty:
        return 0.0
    return float(cs['consensus'].mean())


def flag_for_expert_review(multi_model_results: Dict[str, pd.DataFrame],
                           consensus_threshold: float = 0.25) -> pd.DataFrame:
    """
    Return items where consensus < *consensus_threshold* (i.e. high disagreement)
    that should be reviewed by a domain expert.
    """
    cs = calculate_consensus_scores(multi_model_results)
    if cs.empty:
        return cs
    flagged = cs[cs['consensus'] < consensus_threshold].copy()
    flagged['review_reason'] = 'High model disagreement (CV > ' + \
        (1 - flagged['consensus']).round(2).astype(str) + ')'
    return flagged


def identify_field_level_disagreements(multi_model_results: Dict[str, pd.DataFrame],
                                        threshold: float = 2.0) -> List[Dict[str, Any]]:
    """
    Identify per-field (Severity / Occurrence / Detection) disagreements
    where the range across models exceeds *threshold*.
    """
    norm = normalize_model_results(multi_model_results)
    model_names = list(norm.keys())
    fields = ['Severity', 'Occurrence', 'Detection']
    max_items = max((len(df) for df in norm.values()), default=0)

    outliers: List[Dict[str, Any]] = []
    for field in fields:
        vals = np.full((max_items, len(model_names)), np.nan)
        for j, m in enumerate(model_names):
            if field in norm[m].columns:
                v = norm[m][field].values
                vals[:len(v), j] = v[:max_items]

        for i in range(max_items):
            row_vals = vals[i][~np.isnan(vals[i])]
            if len(row_vals) >= 2:
                rng = float(row_vals.max() - row_vals.min())
                if rng > threshold:
                    outliers.append({
                        'item': f'Item {i+1}',
                        'field': field,
                        'range': rng,
                        'values': {model_names[j]: float(vals[i, j])
                                   for j in range(len(model_names))
                                   if not np.isnan(vals[i, j])}
                    })
    return outliers


# ---------------------------------------------------------------------------
# Box-plot helpers
# ---------------------------------------------------------------------------

def prepare_box_plot_data(multi_model_results: Dict[str, pd.DataFrame],
                          score_col: str = 'RPN') -> Dict[str, List[float]]:
    """
    Return {model_name: [list of score values]} suitable for box plots.
    """
    norm = normalize_model_results(multi_model_results)
    data: Dict[str, List[float]] = {}
    for model, df in norm.items():
        if score_col in df.columns:
            data[model] = df[score_col].dropna().tolist()
        else:
            data[model] = []
    return data


# ---------------------------------------------------------------------------
# Benchmarking
# ---------------------------------------------------------------------------

def analyze_benchmark_variance(multi_model_results: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Comprehensive benchmarking analytics summary.
    Returns dict with per-model stats, cross-model variance, and overall metrics.
    """
    norm = normalize_model_results(multi_model_results)
    score_cols = ['Severity', 'Occurrence', 'Detection', 'RPN']

    per_model_stats: Dict[str, Dict[str, float]] = {}
    for model, df in norm.items():
        stats: Dict[str, float] = {}
        for col in score_cols:
            if col in df.columns:
                stats[f'{col}_mean'] = float(df[col].mean())
                stats[f'{col}_std'] = float(df[col].std())
                stats[f'{col}_median'] = float(df[col].median())
        per_model_stats[model] = stats

    var_df = calculate_fmea_variance(multi_model_results)
    avg_agreement = calculate_average_agreement(multi_model_results)

    return {
        'per_model_stats': per_model_stats,
        'variance': var_df.to_dict() if not var_df.empty else {},
        'average_agreement': avg_agreement,
        'n_models': len(norm),
        'n_items': max((len(df) for df in norm.values()), default=0),
    }


# ---------------------------------------------------------------------------
# Radar-chart helpers
# ---------------------------------------------------------------------------

def prepare_radar_data(multi_model_results: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """
    Transform multi_model_results into a list of dicts suitable for radar
    chart rendering.

    Each dict: {
        'model': str,
        'Severity': float (mean),
        'Occurrence': float (mean),
        'Detection': float (mean),
        'RPN': float (mean, / 100 for visual scale),
        'Consistency': float (1 - intra-model CV, 0-1)
    }
    """
    norm = normalize_model_results(multi_model_results)
    radar_data: List[Dict[str, Any]] = []

    for model, df in norm.items():
        entry: Dict[str, Any] = {'model': model}
        for col in ['Severity', 'Occurrence', 'Detection']:
            entry[col] = float(df[col].mean()) if col in df.columns else 0.0

        if 'RPN' in df.columns:
            rpn_vals = df['RPN'].dropna()
            entry['RPN'] = float(rpn_vals.mean()) / 100.0  # scale for radar
            # Consistency as 1 - CV of RPN within this model
            mean_rpn = rpn_vals.mean()
            std_rpn = rpn_vals.std()
            if mean_rpn > 0:
                entry['Consistency'] = max(0.0, 1.0 - (std_rpn / mean_rpn))
            else:
                entry['Consistency'] = 1.0
        else:
            entry['RPN'] = 0.0
            entry['Consistency'] = 1.0

        radar_data.append(entry)

    return radar_data


def calculate_consensus_metrics(multi_model_results: Dict[str, pd.DataFrame],
                                 threshold: float = 0.25) -> Dict[str, Any]:
    """
    Calculate consensus metrics across models using Coefficient of Variation (CV).

    Returns:
        {
          'overall_consensus': float 0-1,
          'per_field': {field: {'mean': …, 'std': …, 'cv': …, 'consensus': …}},
          'high_agreement_fields': [str],
          'low_agreement_fields': [str],
          'badge': str ('High' / 'Medium' / 'Low'),
          'badge_color': str (hex color for UI),
        }
    """
    norm = normalize_model_results(multi_model_results)
    model_names = list(norm.keys())
    fields = ['Severity', 'Occurrence', 'Detection', 'RPN']

    per_field: Dict[str, Dict[str, float]] = {}
    for field in fields:
        means_per_model = []
        for m in model_names:
            if field in norm[m].columns:
                means_per_model.append(float(norm[m][field].mean()))
        if len(means_per_model) >= 2:
            arr = np.array(means_per_model)
            mu = arr.mean()
            sigma = arr.std()
            cv = sigma / mu if mu > 0 else 0.0
            consensus = max(0.0, 1.0 - cv)
        elif len(means_per_model) == 1:
            mu, sigma, cv, consensus = means_per_model[0], 0.0, 0.0, 1.0
        else:
            mu, sigma, cv, consensus = 0.0, 0.0, 0.0, 1.0
        per_field[field] = {'mean': mu, 'std': sigma, 'cv': cv, 'consensus': consensus}

    overall = float(np.mean([v['consensus'] for v in per_field.values()]))
    high = [f for f, v in per_field.items() if v['cv'] <= threshold]
    low = [f for f, v in per_field.items() if v['cv'] > threshold]

    if overall >= 0.8:
        badge, badge_color = 'High', '#28a745'
    elif overall >= 0.5:
        badge, badge_color = 'Medium', '#ffc107'
    else:
        badge, badge_color = 'Low', '#dc3545'

    return {
        'overall_consensus': overall,
        'per_field': per_field,
        'high_agreement_fields': high,
        'low_agreement_fields': low,
        'badge': badge,
        'badge_color': badge_color,
    }


# ---------------------------------------------------------------------------
# DataFrame enrichment for Excel export
# ---------------------------------------------------------------------------

def enrich_with_consensus(comparison_df: pd.DataFrame,
                          multi_model_results: Dict[str, pd.DataFrame],
                          consensus_threshold: float = 0.5) -> pd.DataFrame:
    """
    Add *Disagreement_Score*, *Consensus_Status* and *Review_Required*
    columns to an existing comparison DataFrame so that
    ``FMEAGenerator.export_fmea_with_alerts`` can highlight rows.

    Args:
        comparison_df: The comparison DataFrame from
            ``MultiModelComparator.compare_models``.
        multi_model_results: The ``individual_results`` dict
            (model_name → FMEA DataFrame).
        consensus_threshold: Items with a consensus score **below** this
            value are flagged as high disagreement.

    Returns:
        A copy of *comparison_df* with three new columns appended.
    """
    df = comparison_df.copy()

    # Per-item consensus (CV-based)
    cs = calculate_consensus_scores(multi_model_results)

    n_items = len(df)
    disagreement_scores = []
    consensus_statuses = []
    review_flags = []

    for i in range(n_items):
        if i < len(cs):
            consensus_val = float(cs.iloc[i]['consensus'])
            cv_val = float(cs.iloc[i]['cv'])
        else:
            consensus_val = 1.0
            cv_val = 0.0

        # Disagreement Score = CV rounded to 2 dp
        disagreement_scores.append(round(cv_val, 2))

        # Status label
        if consensus_val < consensus_threshold:
            consensus_statuses.append('🔴 HIGH DISAGREEMENT')
            review_flags.append('YES')
        elif consensus_val < 0.8:
            consensus_statuses.append('🟡 MEDIUM DISAGREEMENT')
            review_flags.append('REVIEW')
        else:
            consensus_statuses.append('🟢 CONSENSUS')
            review_flags.append('NO')

    df['Disagreement_Score'] = disagreement_scores
    df['Consensus_Status'] = consensus_statuses
    df['Review_Required'] = review_flags

    return df


def generate_radar_chart(multi_model_results: Dict[str, pd.DataFrame],
                         title: str = "Multi-Model FMEA Radar Comparison") -> go.Figure:
    """
    Generate an interactive Plotly radar (spider) chart comparing models.

    Each model is a trace.  Axes: Severity, Occurrence, Detection, RPN (scaled),
    Consistency.  All values are normalized to a 0-10 scale so that axes with
    different native ranges are visually comparable.
    """
    radar_data = prepare_radar_data(multi_model_results)
    if not radar_data:
        fig = go.Figure()
        fig.add_annotation(text="No model data available", showarrow=False,
                           xref="paper", yref="paper", x=0.5, y=0.5, font_size=18)
        return fig

    categories = ['Severity', 'Occurrence', 'Detection', 'RPN (scaled)', 'Consistency']

    # Compute per-axis min/max for normalization
    raw_keys = ['Severity', 'Occurrence', 'Detection', 'RPN', 'Consistency']
    axis_max = {}
    axis_min = {}
    for i, key in enumerate(raw_keys):
        vals = [e.get(key, 0) for e in radar_data]
        axis_max[key] = max(vals) if vals else 1
        axis_min[key] = min(vals) if vals else 0
        if axis_max[key] == axis_min[key]:
            axis_max[key] = axis_min[key] + 1  # avoid division by zero

    # Color palette (up to 8 models)
    colors = [
        'rgba(31, 119, 180, 0.7)',   # blue
        'rgba(255, 127, 14, 0.7)',   # orange
        'rgba(44, 160, 44, 0.7)',    # green
        'rgba(214, 39, 40, 0.7)',    # red
        'rgba(148, 103, 189, 0.7)',  # purple
        'rgba(140, 86, 75, 0.7)',    # brown
        'rgba(227, 119, 194, 0.7)',  # pink
        'rgba(127, 127, 127, 0.7)',  # gray
    ]

    fig = go.Figure()

    for idx, entry in enumerate(radar_data):
        color = colors[idx % len(colors)]
        fill_color = color.replace('0.7', '0.15')
        raw_values = [
            entry.get('Severity', 0),
            entry.get('Occurrence', 0),
            entry.get('Detection', 0),
            entry.get('RPN', 0),
            entry.get('Consistency', 0),
        ]
        # Normalize each axis to 0-10 for visual comparability
        norm_values = []
        for i, key in enumerate(raw_keys):
            v = raw_values[i]
            norm_values.append(round(10 * (v - axis_min[key]) / (axis_max[key] - axis_min[key]), 2))

        # Close the polygon
        norm_closed = norm_values + [norm_values[0]]
        cats_closed = categories + [categories[0]]

        # Build hover text with actual values
        hover_texts = [
            f"<b>{categories[i]}</b><br>Normalized: {norm_values[i]:.1f}/10<br>Actual: {raw_values[i]:.2f}"
            for i in range(len(categories))
        ]
        hover_texts.append(hover_texts[0])

        fig.add_trace(go.Scatterpolar(
            r=norm_closed,
            theta=cats_closed,
            fill='toself',
            fillcolor=fill_color,
            line=dict(color=color, width=2),
            name=entry['model'],
            text=hover_texts,
            hoverinfo='text+name',
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10],
                tickfont_size=10,
            ),
            angularaxis=dict(tickfont_size=12),
        ),
        title=dict(text=title, font_size=18, x=0.5),
        showlegend=True,
        legend=dict(
            orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5,
            font_size=12,
        ),
        margin=dict(t=80, b=80, l=80, r=80),
        height=550,
    )

    return fig


def generate_field_radar_chart(multi_model_results: Dict[str, pd.DataFrame],
                                item_index: int = 0,
                                title: str = "Per-Item Model Comparison") -> go.Figure:
    """
    Generate a radar chart for a single FMEA item comparing all models on
    Severity, Occurrence, and Detection.
    """
    norm = normalize_model_results(multi_model_results)
    categories = ['Severity', 'Occurrence', 'Detection']
    colors = [
        'rgba(31, 119, 180, 0.7)', 'rgba(255, 127, 14, 0.7)',
        'rgba(44, 160, 44, 0.7)', 'rgba(214, 39, 40, 0.7)',
        'rgba(148, 103, 189, 0.7)', 'rgba(140, 86, 75, 0.7)',
    ]

    fig = go.Figure()
    for idx, (model, df) in enumerate(norm.items()):
        if item_index >= len(df):
            continue
        row = df.iloc[item_index]
        vals = [float(row.get(c, 0)) for c in categories]
        vals_closed = vals + [vals[0]]
        cats_closed = categories + [categories[0]]

        color = colors[idx % len(colors)]
        fig.add_trace(go.Scatterpolar(
            r=vals_closed, theta=cats_closed,
            fill='toself',
            fillcolor=color.replace('0.7', '0.15'),
            line=dict(color=color, width=2),
            name=model,
        ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
        title=dict(text=f"{title} — Item {item_index + 1}", font_size=16, x=0.5),
        showlegend=True, height=450,
        margin=dict(t=60, b=60, l=60, r=60),
    )
    return fig
