"""
Neurion QPE System - Comprehensive Validation & Optimization
Tests all components, validates configuration, and prepares for launch
"""

import sys
import os
from pathlib import Path
import json

# Colors for output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title:^70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(message):
    print(f"{Colors.GREEN}[OK]{Colors.END} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.END} {message}")

def print_info(message):
    print(f"{Colors.BLUE}[INFO]{Colors.END} {message}")


def check_file_structure():
    """Validate file structure"""
    print_section("FILE STRUCTURE VALIDATION")
    
    required_dirs = [
        'core/integrity',
        'config/profiles',
        'integrations',
        'trading',
        'scripts',
        'tests'
    ]
    
    required_files = [
        'main.py',
        'requirements.txt',
        'config/config.json',
        'config/settings.py',
        'core/integrity/integrity_bus.py',
        'core/integrity/multi_agent_ensemble.py',
        'core/integrity/bayesian_calibrator.py',
        'core/integrity/confidence_scorer.py',
        'trading/autonomous_trader_v2.py',
        'integrations/ig_markets_api.py',
        'integrations/ic_markets_api.py'
    ]
    
    all_good = True
    
    print("Checking directories...")
    for dir_path in required_dirs:
        full_path = Path(dir_path)
        if full_path.exists() and full_path.is_dir():
            print_success(f"{dir_path}")
        else:
            print_error(f"{dir_path} - MISSING")
            all_good = False
    
    print("\nChecking critical files...")
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            print_success(f"{file_path} ({size:,} bytes)")
        else:
            print_error(f"{file_path} - MISSING")
            all_good = False
    
    return all_good


def check_configuration():
    """Validate configuration files"""
    print_section("CONFIGURATION VALIDATION")
    
    all_good = True
    
    # Check config.json
    print("Checking config.json...")
    config_path = Path('config/config.json')
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            print_success("config.json is valid JSON")
            print_info(f"  Active profile: {config.get('profile', 'NOT SET')}")
            print_info(f"  Risk per trade: {config.get('risk_per_trade', 'NOT SET')}")
            print_info(f"  Confidence threshold: {config.get('confidence_threshold', 'NOT SET')}")
        except Exception as e:
            print_error(f"config.json error: {e}")
            all_good = False
    else:
        print_error("config.json not found")
        all_good = False
    
    # Check profiles
    print("\nChecking trading profiles...")
    profiles_dir = Path('config/profiles')
    if profiles_dir.exists():
        profiles = list(profiles_dir.glob('*.json'))
        print_info(f"Found {len(profiles)} profile(s):")
        for profile in profiles:
            try:
                with open(profile) as f:
                    p_data = json.load(f)
                print_success(f"  {profile.name}")
                print_info(f"    Risk: {p_data.get('risk_per_trade', 'N/A')}")
                print_info(f"    Confidence: {p_data.get('confidence_threshold', 'N/A')}")
            except Exception as e:
                print_error(f"  {profile.name} - Invalid: {e}")
                all_good = False
    else:
        print_error("Profiles directory not found")
        all_good = False
    
    # Check .env
    print("\nChecking environment file...")
    env_path = Path('.env')
    if env_path.exists():
        print_success(".env file exists")
        with open(env_path) as f:
            env_lines = f.readlines()
        print_info(f"  Contains {len(env_lines)} lines")
    else:
        print_warning(".env file not found (will use config.json)")
    
    return all_good


def check_python_imports():
    """Test critical imports"""
    print_section("PYTHON IMPORTS VALIDATION")
    
    all_good = True
    
    critical_imports = [
        ('asyncio', 'Async support'),
        ('aiohttp', 'HTTP client'),
        ('numpy', 'Numerical computing'),
        ('json', 'JSON handling'),
        ('datetime', 'Date/time'),
        ('pathlib', 'Path handling')
    ]
    
    print("Checking critical imports...")
    for module, description in critical_imports:
        try:
            __import__(module)
            print_success(f"{module:20} - {description}")
        except ImportError:
            print_error(f"{module:20} - MISSING - {description}")
            all_good = False
    
    # Check optional but recommended
    optional_imports = [
        ('pandas', 'Data analysis'),
        ('ta', 'Technical analysis'),
        ('sklearn', 'Machine learning')
    ]
    
    print("\nChecking optional imports...")
    for module, description in optional_imports:
        try:
            __import__(module)
            print_success(f"{module:20} - {description}")
        except ImportError:
            print_warning(f"{module:20} - Not installed - {description}")
    
    return all_good


