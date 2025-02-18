# scripts/test_runner.py
import sys
import argparse
from typing import List
import pytest

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test runner for AINewsJohnStewart")
    parser.add_argument(
        "--agent",
        choices=["satirist", "all"],
        default="all",
        help="Specify which agent's tests to run"
    )
    parser.add_argument(
        "--test-type",
        choices=["unit", "integration", "all"],
        default="all",
        help="Specify type of tests to run"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--coverage-threshold",
        type=int,
        default=80,
        help="Minimum required coverage percentage"
    )
    return parser.parse_args()

def build_pytest_args(args: argparse.Namespace) -> List[str]:
    """Build pytest command arguments based on input args"""
    pytest_args = ["-v"]
    
    # Add parallel execution if requested
    if args.parallel:
        pytest_args.extend(["-n", "auto"])
    
    # Add test selection markers
    markers = []
    if args.test_type != "all":
        markers.append(args.test_type)
    if args.agent != "all":
        markers.append(args.agent)
    
    if markers:
        pytest_args.append("-m" + " and ".join(markers))
    
    # Add coverage settings
    pytest_args.extend([
        f"--cov-fail-under={args.coverage_threshold}",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_reports/html",
    ])
    
    return pytest_args

def run_tests(args: List[str]) -> int:
    """Run pytest with given arguments"""
    return pytest.main(args)

def run_unit_tests() -> int:
    """Run only unit tests"""
    return run_tests(["-v", "-m", "unit"])

def run_integration_tests() -> int:
    """Run only integration tests"""
    return run_tests(["-v", "-m", "integration"])

def run_all_tests() -> int:
    """Run all tests"""
    return run_tests(["-v"])

def main() -> int:
    """Main entry point for test runner"""
    args = parse_args()
    pytest_args = build_pytest_args(args)
    return run_tests(pytest_args)

if __name__ == "__main__":
    sys.exit(main())
