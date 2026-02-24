"""
Tests for GPU Safeguards
Verifies thread-locking for inference and OOM fallback behavior.
"""

import unittest
import torch
import threading
import time
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from llm_extractor import LLMExtractor, _GPU_LOCK

class TestGPUSafeguards(unittest.TestCase):
    def setUp(self):
        self.config = {
            'model': {
                'name': 'mock-model',
                'device': 'cpu'  # Use CPU for tests to avoid actual GPU requirement
            },
            'prompts': {
                'failure_extraction': 'Process this: ${text}'
            }
        }
        
    @patch('llm_extractor.pipeline')
    @patch('llm_extractor.AutoModelForCausalLM')
    @patch('llm_extractor.AutoTokenizer')
    def test_gpu_lock_serialization(self, mock_tokenizer, mock_model, mock_pipeline):
        """Verify that concurrent requests are serialized by the _GPU_LOCK"""
        # Set up mock pipeline
        mock_pipe = MagicMock()
        mock_pipe.return_value = [{'generated_text': '{"failure_mode": "Test", "effect": "Test", "cause": "Test", "component": "Test", "existing_controls": "Test"}'}]
        mock_pipeline.return_value = mock_pipe
        
        extractor = LLMExtractor(self.config)
        extractor.model_config['device'] = 'cuda' # Force the lock to be used
        
        # Track locked time
        lock_times = []
        
        def mock_inference(prompt, **kwargs):
            time.sleep(0.5) # Simulate workload
            lock_times.append(time.time())
            return [{'generated_text': '{"failure_mode": "Test", "effect": "Test", "cause": "Test", "component": "Test", "existing_controls": "Test"}'}]
            
        mock_pipe.side_effect = mock_inference
        
        # Run two threads
        t1 = threading.Thread(target=extractor.extract_failure_info, args=("Text 1",))
        t2 = threading.Thread(target=extractor.extract_failure_info, args=("Text 2",))
        
        t1.start()
        time.sleep(0.1) # Ensure t1 starts first
        t2.start()
        
        t1.join()
        t2.join()
        
        # If serialized, the difference between lock_times should be at least 0.5s
        self.assertEqual(len(lock_times), 2)
        self.assertGreaterEqual(abs(lock_times[1] - lock_times[0]), 0.4)

    @patch('llm_extractor.pipeline')
    def test_oom_fallback(self, mock_pipeline):
        """Verify that OOM errors trigger the rule-based fallback"""
        mock_pipe = MagicMock()
        mock_pipe.side_effect = torch.cuda.OutOfMemoryError("Mock OOM")
        mock_pipeline.return_value = mock_pipe
        
        extractor = LLMExtractor(self.config)
        extractor.pipeline = mock_pipe
        
        # This should not raise an error but return rule-based results
        result = extractor.extract_failure_info("The engine caught fire because of a fuel leak.")
        
        self.assertIn('failure_mode', result)
        self.assertNotEqual(result['failure_mode'], 'Not specified')
        # Rule-based should catch 'engine' and 'fire' (or similar)
        self.assertTrue(any(k in result['failure_mode'].lower() for k in ['engine', 'fire', 'failed']))

if __name__ == '__main__':
    unittest.main()