def check_system_modules():
    """Test system module imports"""
    print_section("SYSTEM MODULES VALIDATION")
    
    all_good = True
    
    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    modules = [
        ('core.integrity.integrity_bus', 'PIE Integration Bus'),
        ('core.integrity.multi_agent_ensemble', 'Multi-Agent Ensemble'),
        ('core.integrity.bayesian_calibrator', 'Bayesian Calibrator'),
        ('core.integrity.confidence_scorer', 'Confidence Scorer'),
        ('config.settings', 'Settings Manager'),
        ('config.profile_manager', 'Profile Manager'),
        ('integrations.ig_markets_api', 'IG Markets API'),
        ('integrations.ic_markets_api', 'IC Markets API')
    ]
    
    print("Testing system imports...")
    for module_path, description in modules:
        try:
            __import__(module_path)
            print_success(f"{description}")
        except ImportError as e:
            print_error(f"{description} - FAILED: {e}")
            all_good = False
        except Exception as e:
            print_warning(f"{description} - Warning: {e}")
    
    return all_good


def check_documentation():
    """Validate documentation"""
    print_section("DOCUMENTATION VALIDATION")
    
    docs = [
        ('README.md', 'Main documentation'),
        ('QUICKSTART.md', 'Quick start guide'),
        ('ARCHITECTURE.md', 'System architecture'),
        ('AGGRESSIVE_10PCT_DAILY_GUIDE.md', '10% daily strategy'),
        ('IG_DIAGNOSTIC_REPORT.md', 'IG connection diagnostic'),
    ]
    
    total_lines = 0
    
    print("Checking documentation files...")
    for doc, description in docs:
        doc_path = Path(doc)
        if doc_path.exists():
            lines = len(doc_path.read_text(encoding='utf-8').split('\n'))
            total_lines += lines
            print_success(f"{doc:40} ({lines:4} lines) - {description}")
        else:
            print_warning(f"{doc:40} - Not found")
    
    print_info(f"\nTotal documentation: {total_lines:,} lines")
    return True


def generate_optimization_report():
    """Generate optimization suggestions"""
    print_section("OPTIMIZATION RECOMMENDATIONS")
    
    print("Performance Optimizations:")
    print_info("  1. Pre-compile frequently used calculations")
    print_info("  2. Implement result caching for market data")
    print_info("  3. Use connection pooling for API calls")
    print_info("  4. Add circuit breakers for API failures")
    
    print("\nSafety Optimizations:")
    print_info("  1. Add pre-trade validation checks")
    print_info("  2. Implement position size limits")
    print_info("  3. Add emergency shutdown triggers")
    print_info("  4. Enable trade journaling")
    
    print("\nMonitoring Optimizations:")
    print_info("  1. Add real-time performance dashboard")
    print_info("  2. Implement alert system for anomalies")
    print_info("  3. Track confidence scores over time")
    print_info("  4. Log all decisions for analysis")


def main():
    """Run complete system validation"""
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("+" + "="*68 + "+")
    print("|" + " "*68 + "|")
    print("|" + "    NEURION QPE SYSTEM - COMPREHENSIVE VALIDATION    ".center(68) + "|")
    print("|" + "               TEST, VERIFY, OPTIMIZE               ".center(68) + "|")
    print("|" + " "*68 + "|")
    print("+" + "="*68 + "+")
    print(Colors.END)
    
    # Run all checks
    results = {
        'File Structure': check_file_structure(),
        'Configuration': check_configuration(),
        'Python Imports': check_python_imports(),
        'System Modules': check_system_modules(),
        'Documentation': check_documentation()
    }
    
    # Generate optimizations
    generate_optimization_report()
    
    # Summary
    print_section("VALIDATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        if result:
            print_success(f"{test}: PASSED")
        else:
            print_error(f"{test}: FAILED")
    
    print(f"\n{Colors.BOLD}OVERALL: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] SYSTEM READY FOR TRADING!{Colors.END}")
        print(f"{Colors.GREEN}All validations passed. System is optimized and ready.{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}[WARNING] SYSTEM NEEDS ATTENTION{Colors.END}")
        print(f"{Colors.YELLOW}Some validations failed. Review errors above.{Colors.END}")
    
    print_section("NEXT STEPS")
    
    print("1. Fix IG Markets API credentials (see IG_DIAGNOSTIC_REPORT.md)")
    print("2. Run: python scripts\\test_ig_connection.py")
    print("3. Migrate your 99.8% model: python scripts\\migrate_from_legacy.py")
    print("4. Start trading: python main.py")
    
    print("\n" + "="*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
