#!/usr/bin/env python3
"""
FMEA LLM Extraction Evaluation Script
Evaluates LLMExtractor performance against ground truth dataset
"""

import json
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Add src directory to path to import LLMExtractor
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Try to import LLMExtractor, fall back to rule-based if not available  
try:
    from llm_extractor import LLMExtractor
    LLM_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import LLMExtractor: {e}")
    print("Running evaluation in rule-based mode only")
    LLM_AVAILABLE = False
    
    # Create a mock LLMExtractor for rule-based testing
    class MockLLMExtractor:
        def __init__(self, config):
            pass
            
        def extract_failure_info(self, text):
            """Rule-based fallback extraction"""
            return {
                'failure_mode': 'Rule-based extraction result',
                'effect': 'Unknown effect',  
                'cause': 'Unknown cause',
                'component': 'Unknown component'
            }

class FMEAEvaluator:
    """Evaluates FMEA extraction performance"""
    
    def __init__(self, ground_truth_path: str, config_path: str):
        """
        Initialize evaluator
        
        Args:
            ground_truth_path: Path to ground truth JSON file
            config_path: Path to config YAML file
        """
        self.ground_truth_path = ground_truth_path
        self.config_path = config_path
        
        # Load ground truth data
        with open(ground_truth_path, 'r') as f:
            self.ground_truth = json.load(f)
        
        # Load configuration (create minimal config if file doesn't exist)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {'model': {}, 'prompts': {}}
            
        # Initialize LLM extractor
        try:
            if LLM_AVAILABLE:
                self.extractor = LLMExtractor(self.config)
            else:
                self.extractor = MockLLMExtractor(self.config)
        except Exception as e:
            print(f"Warning: Could not initialize LLMExtractor: {e}")
            print("Evaluation will use rule-based extraction only")
            self.extractor = MockLLMExtractor(self.config)
    
    def evaluate_extraction(self, input_text: str, expected: Dict[str, str]) -> Dict:
        """
        Evaluate a single extraction
        
        Args:
            input_text: Text to extract from
            expected: Expected extraction results
            
        Returns:
            Dictionary with evaluation results
        """
        result = {
            'parse_success': False,
            'exact_match': False,
            'field_matches': {
                'failure_mode': False,
                'effect': False, 
                'cause': False,
                'component': False
            },
            'extracted': None,
            'error': None
        }
        
        try:
            # Extract using LLMExtractor or mock
            extracted = self.extractor.extract_failure_info(input_text)
            
            result['parse_success'] = True
            result['extracted'] = extracted
            
            # Check field matches
            required_fields = ['failure_mode', 'effect', 'cause', 'component']
            all_match = True
            
            for field in required_fields:
                expected_val = expected.get(field, '').lower().strip()
                extracted_val = extracted.get(field, '').lower().strip()
                
                # Use simple string matching (case-insensitive)
                field_match = expected_val == extracted_val
                result['field_matches'][field] = field_match
                
                if not field_match:
                    all_match = False
            
            result['exact_match'] = all_match
            
        except Exception as e:
            result['error'] = str(e)
            result['parse_success'] = False
            
        return result
    
    def run_evaluation(self) -> Dict:
        """
        Run full evaluation on ground truth dataset
        
        Returns:
            Dictionary with overall evaluation results
        """
        print("=" * 60)
        print("FMEA LLM EXTRACTION EVALUATION")
        print("=" * 60)
        print(f"Ground truth dataset: {len(self.ground_truth)} examples")
        print(f"LLM Extractor available: {LLM_AVAILABLE}")
        print()
        
        results = {
            'total_examples': len(self.ground_truth),
            'parse_successes': 0,
            'parse_failures': 0,
            'exact_matches': 0,
            'field_accuracies': {
                'failure_mode': 0,
                'effect': 0,
                'cause': 0, 
                'component': 0
            },
            'individual_results': []
        }
        
        for i, example in enumerate(self.ground_truth):
            print(f"Evaluating example {i+1}/{len(self.ground_truth)}: {example['id']}")
            
            eval_result = self.evaluate_extraction(
                example['input_text'], 
                example['expected_output']
            )
            
            results['individual_results'].append({
                'id': example['id'],
                'result': eval_result
            })
            
            # Update counters
            if eval_result['parse_success']:
                results['parse_successes'] += 1
                
                if eval_result['exact_match']:
                    results['exact_matches'] += 1
                
                # Count field accuracies
                for field, is_correct in eval_result['field_matches'].items():
                    if is_correct:
                        results['field_accuracies'][field] += 1
            else:
                results['parse_failures'] += 1
                print(f"  Parse failure: {eval_result['error']}")
        
        # Calculate percentages
        total = results['total_examples']
        
        parse_success_rate = (results['parse_successes'] / total) * 100
        parse_failure_rate = (results['parse_failures'] / total) * 100  
        exact_match_rate = (results['exact_matches'] / total) * 100
        
        field_accuracy_rates = {}
        for field, count in results['field_accuracies'].items():
            field_accuracy_rates[field] = (count / total) * 100
        
        # Print results
        print()
        print("=" * 60)
        print("EVALUATION RESULTS")
        print("=" * 60)
        print()
        print("📊 OVERALL PERFORMANCE:")
        print(f"  Total Examples: {total}")
        print(f"  Parse Success Rate: {parse_success_rate:.1f}% ({results['parse_successes']}/{total})")
        print(f"  Parse Failure Rate: {parse_failure_rate:.1f}% ({results['parse_failures']}/{total})")
        print(f"  Exact Match Rate: {exact_match_rate:.1f}% ({results['exact_matches']}/{total})")
        print()
        print("📋 PER-FIELD ACCURACY:")
        for field, rate in field_accuracy_rates.items():
            count = results['field_accuracies'][field]
            print(f"  {field.replace('_', ' ').title()}: {rate:.1f}% ({count}/{total})")
        print()
        
        # Show some example failures for debugging
        failures = [r for r in results['individual_results'] 
                   if not r['result']['exact_match'] and r['result']['parse_success']]
        
        if failures:
            print("🔍 EXAMPLE EXTRACTION ERRORS (First 3):")
            for i, failure in enumerate(failures[:3]):
                example = next(ex for ex in self.ground_truth if ex['id'] == failure['id'])
                result = failure['result']
                print(f"\n  Example {failure['id']}:")
                print(f"    Input: {example['input_text'][:100]}...")
                print(f"    Expected vs Extracted:")
                for field in ['failure_mode', 'effect', 'cause', 'component']:
                    expected = example['expected_output'][field] 
                    extracted = result['extracted'].get(field, 'N/A')
                    match_status = "✅" if result['field_matches'][field] else "❌"
                    print(f"      {field}: {match_status}")
                    print(f"        Expected:  {expected}")
                    print(f"        Extracted: {extracted}")
        
        # Store detailed results
        results.update({
            'parse_success_rate': parse_success_rate,
            'parse_failure_rate': parse_failure_rate,
            'exact_match_rate': exact_match_rate,
            'field_accuracy_rates': field_accuracy_rates
        })
        
        return results
    
    def save_results(self, results: Dict, output_path: str):
        """Save evaluation results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to: {output_path}")


def main():
    """Run the evaluation"""
    # Set up paths
    script_dir = Path(__file__).parent
    ground_truth_path = script_dir / "ground_truth_fmea.json"
    config_path = script_dir / ".." / ".." / "config" / "config.yaml"
    output_path = script_dir / "evaluation_results.json"
    
    # Check ground truth file exists
    if not ground_truth_path.exists():
        print(f"Error: Ground truth file not found: {ground_truth_path}")
        sys.exit(1)
    
    # Run evaluation
    try:
        evaluator = FMEAEvaluator(str(ground_truth_path), str(config_path))
        results = evaluator.run_evaluation()
        evaluator.save_results(results, str(output_path))
        
        print("\n🎯 EVALUATION COMPLETE")
        print(f"\nKey Metrics:")
        print(f"  - Overall Exact Match: {results['exact_match_rate']:.1f}%")
        print(f"  - Parse Failure Rate: {results['parse_failure_rate']:.1f}%")
        
        if results['field_accuracy_rates']:
            best_field = max(results['field_accuracy_rates'].items(), key=lambda x: x[1])
            worst_field = min(results['field_accuracy_rates'].items(), key=lambda x: x[1])
            print(f"  - Best Field: {best_field[0]} ({best_field[1]:.1f}%)")
            print(f"  - Worst Field: {worst_field[0]} ({worst_field[1]:.1f}%)")
        
    except Exception as e:
        print(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
