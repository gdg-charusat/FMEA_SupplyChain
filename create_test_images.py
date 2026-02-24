"""
Create Test Images for OCR Testing
Generates sample failure report images
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Create output directory
os.makedirs('test_images', exist_ok=True)

print("\n" + "=" * 70)
print("  CREATING TEST IMAGES FOR OCR")
print("=" * 70)

# Test Image 1: Simple failure report
print("\n[1/3] Creating simple failure report image...")
img1 = Image.new('RGB', (800, 500), color='white')
d1 = ImageDraw.Draw(img1)

text1 = """FAILURE REPORT

Failure Mode: Engine overheating
Cause: Coolant leak from radiator
Effect: Engine damage and vehicle breakdown
Severity: Critical
Occurrence: Rare

Component: Cooling System
Detection: Warning light on dashboard
"""

# Try to use a font, fallback to default
try:
    font = ImageFont.truetype("arial.ttf", 20)
except:
    font = ImageFont.load_default()

d1.text((50, 50), text1, fill='black', font=font)
img1.save('test_images/failure_report_1.png')
print("   [OK] Saved: test_images/failure_report_1.png")

# Test Image 2: Multiple issues
print("\n[2/3] Creating multiple issues report...")
img2 = Image.new('RGB', (900, 600), color='white')
d2 = ImageDraw.Draw(img2)

text2 = """QUALITY ISSUES - MANUFACTURING

Issue 1: Welding defects - poor weld quality
Cause: Incorrect temperature settings
Effect: Structural weakness, product failure

Issue 2: Dimensions not matching specifications  
Cause: Worn tooling equipment
Effect: Assembly difficulties at customer site

Issue 3: Surface finish problems
Cause: Contaminated coating material
Effect: Customer complaints, warranty claims
"""

d2.text((50, 50), text2, fill='black', font=font)
img2.save('test_images/failure_report_2.png')
print("   [OK] Saved: test_images/failure_report_2.png")

# Test Image 3: Customer complaint
print("\n[3/3] Creating customer complaint image...")
img3 = Image.new('RGB', (850, 400), color='white')
d3 = ImageDraw.Draw(img3)

text3 = """CUSTOMER COMPLAINT LOG

Vehicle: 2023 Ford Explorer
Issue: Transmission failure at 15,000 miles
Description: Vehicle suddenly lost power while driving
Customer reported burning smell from transmission
Required complete transmission replacement
Safety concern - potential accident risk
"""

d3.text((50, 50), text3, fill='black', font=font)
img3.save('test_images/failure_report_3.png')
print("   [OK] Saved: test_images/failure_report_3.png")

print("\n" + "=" * 70)
print("  TEST IMAGES CREATED!")
print("=" * 70)
print("\nGenerated 3 test images in 'test_images/' folder:")
print("  1. failure_report_1.png - Simple failure report")
print("  2. failure_report_2.png - Multiple issues")
print("  3. failure_report_3.png - Customer complaint")
print("\nNext steps:")
print("  1. Run: streamlit run app.py")
print("  2. Select 'Unstructured Text' → 'Upload File'")
print("  3. Upload one of these test images")
print("  4. Click 'Extract Text & Generate FMEA'")
print("  5. See OCR in action!")
print("")
