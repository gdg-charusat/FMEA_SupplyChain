"""
Model Training Script
Run this to train the two-stage FMEA models with your car review data
"""

import sys
from pathlib import Path
import pandas as pd
from src.model_trainer import FMEAModelTrainer
from src.preprocessing import DataPreprocessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Train sentiment and part extraction models"""
    
    print("\n" + "=" * 70)
    print("  FMEA MODEL TRAINING PIPELINE")
    print("=" * 70)
    print("\nTwo-Stage Training:")
    print("1. Sentiment Classification: GPT-3 Curie (Target: 97% accuracy)")
    print("2. Part Extraction: GPT-3.5 Turbo (Target: 98-99% accuracy)")
    print("")
    
    # Get OpenAI API key
    api_key = input("Enter your OpenAI API Key (or press Enter to skip GPT training): ").strip()
    
    if not api_key:
        print("\n[!] No API key provided. Will use fallback methods:")
        print("    - BiLSTM-CNN for sentiment (87% accuracy)")
        print("    - String matching for parts (75% accuracy)")
        print("")
        use_training = input("Continue with fallback methods? (y/n): ").lower()
        if use_training != 'y':
            print("Training cancelled.")
            return
        api_key = None
    
    # Initialize trainer
    trainer = FMEAModelTrainer(api_key)
    preprocessor = DataPreprocessor()
    
    # Load your car review data
    print("\n[1/4] Loading car review data...")
    review_files = list(Path('archive (3)').glob('*.csv'))[:5]  # Start with 5 brands for testing
    
    all_reviews = []
    for file in review_files:
        print(f"   Loading {file.name}...")
        df = preprocessor.load_unstructured_data(str(file), is_file=True)
        all_reviews.append(df)
    
    reviews_df = pd.concat(all_reviews, ignore_index=True)
    print(f"   [OK] Loaded {len(reviews_df)} reviews from {len(review_files)} brands")
    
    # Prepare data for training
    print("\n[2/4] Preparing training data...")
    
    # Add 'has_part' labels using keyword matching (for supervised training)
    # In production, you'd have manually labeled data
    parts_keywords = ['engine', 'transmission', 'brake', 'tire', 'battery', 'alternator']
    reviews_df['has_part'] = reviews_df['text'].str.lower().str.contains('|'.join(parts_keywords), na=False)
    
    print(f"   [OK] {reviews_df['has_part'].sum()} reviews with parts identified")
    
    # Train models
    if api_key:
        print("\n[3/4] Training GPT models (this may take 10-30 minutes)...")
        results = trainer.train_full_pipeline(reviews_df)
        
        print("\n   Training Results:")
        print(f"   - Sentiment Model: {results['sentiment_model']}")
        print(f"   - Part Extraction Model: {results['part_extraction_model']}")
        print(f"   - Expected Sentiment Accuracy: {results['sentiment_accuracy']*100}%")
        print(f"   - Expected Part Extraction Accuracy: {results['part_extraction_accuracy']*100}%")
    else:
        print("\n[3/4] Skipping GPT training (using fallback methods)")
    
    # Test the pipeline
    print("\n[4/4] Testing trained pipeline...")
    test_reviews = reviews_df.head(100)['text'].tolist()
    results_df = trainer.process_reviews_pipeline(test_reviews)
    
    print(f"\n   Test Results:")
    print(f"   - Processed: {len(test_reviews)} reviews")
    print(f"   - Negative: {results_df.shape[0]} reviews")
    print(f"   - With Parts: {results_df['has_part'].sum()} reviews")
    
    # Save results
    output_file = 'output/model_training_results.xlsx'
    Path('output').mkdir(exist_ok=True)
    results_df.to_excel(output_file, index=False)
    print(f"\n   Results saved to: {output_file}")
    
    print("\n" + "=" * 70)
    print("  TRAINING COMPLETED!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Review training results in output/model_training_results.xlsx")
    print("2. Update config/config.yaml with your fine-tuned model IDs")
    print("3. Run: streamlit run app.py to use trained models")
    print("")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
