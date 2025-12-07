#!/usr/bin/env python3
"""
Test runner for the AI in Classics project.
Run this script to execute all tests in the project.
"""

import unittest
import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def run_tests():
    """Run all tests in the 'tests' directory."""
    # Discover and run all tests
    test_dir = os.path.join(project_root, 'tests')
    
    print("=" * 70)
    print(f"Running tests from {test_dir}")
    print("=" * 70)
    
    # Create test suite and run tests
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print(f"Test Results: {result.testsRun} tests ran.")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    
    return len(result.failures) + len(result.errors) == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
