"""
Richmond StoryGen Test Suite

Comprehensive testing framework with:
- Unit tests (>85% coverage)
- Integration tests
- End-to-end tests
- Security tests
- Performance tests
"""

# Test markers
MARKERS = {
    "unit": "Unit tests",
    "integration": "Integration tests",
    "e2e": "End-to-end tests",
    "security": "Security tests",
    "performance": "Performance tests",
    "slow": "Slow running tests",
    "requires_api_keys": "Tests requiring real API keys"
}

# Test configuration
TEST_CONFIG = {
    "coverage_threshold": 80,
    "performance_sla": {
        "avg_response_time": 2.0,  # seconds
        "p95_response_time": 3.0,  # seconds
        "max_response_time": 5.0,  # seconds
        "min_throughput": 10,      # requests/second
    },
    "security_requirements": {
        "min_password_length": 12,
        "token_expiry": 3600,      # seconds
        "max_login_attempts": 5,
        "rate_limit_requests": 100,
        "rate_limit_window": 60,   # seconds
    },
    "quality_gates": {
        "unit_test_pass_rate": 100,
        "integration_test_pass_rate": 100,
        "code_coverage": 80,
        "security_vulnerabilities": 0,
        "performance_degradation": 10,  # percent
    }
}

# Export test utilities
from tests.utils.test_helpers import (
    TestDataGenerator,
    TestMetrics,
    TestValidator,
    MockDataBuilder,
    APITester,
    create_test_file,
    generate_test_audio_data,
    calculate_content_hash,
    wait_for_condition
)

__all__ = [
    'MARKERS',
    'TEST_CONFIG',
    'TestDataGenerator',
    'TestMetrics',
    'TestValidator',
    'MockDataBuilder',
    'APITester',
    'create_test_file',
    'generate_test_audio_data',
    'calculate_content_hash',
    'wait_for_condition'
]