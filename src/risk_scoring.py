"""
Risk Scoring Engine
Calculates Severity, Occurrence, and Detection scores for FMEA
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)


class RiskScoringEngine:
    """
    Calculates risk scores (S, O, D) and RPN for failure modes
    """
    
    def __init__(self, config: Dict):
        """
        Initialize risk scoring engine with configuration
        
        Args:
            config: Configuration dictionary with scoring parameters
        """
        self.config = config
        self.scoring_config = config.get('risk_scoring', {})
        
        # Load keyword-based scoring rules
        self.severity_keywords = self.scoring_config.get('severity', {})
        self.occurrence_keywords = self.scoring_config.get('occurrence', {})
        self.detection_keywords = self.scoring_config.get('detection', {})
    
    def calculate_severity(self, failure_mode: str, effect: str, 
                          context: Optional[str] = None) -> int:
        """
        Calculate Severity score (1-10)
        Higher score = more severe impact
        
        Args:
            failure_mode: Description of what failed
            effect: Impact/consequence of the failure
            context: Additional context text
            
        Returns:
            Severity score (1-10)
        """
        text = f"{failure_mode} {effect}"
        if context:
            text += f" {context}"
        
        text_lower = text.lower()
        
        # Check for high severity keywords
        high_keywords = self.severity_keywords.get('high_keywords', [])
        medium_keywords = self.severity_keywords.get('medium_keywords', [])
        low_keywords = self.severity_keywords.get('low_keywords', [])
        
        high_count = sum(1 for kw in high_keywords if kw in text_lower)
        medium_count = sum(1 for kw in medium_keywords if kw in text_lower)
        low_count = sum(1 for kw in low_keywords if kw in text_lower)
        
        # Safety-related keywords boost severity significantly
        safety_keywords = ['safety', 'dangerous', 'hazard', 'injury', 'death', 
                          'critical', 'catastrophic', 'life-threatening', 'accident',
                          'explosion', 'fire', 'toxic', 'contamination']
        safety_count = sum(1 for kw in safety_keywords if kw in text_lower)
        
        # Customer/quality impact keywords
        quality_keywords = ['customer', 'recall', 'warranty', 'scrap', 'rework',
                          'dissatisfaction', 'complaint', 'return']
        quality_count = sum(1 for kw in quality_keywords if kw in text_lower)
        
        # Production/operational impact
        production_keywords = ['shutdown', 'stop', 'halt', 'inoperative', 'cannot',
                             'unable', 'impossible', 'complete failure']
        production_count = sum(1 for kw in production_keywords if kw in text_lower)
        
        # Specific high-impact effects (more granular)
        if 'leakage' in text_lower or 'leak' in text_lower:
            score = 8  # Leakage is serious
        elif 'shelf life' in text_lower or 'shelf-life' in text_lower:
            score = 6  # Shelf life reduction is moderate-high
        elif 'contamination' in text_lower:
            score = 9  # Contamination is critical
        elif safety_count > 0:
            score = 9 + min(safety_count, 1)  # 9-10 (Safety critical)
        elif production_count >= 2 or high_count >= 3:
            score = 8  # 8 (Major operational impact)
        elif production_count >= 1 or quality_count >= 2 or high_count >= 2:
            score = 7  # 7 (Significant impact)
        elif quality_count >= 1 or high_count >= 1:
            score = 6  # 6 (Notable impact)
        elif medium_count >= 2:
            score = 5  # 5 (Moderate impact)
        elif medium_count >= 1:
            score = 4  # 4 (Minor-moderate impact)
        elif low_count >= 1:
            score = 2 + min(low_count, 1)  # 2-3 (Minor impact)
        else:
            # More intelligent default based on text length and content
            score = self.severity_keywords.get('default', 4)
            # Boost if effect/failure_mode text is long (indicates serious issue)
            if len(text) > 100:
                score += 1
        
        return min(max(score, 1), 10)  # Ensure between 1-10
    
    def calculate_occurrence(self, cause: str, frequency_data: Optional[List[str]] = None,
                            context: Optional[str] = None) -> int:
        """
        Calculate Occurrence score (1-10)
        Higher score = more frequent/likely to occur
        
        Args:
            cause: Root cause description
            frequency_data: List of similar causes (for frequency analysis)
            context: Additional context text
            
        Returns:
            Occurrence score (1-10)
        """
        text = cause
        if context:
            text += f" {context}"
        
        text_lower = text.lower()
        
        # Check for frequency keywords
        high_keywords = self.occurrence_keywords.get('high_keywords', [])
        medium_keywords = self.occurrence_keywords.get('medium_keywords', [])
        low_keywords = self.occurrence_keywords.get('low_keywords', [])
        
        high_count = sum(1 for kw in high_keywords if kw in text_lower)
        medium_count = sum(1 for kw in medium_keywords if kw in text_lower)
        low_count = sum(1 for kw in low_keywords if kw in text_lower)
        
        # Common failure causes that indicate high occurrence
        common_causes = ['wear', 'fatigue', 'aging', 'corrosion', 'temperature', 
                        'vibration', 'operator', 'human error', 'negligence',
                        'improper', 'incorrect', 'inadequate', 'insufficient']
        common_count = sum(1 for kw in common_causes if kw in text_lower)
        
        # Process control issues (typically medium-high occurrence)
        control_issues = ['variation', 'inconsistent', 'unstable', 'fluctuation',
                         'deviation', 'out of spec', 'tolerance']
        control_count = sum(1 for kw in control_issues if kw in text_lower)
        
        # Analyze frequency from historical data if available
        frequency_score = 0
        if frequency_data:
            frequency_score = self._analyze_frequency(cause, frequency_data)
        
        # Specific cause-based scoring (more granular)
        if 'temperature' in text_lower and 'fluctuation' in text_lower:
            keyword_score = 7  # Temperature fluctuation is frequent
        elif 'material variation' in text_lower or 'material' in text_lower:
            keyword_score = 5  # Material variation is moderate
        elif 'operator' in text_lower and 'negligence' in text_lower:
            keyword_score = 6  # Human error is moderately frequent
        elif 'wear' in text_lower or 'fatigue' in text_lower:
            keyword_score = 8  # Wear/fatigue is very common
        elif high_count >= 2:
            keyword_score = 9  # 9 (Very frequent)
        elif high_count >= 1 or common_count >= 2:
            keyword_score = 7  # 7 (Frequent)
        elif common_count >= 1 or control_count >= 2 or medium_count >= 2:
            keyword_score = 6  # 6 (Moderately frequent)
        elif control_count >= 1 or medium_count >= 1:
            keyword_score = 4  # 4 (Occasional)
        elif low_count >= 1:
            keyword_score = 2  # 2 (Rare)
        else:
            # More intelligent default
            keyword_score = self.occurrence_keywords.get('default', 4)
            # If cause mentions specific operator/process, likely medium occurrence
            if 'operator' in text_lower or 'process' in text_lower:
                keyword_score = 5
        
        # Combine keyword score and frequency score
        if frequency_score > 0:
            score = int(0.6 * keyword_score + 0.4 * frequency_score)
        else:
            score = keyword_score
        
        return min(max(score, 1), 10)
    
    def calculate_detection(self, failure_mode: str, existing_controls: str,
                           context: Optional[str] = None) -> int:
        """
        Calculate Detection score (1-10)
        Higher score = harder to detect (INVERSE relationship)
        
        Args:
            failure_mode: Description of what failed
            existing_controls: Description of existing detection controls
            context: Additional context text
            
        Returns:
            Detection score (1-10)
        """
        text = f"{failure_mode} {existing_controls}"
        if context:
            text += f" {context}"
        
        text_lower = text.lower()
        
        # Check for detectability keywords
        easy_detect = self.detection_keywords.get('high_keywords', [])  # Easy to detect
        medium_detect = self.detection_keywords.get('medium_keywords', [])
        hard_detect = self.detection_keywords.get('low_keywords', [])  # Hard to detect
        
        easy_count = sum(1 for kw in easy_detect if kw in text_lower)
        medium_count = sum(1 for kw in medium_detect if kw in text_lower)
        hard_count = sum(1 for kw in hard_detect if kw in text_lower)
        
        # Advanced control mechanism keywords (better controls = easier detection = lower score)
        advanced_controls = ['sensor', 'monitor', 'alarm', 'warning', 'indicator',
                            'automatic', 'real-time', 'continuous monitoring']
        advanced_count = sum(1 for kw in advanced_controls if kw in text_lower)
        
        # Basic control keywords
        basic_controls = ['inspection', 'test', 'check', 'visual', 'manual',
                         'periodic', 'routine']
        basic_count = sum(1 for kw in basic_controls if kw in text_lower)
        
        # Indicators of poor detectability (internal, hidden failures)
        hidden_indicators = ['internal', 'hidden', 'concealed', 'invisible',
                           'gradual', 'slow', 'progressive', 'intermittent']
        hidden_count = sum(1 for kw in hidden_indicators if kw in text_lower)
        
        # Check if no controls mentioned
        no_control_indicators = ['not specified', 'unknown', 'none', 'no control',
                                'not available', 'n/a', 'na']
        no_controls = any(indicator in existing_controls.lower() 
                         for indicator in no_control_indicators)
        
        # Component-specific detection difficulty
        if 'heat sealer' in text_lower or 'sealer' in text_lower:
            # Equipment failures are moderately detectable
            base_detection = 5
        elif 'material' in text_lower and 'packaging' in text_lower:
            # Material issues are harder to detect
            base_detection = 6
        elif 'sensor' in text_lower or 'temperature control' in text_lower:
            # Sensor/control issues are easier to detect
            base_detection = 3
        else:
            base_detection = None
        
        # Calculate score (remember: high score = hard to detect)
        if base_detection is not None:
            score = base_detection
        elif no_controls:
            score = 9  # 9 (No controls, very hard to detect)
        elif hard_count >= 2 or hidden_count >= 2:
            score = 8  # 8 (Very difficult to detect)
        elif hard_count >= 1 or hidden_count >= 1:
            score = 7  # 7 (Difficult to detect)
        elif basic_count >= 2 or medium_count >= 2:
            score = 5  # 5 (Moderate chance of detection)
        elif basic_count >= 1 or medium_count >= 1:
            score = 4  # 4 (Reasonable chance)
        elif advanced_count >= 2 or easy_count >= 2:
            score = 2  # 2 (Easy to detect)
        elif advanced_count >= 1 or easy_count >= 1:
            score = 3  # 3 (Fairly easy to detect)
        else:
            # More intelligent default
            score = self.detection_keywords.get('default', 6)
            # If failure mode mentions visible/audible symptoms, easier to detect
            visible_symptoms = ['visible', 'audible', 'smell', 'smoke', 'leak', 'crack']
            if any(symptom in text_lower for symptom in visible_symptoms):
                score = 4
        
        return min(max(score, 1), 10)
    
    def calculate_rpn(self, severity: int, occurrence: int, detection: int) -> int:
        """
        Calculate Risk Priority Number
        RPN = Severity × Occurrence × Detection
        
        Args:
            severity: Severity score (1-10)
            occurrence: Occurrence score (1-10)
            detection: Detection score (1-10)
            
        Returns:
            RPN value (1-1000)
        """
        return severity * occurrence * detection
    
    def calculate_action_priority(self, severity: int, occurrence: int, 
                                  detection: int) -> str:
        """
        Calculate Action Priority classification
        
        Args:
            severity: Severity score (1-10)
            occurrence: Occurrence score (1-10)
            detection: Detection score (1-10)
            
        Returns:
            Priority level: 'Critical', 'High', 'Medium', or 'Low'
        """
        rpn = self.calculate_rpn(severity, occurrence, detection)
        
        # Priority based on RPN and individual scores
        if rpn >= 500 or severity >= 9:
            return 'Critical'
        elif rpn >= 250 or (severity >= 7 and occurrence >= 7):
            return 'High'
        elif rpn >= 100:
            return 'Medium'
        else:
            return 'Low'
    
    def score_fmea_row(self, row: Dict[str, str], 
                      frequency_data: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Score a single FMEA row
        
        Args:
            row: Dictionary with failure_mode, effect, cause, existing_controls
                 May also contain _profile_severity_boost, _profile_occurrence_boost,
                 _profile_detection_boost from model-specific extraction profiles.
            frequency_data: Historical frequency data for occurrence calculation
            
        Returns:
            Dictionary with added S, O, D, RPN, and AP scores
        """
        # Calculate individual scores
        severity = self.calculate_severity(
            row.get('failure_mode', ''),
            row.get('effect', ''),
            row.get('component', '')
        )
        
        occurrence = self.calculate_occurrence(
            row.get('cause', ''),
            frequency_data,
            row.get('failure_mode', '')
        )
        
        detection = self.calculate_detection(
            row.get('failure_mode', ''),
            row.get('existing_controls', ''),
            row.get('component', '')
        )

        # Apply model-profile boosts (when present)
        severity = min(max(severity + int(row.get('_profile_severity_boost', 0)), 1), 10)
        occurrence = min(max(occurrence + int(row.get('_profile_occurrence_boost', 0)), 1), 10)
        detection = min(max(detection + int(row.get('_profile_detection_boost', 0)), 1), 10)
        
        rpn = self.calculate_rpn(severity, occurrence, detection)
        action_priority = self.calculate_action_priority(severity, occurrence, detection)
        
        # Add scores to row (strip internal profile keys)
        result = {k: v for k, v in row.items() if not k.startswith('_profile_')}
        result.update({
            'severity': severity,
            'occurrence': occurrence,
            'detection': detection,
            'rpn': rpn,
            'action_priority': action_priority
        })
        
        return result
    
    def _analyze_frequency(self, cause: str, frequency_data: List[str]) -> int:
        """
        Analyze how frequently similar causes appear in historical data
        
        Args:
            cause: Current cause description
            frequency_data: List of historical causes
            
        Returns:
            Frequency-based score (1-10)
        """
        if not frequency_data:
            return 0
        
        # Extract key terms from cause
        cause_terms = set(re.findall(r'\w+', cause.lower()))
        
        # Count similar occurrences
        similar_count = 0
        for historical_cause in frequency_data:
            historical_terms = set(re.findall(r'\w+', historical_cause.lower()))
            
            # Calculate similarity (Jaccard index)
            if cause_terms and historical_terms:
                intersection = len(cause_terms & historical_terms)
                union = len(cause_terms | historical_terms)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.3:  # Threshold for "similar"
                    similar_count += 1
        
        # Convert count to score
        total_records = len(frequency_data)
        frequency_ratio = similar_count / total_records if total_records > 0 else 0
        
        if frequency_ratio >= 0.5:
            return 9
        elif frequency_ratio >= 0.3:
            return 7
        elif frequency_ratio >= 0.15:
            return 5
        elif frequency_ratio >= 0.05:
            return 3
        else:
            return 1
    
    def batch_score(self, fmea_data: pd.DataFrame) -> pd.DataFrame:
        """
        Score multiple FMEA rows in batch
        
        Args:
            fmea_data: DataFrame with FMEA information
            
        Returns:
            DataFrame with added risk scores
        """
        logger.info(f"Batch scoring {len(fmea_data)} FMEA rows")
        
        # Get frequency data for occurrence calculation
        frequency_data = fmea_data['cause'].tolist() if 'cause' in fmea_data.columns else []
        
        scored_rows = []
        for idx, row in fmea_data.iterrows():
            scored_row = self.score_fmea_row(row.to_dict(), frequency_data)
            scored_rows.append(scored_row)
            
            if (idx + 1) % 50 == 0:
                logger.info(f"Scored {idx + 1}/{len(fmea_data)} rows")
        
        result_df = pd.DataFrame(scored_rows)
        
        logger.info("Batch scoring completed")
        return result_df


if __name__ == "__main__":
    # Example usage
    import yaml
    
    with open('../config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    scorer = RiskScoringEngine(config)
    
    # Test scoring
    test_row = {
        'failure_mode': 'Brake system failure',
        'effect': 'Unable to stop vehicle, dangerous situation',
        'cause': 'Worn brake pads not detected during maintenance',
        'component': 'Brake system',
        'existing_controls': 'Regular inspection schedule'
    }
    
    result = scorer.score_fmea_row(test_row)
    print("\nScored FMEA Row:")
    for key, value in result.items():
        print(f"{key}: {value}")
