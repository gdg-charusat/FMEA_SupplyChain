"""
Multi-Model Comparison Module
Enables structured side-by-side evaluation of outputs from multiple LLMs
Provides disagreement indicators and comparative summary insights
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class MultiModelComparator:
    """
    Orchestrates comparison of FMEA results from multiple models
    Analyzes differences, provides disagreement indicators, and summary insights
    """
    
    def __init__(self, config: Dict):
        """
        Initialize Multi-Model Comparator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.comparison_config = config.get('model_comparison', {})
        self.rpn_threshold = self.comparison_config.get('rpn_diff_threshold', 50)
        self.severity_threshold = self.comparison_config.get('severity_diff_threshold', 2)
        self.occurrence_threshold = self.comparison_config.get('occurrence_diff_threshold', 2)
        self.detection_threshold = self.comparison_config.get('detection_diff_threshold', 2)
        
        logger.info("Multi-Model Comparator initialized")
    
    def compare_models(self, model_results: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Compare FMEA results from multiple models
        
        Args:
            model_results: Dictionary mapping model names to their FMEA DataFrames
                          {
                              'Model1': fmea_df_1,
                              'Model2': fmea_df_2,
                              ...
                          }
        
        Returns:
            Comprehensive comparison dictionary with:
            {
                'comparison_df': Combined comparison DataFrame,
                'disagreement_matrix': Matrix showing disagreements,
                'summary': Comparative summary insights,
                'metrics': Comparison metrics,
                'high_disagreement_cases': Cases with high disagreement
            }
        """
        logger.info(f"Comparing {len(model_results)} models")
        
        if len(model_results) < 2:
            raise ValueError("Need at least 2 models for comparison")
        
        # Step 1: Normalize and align results
        aligned_results = self._align_results(model_results)
        
        # Step 2: Calculate differences for each failure mode
        comparison_df = self._calculate_differences(aligned_results, model_results)
        
        # Step 3: Identify disagreements
        disagreement_matrix = self._identify_disagreements(comparison_df)
        
        # Step 4: Generate comparative summary
        summary = self._generate_comparative_summary(comparison_df, model_results)
        
        # Step 5: Calculate metrics
        metrics = self._calculate_comparison_metrics(comparison_df, disagreement_matrix)
        
        # Step 6: Identify high disagreement cases
        high_disagreement = self._identify_high_disagreement_cases(comparison_df, disagreement_matrix)
        
        return {
            'comparison_df': comparison_df,
            'disagreement_matrix': disagreement_matrix,
            'summary': summary,
            'metrics': metrics,
            'high_disagreement_cases': high_disagreement,
            'model_names': list(model_results.keys())
        }
    
    def _align_results(self, model_results: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict]]:
        """
        Align results from different models by failure mode
        Models may produce different failure modes, so we group by similarity
        
        Args:
            model_results: Dictionary of model names to FMEA DataFrames
        
        Returns:
            Aligned results indexed by failure mode
        """
        aligned = defaultdict(dict)
        
        # Convert each model's results to list of dicts
        for model_name, df in model_results.items():
            logger.info(f"Processing {len(df)} failure modes from {model_name}")
            logger.debug(f"Columns in {model_name} DataFrame: {list(df.columns)}")
            
            for idx, row in df.iterrows():
                # Try both snake_case and Title Case column names
                failure_mode_raw = row.get('failure_mode', row.get('Failure Mode', '')).strip()
                effect = row.get('effect', row.get('Effect', '')).strip()
                cause = row.get('cause', row.get('Cause', '')).strip()
                
                # Get numeric values and convert to int, handling various formats
                try:
                    severity = int(float(row.get('severity', row.get('Severity', 5))))
                except (ValueError, TypeError):
                    severity = 5
                
                try:
                    occurrence = int(float(row.get('occurrence', row.get('Occurrence', 5))))
                except (ValueError, TypeError):
                    occurrence = 5
                
                try:
                    detection = int(float(row.get('detection', row.get('Detection', 5))))
                except (ValueError, TypeError):
                    detection = 5
                
                try:
                    rpn = int(float(row.get('rpn', row.get('Rpn', 125))))
                except (ValueError, TypeError):
                    rpn = 125
                
                action_priority = str(row.get('action_priority', row.get('Action Priority', 'Medium')))
                
                # Normalize for matching but keep original for display
                failure_mode_key = failure_mode_raw.lower()
                
                # Include all failure modes (only skip completely empty ones)
                if failure_mode_key:
                    if failure_mode_key not in aligned:
                        aligned[failure_mode_key] = {
                            'failure_mode': failure_mode_raw,  # Keep original formatting
                            'effect': effect,
                            'cause': cause,
                            'models': {}
                        }
                    
                    aligned[failure_mode_key]['models'][model_name] = {
                        'severity': severity,
                        'occurrence': occurrence,
                        'detection': detection,
                        'rpn': rpn,
                        'action_priority': action_priority
                    }
        
        logger.info(f"Aligned {len(aligned)} unique failure modes across models")
        return dict(aligned)
    
    def _calculate_differences(self, aligned_results: Dict[str, Dict],
                              model_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Calculate numerical differences between models for each failure mode
        
        Args:
            aligned_results: Aligned results from models
            model_results: Original model results
        
        Returns:
            DataFrame with comparison data and differences
        """
        comparison_data = []
        model_names = list(model_results.keys())
        
        for failure_mode_key, data in aligned_results.items():
            models_data = data.get('models', {})
            
            # Include ALL failure modes from all models (not just overlapping ones)
            comparison_row = {
                'failure_mode': data['failure_mode'],
                'effect': data['effect'],
                'cause': data['cause']
            }
            
            # Add individual model scores
            severities = []
            occurrences = []
            detections = []
            rpns = []
            
            for model in model_names:
                if model in models_data:
                    score = models_data[model]
                    comparison_row[f'{model}_severity'] = score['severity']
                    comparison_row[f'{model}_occurrence'] = score['occurrence']
                    comparison_row[f'{model}_detection'] = score['detection']
                    comparison_row[f'{model}_rpn'] = score['rpn']
                    comparison_row[f'{model}_priority'] = score['action_priority']
                    
                    severities.append(score['severity'])
                    occurrences.append(score['occurrence'])
                    detections.append(score['detection'])
                    rpns.append(score['rpn'])
                else:
                    # Model didn't produce this failure mode - use NaN
                    comparison_row[f'{model}_severity'] = np.nan
                    comparison_row[f'{model}_occurrence'] = np.nan
                    comparison_row[f'{model}_detection'] = np.nan
                    comparison_row[f'{model}_rpn'] = np.nan
                    comparison_row[f'{model}_priority'] = 'N/A'
            
            # Calculate statistics (only from available values)
            if len(severities) > 0:
                comparison_row['severity_mean'] = np.mean(severities)
                comparison_row['severity_std'] = np.std(severities)
                comparison_row['severity_range'] = max(severities) - min(severities)
            else:
                comparison_row['severity_mean'] = 0
                comparison_row['severity_std'] = 0
                comparison_row['severity_range'] = 0
            
            if len(occurrences) > 0:
                comparison_row['occurrence_mean'] = np.mean(occurrences)
                comparison_row['occurrence_std'] = np.std(occurrences)
                comparison_row['occurrence_range'] = max(occurrences) - min(occurrences)
            else:
                comparison_row['occurrence_mean'] = 0
                comparison_row['occurrence_std'] = 0
                comparison_row['occurrence_range'] = 0
            
            if len(detections) > 0:
                comparison_row['detection_mean'] = np.mean(detections)
                comparison_row['detection_std'] = np.std(detections)
                comparison_row['detection_range'] = max(detections) - min(detections)
            else:
                comparison_row['detection_mean'] = 0
                comparison_row['detection_std'] = 0
                comparison_row['detection_range'] = 0
            
            if len(rpns) > 0:
                comparison_row['rpn_mean'] = np.mean(rpns)
                comparison_row['rpn_std'] = np.std(rpns)
                comparison_row['rpn_range'] = max(rpns) - min(rpns)
            else:
                comparison_row['rpn_mean'] = 0
                comparison_row['rpn_std'] = 0
                comparison_row['rpn_range'] = 0
            
            comparison_data.append(comparison_row)
        
        comparison_df = pd.DataFrame(comparison_data)
        
        if len(comparison_df) == 0:
            logger.warning("No failure modes found across models")
            return pd.DataFrame()
        
        logger.info(f"Generated comparison data for {len(comparison_df)} failure modes from all models")
        
        return comparison_df
    
    def _identify_disagreements(self, comparison_df: pd.DataFrame) -> Dict[int, Dict[str, bool]]:
        """
        Identify disagreement cases where model scores differ significantly
        
        Args:
            comparison_df: Comparison DataFrame
        
        Returns:
            Matrix indicating disagreements for each row and metric
        """
        disagreement_matrix = {}
        
        for idx, row in comparison_df.iterrows():
            disagreements = {
                'has_severity_disagreement': row['severity_range'] >= self.severity_threshold,
                'has_occurrence_disagreement': row['occurrence_range'] >= self.occurrence_threshold,
                'has_detection_disagreement': row['detection_range'] >= self.detection_threshold,
                'has_rpn_disagreement': row['rpn_range'] >= self.rpn_threshold,
                'severity_range': row['severity_range'],
                'occurrence_range': row['occurrence_range'],
                'detection_range': row['detection_range'],
                'rpn_range': row['rpn_range']
            }
            
            # Overall disagreement flag
            disagreements['has_any_disagreement'] = any([
                disagreements['has_severity_disagreement'],
                disagreements['has_occurrence_disagreement'],
                disagreements['has_detection_disagreement'],
                disagreements['has_rpn_disagreement']
            ])
            
            disagreement_matrix[idx] = disagreements
        
        return disagreement_matrix
    
    def _generate_comparative_summary(self, comparison_df: pd.DataFrame,
                                     model_results: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Generate automated insights about model differences
        
        Args:
            comparison_df: Comparison DataFrame with aligned results
            model_results: Original model results
        
        Returns:
            Dictionary with comparative summary insights
        """
        if comparison_df.empty:
            return {
                'high_severity_assignments': {},
                'conservative_detection': {},
                'agreement_level': 0.0,
                'key_insights': ["No common failure modes found across models for comparison"]
            }
        
        model_names = list(model_results.keys())
        summary = {}
        insights = []
        
        # Analyze which models assign higher severity on average
        severity_means = {}
        for model in model_names:
            col = f'{model}_severity'
            if col in comparison_df.columns:
                severity_means[model] = comparison_df[col].mean()
        
        if severity_means:
            max_severity_model = max(severity_means, key=severity_means.get)
            min_severity_model = min(severity_means, key=severity_means.get)
            summary['high_severity_model'] = max_severity_model
            summary['conservative_severity_model'] = min_severity_model
            
            severity_diff = severity_means[max_severity_model] - severity_means[min_severity_model]
            if severity_diff > 1:
                insights.append(
                    f"{max_severity_model} assigns significantly higher severity "
                    f"(avg {severity_means[max_severity_model]:.2f}) compared to "
                    f"{min_severity_model} (avg {severity_means[min_severity_model]:.2f})"
                )
        
        # Analyze which models are more conservative in detection
        detection_means = {}
        for model in model_names:
            col = f'{model}_detection'
            if col in comparison_df.columns:
                detection_means[model] = comparison_df[col].mean()
        
        if detection_means:
            max_detection_model = max(detection_means, key=detection_means.get)  # Higher detection score = harder to detect
            min_detection_model = min(detection_means, key=detection_means.get)
            summary['optimistic_detection_model'] = min_detection_model
            summary['conservative_detection_model'] = max_detection_model
            
            detection_diff = detection_means[max_detection_model] - detection_means[min_detection_model]
            if detection_diff > 1:
                insights.append(
                    f"{max_detection_model} is more conservative in detection assessment "
                    f"(avg {detection_means[max_detection_model]:.2f}) compared to "
                    f"{min_detection_model} (avg {detection_means[min_detection_model]:.2f})"
                )
        
        # Calculate agreement level
        disagreement_df = comparison_df[comparison_df['severity_range'] > 0]
        agreement_level = (len(comparison_df) - len(disagreement_df)) / len(comparison_df) * 100 if len(comparison_df) > 0 else 0
        summary['agreement_level'] = agreement_level
        
        if agreement_level > 80:
            insights.append(f"High agreement level ({agreement_level:.1f}%) - models produce consistent results")
        elif agreement_level > 50:
            insights.append(f"Moderate agreement level ({agreement_level:.1f}%) - some variation in model assessments")
        else:
            insights.append(f"Low agreement level ({agreement_level:.1f}%) - significant variation between models")
        
        # Analyze RPN differences
        rpn_high_diff = comparison_df[comparison_df['rpn_range'] >= self.rpn_threshold]
        if len(rpn_high_diff) > 0:
            insights.append(
                f"{len(rpn_high_diff)} failure mode(s) show significant RPN differences "
                f"(≥ {self.rpn_threshold} points) between models"
            )
            summary['rpn_disagreement_count'] = len(rpn_high_diff)
        
        summary['key_insights'] = insights
        
        return summary
    
    def _calculate_comparison_metrics(self, comparison_df: pd.DataFrame,
                                     disagreement_matrix: Dict) -> Dict[str, Any]:
        """
        Calculate comprehensive comparison metrics
        
        Args:
            comparison_df: Comparison DataFrame
            disagreement_matrix: Disagreement matrix
        
        Returns:
            Dictionary with comparison metrics
        """
        if comparison_df.empty:
            return {
                'total_compared': 0,
                'severity_disagreement_count': 0,
                'occurrence_disagreement_count': 0,
                'detection_disagreement_count': 0,
                'rpn_disagreement_count': 0,
                'total_disagreement_count': 0
            }
        
        metrics = {
            'total_compared': len(comparison_df),
            'severity_disagreement_count': sum(
                1 for v in disagreement_matrix.values() 
                if v['has_severity_disagreement']
            ),
            'occurrence_disagreement_count': sum(
                1 for v in disagreement_matrix.values() 
                if v['has_occurrence_disagreement']
            ),
            'detection_disagreement_count': sum(
                1 for v in disagreement_matrix.values() 
                if v['has_detection_disagreement']
            ),
            'rpn_disagreement_count': sum(
                1 for v in disagreement_matrix.values() 
                if v['has_rpn_disagreement']
            ),
            'total_disagreement_count': sum(
                1 for v in disagreement_matrix.values() 
                if v['has_any_disagreement']
            )
        }
        
        # Calculate percentages
        total = metrics['total_compared']
        if total > 0:
            metrics['severity_disagreement_pct'] = (metrics['severity_disagreement_count'] / total) * 100
            metrics['occurrence_disagreement_pct'] = (metrics['occurrence_disagreement_count'] / total) * 100
            metrics['detection_disagreement_pct'] = (metrics['detection_disagreement_count'] / total) * 100
            metrics['rpn_disagreement_pct'] = (metrics['rpn_disagreement_count'] / total) * 100
            metrics['total_disagreement_pct'] = (metrics['total_disagreement_count'] / total) * 100
        
        return metrics
    
    def _identify_high_disagreement_cases(self, comparison_df: pd.DataFrame,
                                         disagreement_matrix: Dict) -> List[Dict]:
        """
        Identify failure modes with high disagreement between models
        
        Args:
            comparison_df: Comparison DataFrame
            disagreement_matrix: Disagreement matrix
        
        Returns:
            List of high disagreement cases sorted by severity of disagreement
        """
        high_disagreement = []
        
        for idx, row in comparison_df.iterrows():
            disagreements = disagreement_matrix.get(idx, {})
            
            if disagreements.get('has_any_disagreement', False):
                high_disagreement.append({
                    'failure_mode': row['failure_mode'],
                    'effect': row['effect'],
                    'severity_range': disagreements.get('severity_range', 0),
                    'occurrence_range': disagreements.get('occurrence_range', 0),
                    'detection_range': disagreements.get('detection_range', 0),
                    'rpn_range': disagreements.get('rpn_range', 0),
                    'disagreement_categories': [
                        k.replace('has_', '').replace('_disagreement', '').upper()
                        for k, v in disagreements.items()
                        if 'has_' in k and v is True
                    ]
                })
        
        # Sort by maximum range (descending)
        high_disagreement.sort(
            key=lambda x: max(
                x['severity_range'],
                x['occurrence_range'],
                x['detection_range'],
                x['rpn_range']
            ),
            reverse=True
        )
        
        return high_disagreement
    
    def get_disagreement_indicator(self, row_idx: int,
                                  disagreement_matrix: Dict) -> Dict[str, Any]:
        """
        Get disagreement indicator for a specific failure mode
        
        Args:
            row_idx: Row index in comparison DataFrame
            disagreement_matrix: Disagreement matrix
        
        Returns:
            Indicator dictionary with disagreement details and visual level
        """
        disagreements = disagreement_matrix.get(row_idx, {})
        
        # Determine visual level (0-3: None, Low, Medium, High)
        disagreement_categories = sum(1 for k, v in disagreements.items() 
                                     if 'has_' in k and v is True)
        
        if disagreement_categories == 0:
            level = 0  # None
            color = "green"
            label = "✅ Agreement"
        elif disagreement_categories == 1:
            level = 1  # Low
            color = "yellow"
            label = "⚠️ Minor Disagreement"
        elif disagreement_categories == 2:
            level = 2  # Medium
            color = "orange"
            label = "⚠️ Moderate Disagreement"
        else:
            level = 3  # High
            color = "red"
            label = "🔴 High Disagreement"
        
        return {
            'level': level,
            'color': color,
            'label': label,
            'has_severity_disagreement': disagreements.get('has_severity_disagreement', False),
            'has_occurrence_disagreement': disagreements.get('has_occurrence_disagreement', False),
            'has_detection_disagreement': disagreements.get('has_detection_disagreement', False),
            'has_rpn_disagreement': disagreements.get('has_rpn_disagreement', False),
            'severity_range': disagreements.get('severity_range', 0),
            'occurrence_range': disagreements.get('occurrence_range', 0),
            'detection_range': disagreements.get('detection_range', 0),
            'rpn_range': disagreements.get('rpn_range', 0)
        }


class ComparisonVisualizationHelper:
    """Helper class for generating comparison visualizations"""
    
    @staticmethod
    def create_comparison_summary_text(summary: Dict[str, Any]) -> str:
        """
        Create human-readable summary text from comparison summary
        
        Args:
            summary: Comparison summary dictionary
        
        Returns:
            Formatted summary text
        """
        text = "## Model Comparison Summary\n\n"
        
        if summary.get('key_insights'):
            text += "### Key Insights:\n"
            for insight in summary['key_insights']:
                text += f"- {insight}\n"
        
        text += f"\n### Overall Agreement Level: {summary.get('agreement_level', 0):.1f}%\n"
        
        return text
    
    @staticmethod
    def create_disagreement_visual(disagreement_level: int) -> str:
        """
        Create visual indicator for disagreement level
        
        Args:
            disagreement_level: Level 0-3
        
        Returns:
            Visual representation string
        """
        visuals = {
            0: "🟢",  # Full agreement
            1: "🟡",  # Low disagreement
            2: "🟠",  # Medium disagreement
            3: "🔴"   # High disagreement
        }
        return visuals.get(disagreement_level, "⚪")
    
    @staticmethod
    def create_score_comparison_chart(comparison_df: pd.DataFrame,
                                     model_names: List[str],
                                     metric: str = 'rpn') -> Dict[str, Any]:
        """
        Create a comparison chart for a specific metric across models
        
        Args:
            comparison_df: Comparison DataFrame
            model_names: List of model names
            metric: 'rpn', 'severity', 'occurrence', or 'detection'
        
        Returns:
            Dictionary with chart data for visualization
        """
        import plotly.graph_objects as go
        
        chart_data = {
            'model_scores': {},
            'differences': [],
            'avg_per_model': {}
        }
        
        metric_lower = metric.lower()
        
        # Collect scores for each model
        for model in model_names:
            col_name = f'{model}_{metric_lower}'
            if col_name in comparison_df.columns:
                scores = comparison_df[col_name].values
                chart_data['model_scores'][model] = scores
                chart_data['avg_per_model'][model] = scores.mean()
        
        # Calculate differences
        if len(model_names) >= 2:
            for idx in comparison_df.index:
                scores = []
                for model in model_names:
                    col_name = f'{model}_{metric_lower}'
                    if col_name in comparison_df.columns:
                        scores.append(comparison_df.loc[idx, col_name])
                
                if len(scores) >= 2:
                    diff = max(scores) - min(scores)
                    chart_data['differences'].append({
                        'failure_mode': comparison_df.loc[idx, 'failure_mode'],
                        'difference': diff
                    })
        
        return chart_data
    
    @staticmethod
    def create_model_agreement_heatmap(comparison_df: pd.DataFrame,
                                      model_names: List[str],
                                      metric: str = 'rpn') -> Dict[str, Any]:
        """
        Create heatmap data showing agreement between model pairs
        
        Args:
            comparison_df: Comparison DataFrame
            model_names: List of model names
            metric: Which metric to compare
        
        Returns:
            Heatmap data for visualization
        """
        import numpy as np
        
        metric_lower = metric.lower()
        heatmap_data = np.zeros((len(model_names), len(model_names)))
        
        # Calculate correlation between each model pair
        for i, model1 in enumerate(model_names):
            for j, model2 in enumerate(model_names):
                col1 = f'{model1}_{metric_lower}'
                col2 = f'{model2}_{metric_lower}'
                
                if col1 in comparison_df.columns and col2 in comparison_df.columns:
                    # Calculate correlation coefficient
                    scores1 = comparison_df[col1].values
                    scores2 = comparison_df[col2].values
                    
                    if len(scores1) > 1 and len(scores2) > 1:
                        correlation = np.corrcoef(scores1, scores2)[0, 1]
                        heatmap_data[i][j] = correlation if not np.isnan(correlation) else 0
                    else:
                        heatmap_data[i][j] = 1.0 if i == j else 0
                else:
                    heatmap_data[i][j] = 1.0 if i == j else 0
        
        return {
            'data': heatmap_data.tolist(),
            'models': model_names,
            'metric': metric
        }
    
    @staticmethod
    def create_score_distribution_comparison(comparison_df: pd.DataFrame,
                                            model_names: List[str],
                                            metric: str = 'rpn') -> List[Dict]:
        """
        Create distribution data for each model's scores
        
        Args:
            comparison_df: Comparison DataFrame
            model_names: List of model names
            metric: Which metric to compare
        
        Returns:
            List of dictionaries with distribution data
        """
        metric_lower = metric.lower()
        distributions = []
        
        for model in model_names:
            col_name = f'{model}_{metric_lower}'
            if col_name in comparison_df.columns:
                scores = comparison_df[col_name].values
                distributions.append({
                    'model': model,
                    'mean': float(scores.mean()),
                    'std': float(scores.std()),
                    'min': int(scores.min()),
                    'max': int(scores.max()),
                    'median': float(np.median(scores)),
                    'q25': float(np.percentile(scores, 25)),
                    'q75': float(np.percentile(scores, 75)),
                    'values': [int(v) for v in scores]
                })
        
        return distributions
    
    @staticmethod
    def highlight_disagreement_rows(comparison_df: pd.DataFrame,
                                   disagreement_matrix: Dict) -> List[int]:
        """
        Get indices of rows with disagreements for highlighting
        
        Args:
            comparison_df: Comparison DataFrame
            disagreement_matrix: Disagreement matrix
        
        Returns:
            List of row indices with disagreements
        """
        disagreement_indices = []
        
        for idx, disagreements in disagreement_matrix.items():
            if disagreements.get('has_any_disagreement', False):
                disagreement_indices.append(idx)
        
        return disagreement_indices
    
    @staticmethod
    def create_rpn_comparison_scatter(comparison_df: pd.DataFrame,
                                     model_names: List[str]) -> Dict[str, Any]:
        """
        Create scatter plot data comparing RPN scores between models
        
        Args:
            comparison_df: Comparison DataFrame
            model_names: List of model names (typically 2 for scatter plot)
        
        Returns:
            Scatter plot data
        """
        if len(model_names) < 2:
            return {}
        
        model1, model2 = model_names[0], model_names[1]
        
        col1 = f'{model1}_rpn'
        col2 = f'{model2}_rpn'
        
        if col1 not in comparison_df.columns or col2 not in comparison_df.columns:
            return {}
        
        return {
            'model1': model1,
            'model2': model2,
            'model1_scores': comparison_df[col1].tolist(),
            'model2_scores': comparison_df[col2].tolist(),
            'failure_modes': comparison_df['failure_mode'].tolist(),
            'mean_rpn': float(comparison_df[[col1, col2]].values.mean())
        }
    
    @staticmethod
    def calculate_model_bias(comparison_df: pd.DataFrame,
                           model_names: List[str],
                           metric: str = 'severity') -> Dict[str, float]:
        """
        Calculate bias of each model relative to mean
        
        Args:
            comparison_df: Comparison DataFrame
            model_names: List of model names
            metric: Which metric to analyze
        
        Returns:
            Dictionary with model biases
        """
        metric_lower = metric.lower()
        biases = {}
        
        # Calculate mean for each score
        for idx in comparison_df.index:
            scores = []
            for model in model_names:
                col_name = f'{model}_{metric_lower}'
                if col_name in comparison_df.columns:
                    scores.append(comparison_df.loc[idx, col_name])
            
            mean_score = np.mean(scores) if scores else 0
            
            # Calculate deviation for each model
            for i, model in enumerate(model_names):
                if model not in biases:
                    biases[model] = []
                
                if i < len(scores):
                    deviation = scores[i] - mean_score
                    biases[model].append(deviation)
        
        # Average the deviations per model
        avg_biases = {}
        for model, deviations in biases.items():
            avg_biases[model] = float(np.mean(deviations)) if deviations else 0
        
        return avg_biases



