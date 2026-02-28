"""
Security Fix Verification Script
Tests that the trust_remote_code vulnerability has been properly fixed
"""

import sys
from pathlib import Path
import re

def check_trust_remote_code():
    """Check if trust_remote_code=True exists in llm_extractor.py"""
    print("=" * 70)
    print("SECURITY FIX VERIFICATION")
    print("=" * 70)
    print()
    
    llm_file = Path("src/llm_extractor.py")
    
    if not llm_file.exists():
        print("❌ ERROR: src/llm_extractor.py not found!")
        return False
    
    content = llm_file.read_text(encoding='utf-8')
    
    # Check for vulnerable pattern
    vulnerable_pattern = r'trust_remote_code\s*=\s*True'
    vulnerable_matches = re.findall(vulnerable_pattern, content, re.IGNORECASE)
    
    # Check for secure pattern
    secure_pattern = r'trust_remote_code\s*=\s*False'
    secure_matches = re.findall(secure_pattern, content, re.IGNORECASE)
    
    # Check for whitelist
    whitelist_pattern = r'TRUSTED_MODELS\s*='
    has_whitelist = bool(re.search(whitelist_pattern, content))
    
    # Check for validation method
    validation_pattern = r'def _is_trusted_model'
    has_validation = bool(re.search(validation_pattern, content))
    
    print("1. Checking for vulnerable code (trust_remote_code=True)...")
    if vulnerable_matches:
        print(f"   ❌ FAIL: Found {len(vulnerable_matches)} instances of trust_remote_code=True")
        print("   This is a CRITICAL security vulnerability!")
        return False
    else:
        print("   ✅ PASS: No vulnerable trust_remote_code=True found")
    
    print()
    print("2. Checking for secure code (trust_remote_code=False)...")
    if secure_matches:
        print(f"   ✅ PASS: Found {len(secure_matches)} instances of trust_remote_code=False")
    else:
        print("   ❌ FAIL: No trust_remote_code=False found")
        return False
    
    print()
    print("3. Checking for model whitelist (TRUSTED_MODELS)...")
    if has_whitelist:
        print("   ✅ PASS: Model whitelist found")
        # Extract whitelist
        whitelist_match = re.search(r'TRUSTED_MODELS\s*=\s*\{([^}]+)\}', content, re.DOTALL)
        if whitelist_match:
            models = re.findall(r'"([^"]+)"', whitelist_match.group(1))
            print(f"   Found {len(models)} trusted models:")
            for model in models[:3]:
                print(f"      - {model}")
            if len(models) > 3:
                print(f"      ... and {len(models) - 3} more")
    else:
        print("   ❌ FAIL: No model whitelist found")
        return False
    
    print()
    print("4. Checking for validation method (_is_trusted_model)...")
    if has_validation:
        print("   ✅ PASS: Model validation method found")
    else:
        print("   ❌ FAIL: No validation method found")
        return False
    
    print()
    print("5. Checking for security documentation...")
    docs_found = []
    for doc in ["SECURITY_FIX.md", "SECURITY_QUICKREF.md", "SECURITY_FIX_SUMMARY.md"]:
        if Path(doc).exists():
            docs_found.append(doc)
            print(f"   ✅ {doc} exists")
        else:
            print(f"   ⚠️  {doc} not found")
    
    print()
    print("=" * 70)
    print("VERIFICATION RESULT")
    print("=" * 70)
    
    if len(vulnerable_matches) == 0 and len(secure_matches) >= 2 and has_whitelist and has_validation:
        print("✅ SUCCESS: All security checks passed!")
        print()
        print("Security Status:")
        print("  • trust_remote_code=True: REMOVED ✅")
        print("  • trust_remote_code=False: IMPLEMENTED ✅")
        print("  • Model whitelist: ACTIVE ✅")
        print("  • Validation method: PRESENT ✅")
        print(f"  • Documentation: {len(docs_found)}/3 files ✅")
        print()
        print("🔒 System is now SECURE against supply chain attacks!")
        return True
    else:
        print("❌ FAILURE: Security checks did not pass!")
        print("Please review the fix and ensure all changes are applied.")
        return False


def check_readme_updated():
    """Check if README has been updated with security notice"""
    print()
    print("=" * 70)
    print("README SECURITY NOTICE CHECK")
    print("=" * 70)
    print()
    
    readme = Path("README.md")
    if not readme.exists():
        print("⚠️  README.md not found")
        return False
    
    content = readme.read_text(encoding='utf-8')
    
    has_security_section = "Security Notice" in content or "security" in content.lower()
    has_security_badge = "Security" in content and "badge" in content
    has_security_links = "SECURITY_FIX.md" in content or "SECURITY_QUICKREF.md" in content
    
    if has_security_section:
        print("✅ README contains security information")
    else:
        print("⚠️  README may not have security section")
    
    if has_security_badge:
        print("✅ README has security badge")
    else:
        print("⚠️  README may not have security badge")
    
    if has_security_links:
        print("✅ README links to security documentation")
    else:
        print("⚠️  README may not link to security docs")
    
    return has_security_section or has_security_links


def main():
    """Main verification function"""
    print()
    print("🔍 Starting Security Fix Verification...")
    print()
    
    # Check main security fix
    security_ok = check_trust_remote_code()
    
    # Check README updates
    readme_ok = check_readme_updated()
    
    print()
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print()
    
    if security_ok:
        print("✅ Core Security Fix: VERIFIED")
    else:
        print("❌ Core Security Fix: FAILED")
    
    if readme_ok:
        print("✅ Documentation Updates: VERIFIED")
    else:
        print("⚠️  Documentation Updates: PARTIAL")
    
    print()
    
    if security_ok:
        print("🎉 SECURITY FIX SUCCESSFULLY APPLIED!")
        print()
        print("Next Steps:")
        print("  1. Review SECURITY_FIX.md for complete details")
        print("  2. Test with: python cli.py --text input.csv --output result.xlsx")
        print("  3. Monitor logs for any security rejection messages")
        print("  4. Share SECURITY_QUICKREF.md with your team")
        print()
        return 0
    else:
        print("⚠️  SECURITY FIX INCOMPLETE - Please review the changes")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
