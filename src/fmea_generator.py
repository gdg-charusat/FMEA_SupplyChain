"""
FMEA Generator Module
Orchestrates the complete FMEA generation pipeline
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging
from datetime import datetime

from preprocessing import DataPreprocessor
from llm_extractor import LLMExtractor
from risk_scoring import RiskScoringEngine
from fuzzy_matcher import cluster_and_merge

logger = logging.getLogger(__name__)


class FMEAGenerator:
    """
    Complete FMEA generation system
    Orchestrates preprocessing, extraction, and risk scoring
    """
    
    def __init__(self, config: Dict):
        """
        Initialize FMEA Generator with all components
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        logger.info("Initializing FMEA Generator components...")
        
        # Initialize modules
        self.preprocessor = DataPreprocessor(config)
        self.extractor = LLMExtractor(config)
        self.scorer = RiskScoringEngine(config)
        
        logger.info("FMEA Generator initialized successfully")
    
    def generate_from_text(self, text_input: Union[str, List[str]], 
                          is_file: bool = False) -> pd.DataFrame:
        """
        Generate FMEA from unstructured text input
        
        Args:
            text_input: File path or list of text strings
            is_file: Whether text_input is a file path
            
        Returns:
            Complete FMEA DataFrame
        """
        logger.info("Generating FMEA from unstructured text...")
        
        # Step 1: Preprocess text
        if is_file:
            preprocessed_df = self.preprocessor.load_unstructured_data(file_path=text_input)
        else:
            preprocessed_df = self.preprocessor.load_unstructured_data(text_data=text_input)
        
        # Step 2: Extract failure information using LLM
        texts = preprocessed_df['text_cleaned'].tolist()
        extracted_info = self.extractor.batch_extract(texts)
        
        # Convert to DataFrame
        extracted_df = pd.DataFrame(extracted_info)
        
        # Add original text for reference
        extracted_df['original_text'] = preprocessed_df['text'].values
        extracted_df['sentiment'] = preprocessed_df['sentiment'].values
        
        # Step 3: Calculate risk scores
        fmea_df = self.scorer.batch_score(extracted_df)
        
        # Step 4: Generate recommended actions
        fmea_df = self._generate_recommendations(fmea_df)
        
        # Step 5: Format final output
        fmea_df = self._format_output(fmea_df)
        
        logger.info(f"Generated FMEA with {len(fmea_df)} entries")
        
        return fmea_df
    
    def generate_from_structured(self, file_path: str) -> pd.DataFrame:
        """
        Generate FMEA from structured input (CSV/Excel)
        
        Args:
            file_path: Path to CSV or Excel file
            
        Returns:
            Complete FMEA DataFrame
        """
        logger.info(f"Generating FMEA from structured file: {file_path}")
        
        # Step 1: Load and validate structured data
        structured_df = self.preprocessor.load_structured_data(file_path)
        
        # Step 2: Check if risk scores already exist
        has_scores = all(col in structured_df.columns 
                        for col in ['severity', 'occurrence', 'detection'])
        
        if not has_scores:
            # Calculate risk scores
            logger.info("Calculating risk scores for structured data...")
            fmea_df = self.scorer.batch_score(structured_df)
        else:
            # Use existing scores, recalculate RPN
            logger.info("Using existing risk scores from file")
            fmea_df = structured_df.copy()
            fmea_df['rpn'] = fmea_df.apply(
                lambda row: self.scorer.calculate_rpn(
                    row['severity'], row['occurrence'], row['detection']
                ), axis=1
            )
            fmea_df['action_priority'] = fmea_df.apply(
                lambda row: self.scorer.calculate_action_priority(
                    row['severity'], row['occurrence'], row['detection']
                ), axis=1
            )
        
        # Step 3: Generate recommended actions
        fmea_df = self._generate_recommendations(fmea_df)
        
        # Step 4: Format output
        fmea_df = self._format_output(fmea_df)
        
        logger.info(f"Generated FMEA with {len(fmea_df)} entries")
        
        return fmea_df
    
    def generate_hybrid(self, structured_file: Optional[str] = None,
                       text_input: Optional[Union[str, List[str]]] = None) -> pd.DataFrame:
        """
        Generate FMEA from both structured and unstructured inputs
        
        Args:
            structured_file: Path to structured data file
            text_input: Unstructured text data
            
        Returns:
            Combined FMEA DataFrame
        """
        logger.info("Generating hybrid FMEA from multiple sources...")
        
        dataframes = []
        
        # Process structured data
        if structured_file:
            structured_fmea = self.generate_from_structured(structured_file)
            structured_fmea['source'] = 'Structured Data'
            dataframes.append(structured_fmea)
        
        # Process unstructured data
        if text_input:
            is_file = isinstance(text_input, str) and Path(text_input).exists()
            text_fmea = self.generate_from_text(text_input, is_file=is_file)
            text_fmea['source'] = 'Unstructured Text'
            dataframes.append(text_fmea)
        
        if not dataframes:
            raise ValueError("No input data provided")
        
        # Combine all sources
        combined_fmea = pd.concat(dataframes, ignore_index=True)
        
        # Remove duplicates based on similarity
        combined_fmea = self._deduplicate_failures(combined_fmea)
        
        # Re-sort by RPN
        combined_fmea = combined_fmea.sort_values('Rpn', ascending=False).reset_index(drop=True)
        
        logger.info(f"Generated combined FMEA with {len(combined_fmea)} entries")
        
        return combined_fmea
    
    def _generate_recommendations(self, fmea_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate recommended actions based on risk scores
        
        Args:
            fmea_df: FMEA DataFrame with risk scores
            
        Returns:
            DataFrame with added recommendations
        """
        def get_recommendation(row):
            priority = row.get('action_priority', 'Medium')
            severity = row.get('severity', 5)
            occurrence = row.get('occurrence', 5)
            detection = row.get('detection', 5)
            
            recommendations = []
            
            # Severity-based recommendations
            if severity >= 8:
                recommendations.append("Immediate design review required")
                recommendations.append("Implement redundant safety systems")
            elif severity >= 6:
                recommendations.append("Enhance safety controls")
            
            # Occurrence-based recommendations
            if occurrence >= 8:
                recommendations.append("Root cause analysis needed")
                recommendations.append("Process improvement required")
            elif occurrence >= 6:
                recommendations.append("Implement preventive maintenance")
            
            # Detection-based recommendations
            if detection >= 8:
                recommendations.append("Improve detection methods")
                recommendations.append("Add monitoring systems")
            elif detection >= 6:
                recommendations.append("Enhance inspection procedures")
            
            if priority == 'Critical':
                recommendations.insert(0, "URGENT: Immediate action required")
            
            return " | ".join(recommendations) if recommendations else "Continue monitoring"
        
        fmea_df['recommended_action'] = fmea_df.apply(get_recommendation, axis=1)
        
        return fmea_df
    
    def _format_output(self, fmea_df: pd.DataFrame) -> pd.DataFrame:
        """
        Format FMEA output with proper column order and naming
        
        Args:
            fmea_df: FMEA DataFrame
            
        Returns:
            Formatted DataFrame
        """
        # Define standard FMEA column order
        standard_columns = [
            'failure_mode',
            'effect',
            'cause',
            'component',
            'process',
            'existing_controls',
            'severity',
            'occurrence',
            'detection',
            'rpn',
            'action_priority',
            'recommended_action'
        ]
        
        # Add optional columns if they exist
        optional_columns = ['source', 'original_text', 'sentiment']
        
        # Select available columns
        output_columns = [col for col in standard_columns if col in fmea_df.columns]
        output_columns += [col for col in optional_columns if col in fmea_df.columns]
        
        # Ensure process column exists
        if 'process' not in fmea_df.columns:
            fmea_df['process'] = fmea_df.get('component', 'General Process')
        
        result_df = fmea_df[output_columns].copy()
        
        # Rename columns to proper case
        result_df.columns = [col.replace('_', ' ').title() for col in result_df.columns]
        
        # Sort by RPN (descending)
        if 'Rpn' in result_df.columns:
            result_df = result_df.sort_values('Rpn', ascending=False).reset_index(drop=True)
        
        return result_df
    
    def _deduplicate_failures(self, fmea_df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate or very similar failure modes
        
        Args:
            fmea_df: FMEA DataFrame
            
        Returns:
            Deduplicated DataFrame
        """
        logger.info("Removing duplicate failure modes (fuzzy matching)...")

        # Read threshold from config (default to 0.85)
        threshold = self.config.get('text_processing', {}).get('fuzzy_match_threshold', 0.85)

        # Use fuzzy matcher to cluster and merge similar failure modes
        try:
            merged = cluster_and_merge(fmea_df, threshold=threshold)
        except Exception as e:
            logger.error(f"Fuzzy clustering failed: {e}")
            return fmea_df

        # Recalculate RPN and action priority based on aggregated scores
        if 'Severity' in merged.columns and 'Occurrence' in merged.columns and 'Detection' in merged.columns:
            merged['Rpn'] = merged.apply(
                lambda row: self.scorer.calculate_rpn(row['Severity'], row['Occurrence'], row['Detection']), axis=1
            )
            merged['Action Priority'] = merged.apply(
                lambda row: self.scorer.calculate_action_priority(row['Severity'], row['Occurrence'], row['Detection']), axis=1
            )

        # Re-generate recommended actions (generator expects lower-case keys)
        temp = merged.copy()
        rename_map = {}
        for col in ['Severity', 'Occurrence', 'Detection', 'Action Priority']:
            if col in temp.columns:
                rename_map[col] = col.lower().replace(' ', '_').strip()

        temp = temp.rename(columns=rename_map)

        temp = self._generate_recommendations(temp)

        # Copy back recommended action if present
        if 'recommended_action' in temp.columns:
            merged['Recommended Action'] = temp['recommended_action'].values

        # Ensure Rpn sort and reset index
        if 'Rpn' in merged.columns:
            merged = merged.sort_values('Rpn', ascending=False).reset_index(drop=True)

        removed_count = len(fmea_df) - len(merged)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} duplicate entries after fuzzy merge")

        return merged
    
    def export_fmea(self, fmea_df: pd.DataFrame, output_path: str, 
                   format: str = 'excel'):
        """
        Export FMEA to file
        
        Args:
            fmea_df: FMEA DataFrame to export
            output_path: Output file path
            format: 'excel' or 'csv'
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'excel':
            # Export to Excel with formatting
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                fmea_df.to_excel(writer, sheet_name='FMEA', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['FMEA']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4472C4',
                    'font_color': 'white',
                    'border': 1
                })
                
                # Format headers
                for col_num, value in enumerate(fmea_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust column widths
                for i, col in enumerate(fmea_df.columns):
                    max_length = max(
                        fmea_df[col].astype(str).apply(len).max(),
                        len(col)
                    )
                    worksheet.set_column(i, i, min(max_length + 2, 50))
            
            logger.info(f"FMEA exported to Excel: {output_path}")
            
        else:  # CSV
            fmea_df.to_csv(output_path, index=False)
            logger.info(f"FMEA exported to CSV: {output_path}")


if __name__ == "__main__":
    # Example usage
    import yaml
    
    with open('../config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    generator = FMEAGenerator(config)
    
    # Test with sample text
    sample_texts = [
        "The engine failed completely after 50k miles. This caused the car to stop on the highway, creating a dangerous situation.",
        "Brake system malfunction - brakes became unresponsive during heavy rain. Almost caused an accident."
    ]
    
    fmea = generator.generate_from_text(sample_texts, is_file=False)
    print("\nGenerated FMEA:")
    print(fmea)
