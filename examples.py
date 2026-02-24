"""
Example script demonstrating FMEA Generator usage
"""

import sys
from pathlib import Path
import yaml

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from fmea_generator import FMEAGenerator
from utils import setup_logging, generate_summary_report


def example_1_unstructured_text():
    """Example: Generate FMEA from unstructured customer reviews"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Generating FMEA from Customer Reviews")
    print("=" * 60)
    
    # Sample customer reviews
    reviews = [
        "The brake pedal became extremely soft and the car wouldn't stop properly. "
        "This happened during heavy rain on the highway, creating a very dangerous situation. "
        "I had to pump the brakes multiple times to get any response.",
        
        "Engine started making loud knocking noises at around 40,000 miles. "
        "Eventually the engine seized completely. Dealer said it was due to oil pump failure "
        "that wasn't caught during regular maintenance checks.",
        
        "The airbag warning light came on and stayed on. When I took it to the shop, "
        "they found that the airbag system had malfunctioned and wouldn't deploy in a crash. "
        "This is a serious safety issue that could have cost lives.",
        
        "Transmission slipping badly, especially when accelerating. "
        "Car loses power randomly and sometimes won't shift into gear at all. "
        "Very dangerous when trying to merge onto highway.",
        
        "Steering wheel became very difficult to turn at low speeds. "
        "Power steering pump failed without any warning. Could have caused an accident "
        "if it happened while driving at higher speeds."
    ]
    
    # Load configuration
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # For faster demo, use rule-based extraction
    config['model']['name'] = None
    
    # Initialize generator
    generator = FMEAGenerator(config)
    
    # Generate FMEA
    print("\nProcessing customer reviews...")
    fmea_df = generator.generate_from_text(reviews, is_file=False)
    
    # Display results
    print(f"\n✅ Generated FMEA with {len(fmea_df)} failure modes\n")
    print(fmea_df[['Failure Mode', 'Severity', 'Occurrence', 'Detection', 'Rpn', 'Action Priority']].to_string())
    
    # Export
    output_path = 'output/example_1_customer_reviews.xlsx'
    generator.export_fmea(fmea_df, output_path, format='excel')
    print(f"\n📁 FMEA exported to: {output_path}")
    
    return fmea_df


def example_2_structured_data():
    """Example: Generate FMEA from YOUR structured CSV file (FMEA.csv)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Processing YOUR FMEA.csv Dataset")
    print("=" * 60)
    
    # Check if FMEA.csv exists
    if not Path('FMEA.csv').exists():
        print("\n⚠️  FMEA.csv not found in workspace!")
        return None
    
    import pandas as pd
    
    # Show preview of your data
    df_preview = pd.read_csv('FMEA.csv')
    print(f"\n📊 Your FMEA.csv contains {len(df_preview)} failure modes")
    print(f"📋 Columns: {', '.join(df_preview.columns.tolist())}")
    print("\nPreview of first 3 rows:")
    print(df_preview[['Component', 'Failure Mode', 'Severity', 'Occurrence', 'Detection', 'RPN']].head(3).to_string())
    
    # Load configuration
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Use rule-based for faster processing
    config['model']['name'] = None
    
    # Initialize generator
    generator = FMEAGenerator(config)
    
    # Generate FMEA
    print("\n🔄 Processing YOUR structured FMEA data...")
    fmea_df = generator.generate_from_structured('FMEA.csv')
    
    # Display results
    print(f"\n✅ Enhanced FMEA with {len(fmea_df)} failure modes")
    print("\nTop 10 Highest Risk Items:")
    print(fmea_df[['Component', 'Failure Mode', 'Severity', 'Occurrence', 'Detection', 'Rpn', 'Action Priority']].head(10).to_string())
    
    # Export
    output_path = 'output/example_2_structured.xlsx'
    generator.export_fmea(fmea_df, output_path, format='excel')
    print(f"\n📁 FMEA exported to: {output_path}")
    
    return fmea_df


