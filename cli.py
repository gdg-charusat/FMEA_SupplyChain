"""
Command-line interface for FMEA Generator
Allows running the system without the dashboard
"""

import argparse
import re
import sys
from pathlib import Path
import yaml
import pandas as pd

# Add src directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from fmea_generator import FMEAGenerator
from utils import setup_logging, load_config, generate_summary_report
from preprocessing import flag_ambiguous_reviews


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='LLM-Powered FMEA Generator - Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate FMEA from unstructured text file
  python cli.py --text reviews.csv --output fmea_output.xlsx
  
  # Generate FMEA from structured file
  python cli.py --structured failures.csv --output fmea_output.xlsx
  
  # Generate hybrid FMEA
  python cli.py --text reviews.csv --structured failures.csv --output fmea_output.xlsx
  
  # Use custom configuration
  python cli.py --text reviews.csv --config custom_config.yaml --output fmea_output.xlsx
        """
    )
    
    # Input arguments
    parser.add_argument(
        '--text', '-t',
        type=str,
        help='Path to unstructured text file (CSV with reviews, TXT, etc.)'
    )
    
    parser.add_argument(
        '--structured', '-s',
        type=str,
        help='Path to structured FMEA file (CSV or Excel)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        required=True,
        help='Output file path for generated FMEA'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['excel', 'csv', 'json'],
        default='excel',
        help='Output format (default: excel)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--log-level', '-l',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print summary report to console'
    )
    
    parser.add_argument(
        '--no-model',
        action='store_true',
        help='Use rule-based extraction instead of LLM (faster, less accurate)'
    )

    parser.add_argument(
        '--simulate-failure',
        metavar='NODE',
        type=str,
        default=None,
        help=(
            'Simulate a supply chain node failure and generate an additional '
            'disruption report.  NODE can be a Route ID (e.g. "5", "Route_5"), '
            'a Product Category (e.g. "Fresh"), or a Traffic Conditions value '
            '(e.g. "High").  The primary FMEA output (--output) is NOT affected; '
            'the disruption report is written alongside it as '
            '<stem>_disruption_<node>.xlsx.'
        )
    )

    args = parser.parse_args()
    
    # Validate inputs
    if not args.text and not args.structured:
        parser.error("At least one of --text or --structured must be provided")
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Load configuration
    print(f"Loading configuration from: {args.config}")
    config = load_config(args.config)
    
    # Override model if no-model flag is set
    if args.no_model:
        print("Using rule-based extraction (no LLM)")
        config['model']['name'] = None
    
    # Initialize generator
    print("Initializing FMEA Generator...")
    generator = FMEAGenerator(config)
    
    # Generate FMEA
    print("\nGenerating FMEA...")
    
    if args.text and args.structured:
        # Hybrid mode
        print("Mode: Hybrid (Text + Structured)")
        fmea_df = generator.generate_hybrid(
            structured_file=args.structured,
            text_input=args.text
        )
    elif args.text:
        # Text only
        print("Mode: Unstructured Text")
        fmea_df = generator.generate_from_text(args.text, is_file=True)
    else:
        # Structured only
        print("Mode: Structured Data")
        fmea_df = generator.generate_from_structured(args.structured)

    # ------------------------------------------------------------------
    # Sarcasm / ambiguity filter (runs only when text input was provided)
    # ------------------------------------------------------------------
    if args.text:
        import csv as _csv
        # Collect raw lines from the text file
        text_path = Path(args.text)
        if text_path.exists():
            try:
                with open(text_path, encoding='utf-8', errors='replace') as _f:
                    raw_lines = [line.strip() for line in _f if line.strip()]
                # Try to read as CSV; fall back to plain lines
                try:
                    import pandas as _pd
                    _df_raw = _pd.read_csv(text_path, encoding='utf-8',
                                           on_bad_lines='skip', low_memory=False)
                    text_col = next(
                        (c for c in _df_raw.columns
                         if c.lower() in ('review', 'text', 'comment',
                                          'description', 'feedback')),
                        _df_raw.columns[0]
                    )
                    raw_lines = _df_raw[text_col].dropna().astype(str).tolist()
                except Exception:
                    pass  # use the plain-line fallback above

                sarcasm_result = flag_ambiguous_reviews(raw_lines)
                flagged = sarcasm_result["flagged"]
                if flagged:
                    print(f"\n⚠️  {len(flagged)} review(s) flagged as potentially "
                          f"sarcastic — see flagged_reviews.txt")
                    flagged_path = Path("flagged_reviews.txt")
                    with open(flagged_path, "w", encoding="utf-8") as _out:
                        for _rev in flagged:
                            _out.write(_rev + "\n")
                    print(f"   Flagged reviews written to: {flagged_path.resolve()}")
                else:
                    print("\n✅ No sarcastic or ambiguous reviews detected.")
            except Exception as _err:
                print(f"\n⚠️  Sarcasm filter skipped: {_err}")
    
    print(f"\n✅ FMEA generated successfully with {len(fmea_df)} entries")
    
    # Export
    output_path = Path(args.output)
    
    if args.format == 'json':
        from utils import export_to_json
        export_to_json(fmea_df, str(output_path))
    else:
        generator.export_fmea(fmea_df, str(output_path), format=args.format)
    
    print(f"📁 FMEA exported to: {output_path}")
    
    # Print summary if requested
    if args.summary:
        print("\n" + "=" * 60)
        summary = generate_summary_report(fmea_df)
        print(summary)
    
    # Print top 3 critical issues
    critical_df = fmea_df[fmea_df['Action Priority'] == 'Critical']
    if len(critical_df) > 0:
        print("\n⚠️  CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:")
        print("=" * 60)
        for idx, row in critical_df.head(3).iterrows():
            print(f"\n{idx + 1}. {row['Failure Mode']}")
            print(f"   RPN: {row['Rpn']}")
            print(f"   Effect: {row['Effect']}")
            print(f"   Recommended Action: {row['Recommended Action']}")
    
    # Disruption simulation (optional)
    if args.simulate_failure:
        failed_node = args.simulate_failure
        safe_node = re.sub(r'[^\w\-]', '_', failed_node)
        disruption_path = output_path.stem + f"_disruption_{safe_node}.xlsx"
        disruption_out = output_path.parent / disruption_path

        print(f"\n🔴 Simulating failure of supply chain node: {failed_node}")

        dataset_path = Path(__file__).parent / "Dataset_AI_Supply_Optimization.csv"

        try:
            from disruption_simulator import DisruptionSimulator
        except ImportError as exc:
            print(
                f"\n⚠️  Could not import DisruptionSimulator: {exc}\n"
                "Make sure src/disruption_simulator.py exists and dependencies "
                "are installed.",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            sim = DisruptionSimulator(str(dataset_path))
            sim.export_disruption_report(fmea_df, failed_node, str(disruption_out))
            print(f"📊 Disruption report written to: {disruption_out}")
        except Exception as exc:  # noqa: BLE001
            print(
                f"\n⚠️  Disruption simulation failed: {exc}",
                file=sys.stderr,
            )
            sys.exit(1)

    print("\n✨ Process completed successfully!")


if __name__ == "__main__":
    main()
