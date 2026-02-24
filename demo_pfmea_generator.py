"""
PFMEA Generator Demo
Test the new form-based prompt generation feature
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from fmea_generator import FMEAGenerator
import yaml

print("\n" + "=" * 70)
print("  PFMEA LLM GENERATOR - DEMO")
print("=" * 70)

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize generator
print("\nInitializing FMEA Generator...")
generator = FMEAGenerator(config)
print("[OK] Generator ready!")

# Test Case 1: Form-based input (like the picture)
print("\n" + "-" * 70)
print("Test Case 1: Form-Based PFMEA Generation")
print("-" * 70)

defect = "dimensions not ok"
cause = "Bad positioning of components in the welding device"
effect = "Difficulties on the assembling line at the customer"
process_type = "welding process"

# Generate prompt
prompt = f"Generate PFMEA LLM record(s) for the {process_type} with defect type '{defect}'."
print(f"\nGenerated Prompt: {prompt}")

# Build context
context = f"Defect: {defect}. Cause: {cause}. Effect: {effect}"
print(f"Context: {context}")

# Generate FMEA
print("\nGenerating PFMEA...")
fmea_df = generator.generate_from_text([context], is_file=False)  # Pass as list

print(f"\n[OK] Generated {len(fmea_df)} PFMEA record(s)")
print("\nResults:")
print(fmea_df[['Component', 'Failure Mode', 'Cause', 'Effect', 'Severity', 'Occurrence', 'Detection', 'Rpn', 'Action Priority']].to_string())

# Export
output_file = 'output/pfmea_demo_form.xlsx'
Path('output').mkdir(exist_ok=True)
generator.export_fmea(fmea_df, output_file, format='excel')
print(f"\n[OK] Saved to: {output_file}")

# Test Case 2: Different defect
print("\n" + "-" * 70)
print("Test Case 2: Different Defect Type")
print("-" * 70)

defect2 = "surface crack"
cause2 = "Excessive heat during welding"
effect2 = "Part failure under stress"
process_type2 = "heat treatment process"

prompt2 = f"Generate PFMEA LLM record(s) for the {process_type2} with defect type '{defect2}'."
print(f"\nGenerated Prompt: {prompt2}")

context2 = f"Defect: {defect2}. Cause: {cause2}. Effect: {effect2}"
fmea_df2 = generator.generate_from_text([context2], is_file=False)  # Pass as list

print(f"\n[OK] Generated {len(fmea_df2)} PFMEA record(s)")
print("\nResults:")
print(fmea_df2[['Component', 'Failure Mode', 'Cause', 'Effect', 'Rpn', 'Action Priority']].head().to_string())

# Export
output_file2 = 'output/pfmea_demo_surface_crack.xlsx'
generator.export_fmea(fmea_df2, output_file2, format='excel')
print(f"\n[OK] Saved to: {output_file2}")

print("\n" + "=" * 70)
print("  DEMO COMPLETED!")
print("=" * 70)
print("\nGenerated files:")
print(f"  - {output_file}")
print(f"  - {output_file2}")
print("\nNext steps:")
print("  1. Review the generated Excel files")
print("  2. Run: streamlit run app.py")
print("  3. Try the 'PFMEA Generator' tab in the dashboard")
print("  4. Optional: Train GPT models with: python train_models.py")
print("")