def example_3_car_reviews_analysis():
    """Example: Analyze YOUR car review data from archive (3) folder"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Processing YOUR Car Review Dataset")
    print("=" * 60)
    
    # Check for review files
    review_files = list(Path('archive (3)').glob('*.csv'))
    
    if not review_files:
        print("⚠️  No review files found in 'archive (3)' folder")
        return None
    
    print(f"\n📁 Found {len(review_files)} car brand review files in your dataset")
    
    # Use Ford reviews as example (one of your files)
    ford_file = Path('archive (3)/Scraped_Car_Review_ford.csv')
    if not ford_file.exists():
        # Fallback to first available file
        review_file = review_files[0]
    else:
        review_file = ford_file
    
    print(f"\n🚗 Analyzing reviews from: {review_file.name}")
    
    # Load configuration
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # For faster processing, use rule-based extraction
    config['model']['name'] = None
    config['text_processing']['max_reviews_per_batch'] = 100  # Process 100 reviews for demo
    
    # Initialize generator
    generator = FMEAGenerator(config)
    
    # Read first few reviews to show what we're processing
    import pandas as pd
    preview_df = pd.read_csv(review_file, nrows=3)
    print(f"\n📝 Sample reviews from {review_file.stem}:")
    if 'Review' in preview_df.columns:
        for i, review in enumerate(preview_df['Review'].head(2), 1):
            print(f"\n{i}. {review[:150]}...")
    
    # Generate FMEA
    print(f"\n🔄 Processing car reviews (analyzing up to 100 reviews)...")
    print("   This may take 1-2 minutes...")
    try:
        fmea_df = generator.generate_from_text(str(review_file), is_file=True)
        
        # Display results
        print(f"\n✅ Generated FMEA with {len(fmea_df)} failure modes from car reviews")
        
        # Show critical issues
        print("\n⚠️  CRITICAL & HIGH PRIORITY FAILURES FOUND:")
        critical_high = fmea_df[fmea_df['Action Priority'].isin(['Critical', 'High'])]
        if len(critical_high) > 0:
            print(critical_high[['Failure Mode', 'Rpn', 'Action Priority']].head(10).to_string())
        else:
            print("   No critical issues found in sample")
        
        # Show top 5 by RPN
        print("\n📊 Top 5 Risks by RPN:")
        print(fmea_df[['Failure Mode', 'Effect', 'Rpn', 'Action Priority']].head().to_string())
        
        # Export
        output_path = f'output/example_3_{review_file.stem}_analysis.xlsx'
        generator.export_fmea(fmea_df, output_path, format='excel')
        print(f"\n📁 FMEA exported to: {output_path}")
        
        # Generate summary
        summary = generate_summary_report(fmea_df)
        print("\n" + summary)
        
        return fmea_df
        
    except Exception as e:
        print(f"❌ Error processing reviews: {e}")
        return None


def main():
    """Run all examples"""
    setup_logging('INFO')
    
    print("\n" + "=" * 60)
    print("🚀 FMEA GENERATOR - EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate different use cases of the FMEA Generator:")
    print("1. Unstructured customer reviews")
    print("2. Structured failure data from CSV")
    print("3. Real-world car review analysis")
    print("\nPress Ctrl+C to stop at any time.")
    print("=" * 60)
    
    # Create output directory
    Path('output').mkdir(exist_ok=True)
    
    # Run examples
    try:
        # Example 1
        input("\nPress Enter to run Example 1 (Customer Reviews)...")
        fmea_1 = example_1_unstructured_text()
        
        # Example 2
        input("\nPress Enter to run Example 2 (Structured Data)...")
        fmea_2 = example_2_structured_data()
        
        # Example 3
        input("\nPress Enter to run Example 3 (Real Car Reviews)...")
        fmea_3 = example_3_car_reviews_analysis()
        
        print("\n" + "=" * 60)
        print("✨ All examples completed successfully!")
        print("=" * 60)
        print("\nGenerated files can be found in the 'output' folder.")
        print("You can now run the dashboard using: streamlit run app.py")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
