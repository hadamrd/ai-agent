import sys
import pytest

def run_satirist_tests():
    """Entry point for running satirist integration tests"""
    sys.exit(pytest.main(["AINewsJohnStewart/tests/test_satirist_agent_integration.py", "-v"]))