#!/usr/bin/env python3
"""
Comprehensive test runner with coverage reporting and quality gates
"""
import sys
import os
import argparse
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET


class TestRunner:
    """Orchestrate test execution with coverage and reporting"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.test_results: Dict[str, Any] = {
            "start_time": time.time(),
            "suites": {},
            "coverage": {},
            "quality_gates": {}
        }
    
    def run_command(self, command: List[str], env: Optional[Dict] = None) -> subprocess.CompletedProcess:
        """Run a command and capture output"""
        if self.verbose:
            print(f"Running: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env={**os.environ, **(env or {})}
        )
        
        if self.verbose and result.returncode != 0:
            print(f"Error output: {result.stderr}")
        
        return result
    
    def run_unit_tests(self) -> bool:
        """Run unit tests"""
        print("\n🧪 Running Unit Tests...")
        
        result = self.run_command([
            "python", "-m", "pytest",
            "tests/unit",
            "-v",
            "--tb=short",
            "--junitxml=test-results/unit-tests.xml",
            "--cov=.",
            "--cov-report=xml:coverage-unit.xml",
            "--cov-report=term-missing"
        ])
        
        self.test_results["suites"]["unit"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        return result.returncode == 0
    
    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        print("\n🔗 Running Integration Tests...")
        
        result = self.run_command([
            "python", "-m", "pytest",
            "tests/integration",
            "-v",
            "--tb=short",
            "--junitxml=test-results/integration-tests.xml",
            "--cov=.",
            "--cov-append",
            "--cov-report=xml:coverage-integration.xml"
        ])
        
        self.test_results["suites"]["integration"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        return result.returncode == 0
    
    def run_e2e_tests(self) -> bool:
        """Run end-to-end tests"""
        print("\n🎯 Running End-to-End Tests...")
        
        # Start the application
        app_process = subprocess.Popen(
            ["python", "app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for app to start
        time.sleep(3)
        
        try:
            result = self.run_command([
                "python", "-m", "pytest",
                "tests/e2e",
                "-v",
                "--tb=short",
                "--junitxml=test-results/e2e-tests.xml",
                "-m", "not slow"  # Skip slow tests in regular runs
            ])
            
            self.test_results["suites"]["e2e"] = {
                "passed": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr
            }
            
            return result.returncode == 0
            
        finally:
            # Stop the application
            app_process.terminate()
            app_process.wait(timeout=5)
    
    def run_security_tests(self) -> bool:
        """Run security tests"""
        print("\n🔒 Running Security Tests...")
        
        result = self.run_command([
            "python", "-m", "pytest",
            "tests/security",
            "-v",
            "--tb=short",
            "--junitxml=test-results/security-tests.xml",
            "-m", "not slow"
        ])
        
        self.test_results["suites"]["security"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        # Run additional security tools
        self.run_security_scanning()
        
        return result.returncode == 0
    
    def run_performance_tests(self) -> bool:
        """Run performance tests"""
        print("\n⚡ Running Performance Tests...")
        
        result = self.run_command([
            "python", "-m", "pytest",
            "tests/performance",
            "-v",
            "--tb=short",
            "--junitxml=test-results/performance-tests.xml",
            "-m", "not slow"
        ])
        
        self.test_results["suites"]["performance"] = {
            "passed": result.returncode == 0,
            "output": result.stdout,
            "errors": result.stderr
        }
        
        return result.returncode == 0
    
    def run_security_scanning(self):
        """Run additional security scanning tools"""
        print("\n🔍 Running Security Scans...")
        
        # Bandit for Python security issues
        bandit_result = self.run_command([
            "bandit", "-r", ".",
            "-f", "json",
            "-o", "test-results/bandit-report.json",
            "--skip", "B101"  # Skip assert_used test
        ])
        
        # Safety check for known vulnerabilities
        safety_result = self.run_command([
            "safety", "check",
            "--json",
            "--output", "test-results/safety-report.json"
        ])
        
        self.test_results["security_scans"] = {
            "bandit": bandit_result.returncode == 0,
            "safety": safety_result.returncode == 0
        }
    
    def calculate_coverage(self) -> Dict[str, float]:
        """Calculate test coverage from XML reports"""
        coverage_files = [
            "coverage-unit.xml",
            "coverage-integration.xml"
        ]
        
        total_coverage = 0
        file_count = 0
        
        for coverage_file in coverage_files:
            if os.path.exists(coverage_file):
                tree = ET.parse(coverage_file)
                root = tree.getroot()
                
                # Get coverage percentage
                coverage_percent = float(root.attrib.get('line-rate', 0)) * 100
                total_coverage += coverage_percent
                file_count += 1
        
        if file_count > 0:
            average_coverage = total_coverage / file_count
        else:
            average_coverage = 0
        
        # Combine coverage reports
        self.run_command([
            "coverage", "combine"
        ])
        
        # Generate final report
        result = self.run_command([
            "coverage", "report",
            "--precision=2"
        ])
        
        # Parse coverage from output
        lines = result.stdout.strip().split('\n')
        if lines and 'TOTAL' in lines[-1]:
            parts = lines[-1].split()
            if len(parts) >= 4:
                try:
                    average_coverage = float(parts[-1].rstrip('%'))
                except ValueError:
                    pass
        
        self.test_results["coverage"] = {
            "total": average_coverage,
            "report": result.stdout
        }
        
        return {"total": average_coverage}
    
    def check_quality_gates(self) -> bool:
        """Check if quality gates pass"""
        print("\n📊 Checking Quality Gates...")
        
        gates_passed = True
        gates = {
            "coverage": {
                "threshold": 80,
                "actual": self.test_results["coverage"].get("total", 0),
                "passed": False
            },
            "unit_tests": {
                "passed": self.test_results["suites"].get("unit", {}).get("passed", False)
            },
            "integration_tests": {
                "passed": self.test_results["suites"].get("integration", {}).get("passed", False)
            },
            "security_tests": {
                "passed": self.test_results["suites"].get("security", {}).get("passed", False)
            }
        }
        
        # Check coverage threshold
        coverage = gates["coverage"]["actual"]
        gates["coverage"]["passed"] = coverage >= gates["coverage"]["threshold"]
        
        if not gates["coverage"]["passed"]:
            print(f"❌ Coverage {coverage:.2f}% is below threshold of {gates['coverage']['threshold']}%")
            gates_passed = False
        else:
            print(f"✅ Coverage {coverage:.2f}% meets threshold")
        
        # Check test suites
        for suite in ["unit_tests", "integration_tests", "security_tests"]:
            if not gates[suite]["passed"]:
                print(f"❌ {suite.replace('_', ' ').title()} failed")
                gates_passed = False
            else:
                print(f"✅ {suite.replace('_', ' ').title()} passed")
        
        self.test_results["quality_gates"] = gates
        self.test_results["quality_gates_passed"] = gates_passed
        
        return gates_passed
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n📝 Generating Test Report...")
        
        # Create test results directory
        os.makedirs("test-results", exist_ok=True)
        
        # Add timing information
        self.test_results["end_time"] = time.time()
        self.test_results["duration"] = self.test_results["end_time"] - self.test_results["start_time"]
        
        # Write JSON report
        with open("test-results/test-report.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        
        # Generate HTML report
        self.generate_html_report()
        
        print(f"\n📊 Test Report saved to test-results/test-report.html")
    
    def generate_html_report(self):
        """Generate HTML test report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Richmond StoryGen Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #333; color: white; padding: 20px; }
        .summary { background: #f0f0f0; padding: 15px; margin: 20px 0; }
        .suite { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
        .passed { color: green; }
        .failed { color: red; }
        .coverage-bar { background: #eee; height: 20px; margin: 10px 0; }
        .coverage-fill { background: green; height: 100%; }
        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Richmond StoryGen Test Report</h1>
        <p>Generated: {timestamp}</p>
        <p>Duration: {duration:.2f} seconds</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Coverage: {coverage:.2f}%</p>
        <div class="coverage-bar">
            <div class="coverage-fill" style="width: {coverage}%"></div>
        </div>
        <p>Quality Gates: <span class="{gates_class}">{gates_status}</span></p>
    </div>
    
    <h2>Test Suites</h2>
    {suites_html}
    
    <h2>Coverage Report</h2>
    <pre>{coverage_report}</pre>
</body>
</html>
"""
        
        # Generate suites HTML
        suites_html = ""
        for suite_name, suite_data in self.test_results["suites"].items():
            status_class = "passed" if suite_data.get("passed", False) else "failed"
            status_text = "PASSED" if suite_data.get("passed", False) else "FAILED"
            
            suites_html += f"""
    <div class="suite">
        <h3>{suite_name.replace('_', ' ').title()}</h3>
        <p>Status: <span class="{status_class}">{status_text}</span></p>
    </div>
"""
        
        # Fill template
        html = html_template.format(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            duration=self.test_results["duration"],
            coverage=self.test_results["coverage"].get("total", 0),
            gates_class="passed" if self.test_results.get("quality_gates_passed", False) else "failed",
            gates_status="PASSED" if self.test_results.get("quality_gates_passed", False) else "FAILED",
            suites_html=suites_html,
            coverage_report=self.test_results["coverage"].get("report", "No coverage report available")
        )
        
        with open("test-results/test-report.html", "w") as f:
            f.write(html)
    
    def run_all_tests(self, test_types: List[str]) -> bool:
        """Run all specified test types"""
        all_passed = True
        
        test_runners = {
            "unit": self.run_unit_tests,
            "integration": self.run_integration_tests,
            "e2e": self.run_e2e_tests,
            "security": self.run_security_tests,
            "performance": self.run_performance_tests
        }
        
        for test_type in test_types:
            if test_type in test_runners:
                passed = test_runners[test_type]()
                if not passed:
                    all_passed = False
            else:
                print(f"⚠️  Unknown test type: {test_type}")
        
        # Calculate coverage
        self.calculate_coverage()
        
        # Check quality gates
        gates_passed = self.check_quality_gates()
        
        # Generate report
        self.generate_report()
        
        return all_passed and gates_passed


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Richmond StoryGen tests")
    parser.add_argument(
        "--types",
        nargs="+",
        choices=["unit", "integration", "e2e", "security", "performance", "all"],
        default=["all"],
        help="Types of tests to run"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Determine which tests to run
    if "all" in args.types:
        test_types = ["unit", "integration", "e2e", "security", "performance"]
    else:
        test_types = args.types
    
    # Create test runner
    runner = TestRunner(verbose=args.verbose)
    
    print("🚀 Richmond StoryGen Test Suite")
    print("=" * 50)
    
    # Run tests
    success = runner.run_all_tests(test_types)
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()