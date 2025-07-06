# Richmond StoryGen Test Suite

Comprehensive testing framework with >80% code coverage, security testing, performance validation, and E2E flows.

## Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_app.py         # Flask app tests
│   ├── test_bedrock_llm.py # LLM integration tests
│   ├── test_vectorstore.py # Vector store tests
│   ├── test_config.py      # Configuration tests
│   └── test_api_utils.py   # API utility tests
├── integration/            # Integration tests
│   └── test_api_integration.py
├── e2e/                    # End-to-end user flows
│   └── test_e2e_flows.py
├── security/               # Security and penetration tests
│   └── test_security.py
├── performance/            # Performance and load tests
│   └── test_performance.py
├── fixtures/               # Test data and fixtures
├── utils/                  # Test utilities
│   └── test_helpers.py
├── conftest.py            # Pytest configuration and fixtures
└── run_tests.py           # Test runner with coverage reporting
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests with coverage
python tests/run_tests.py --types all

# Run specific test suites
pytest tests/unit -v
pytest tests/integration -v
pytest tests/e2e -v
pytest tests/security -v
pytest tests/performance -v
```

### Test Commands

```bash
# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_app.py -v

# Run tests matching pattern
pytest -k "test_story_generation" -v

# Run with markers
pytest -m "not slow" -v        # Skip slow tests
pytest -m "security" -v        # Only security tests
pytest -m "performance" -v     # Only performance tests

# Run in parallel
pytest -n auto                 # Use all CPU cores

# Generate detailed HTML report
python tests/run_tests.py --verbose
```

## Test Categories

### 1. Unit Tests (tests/unit/)

- **Coverage Target**: >85%
- **Focus**: Individual functions and classes
- **Mocking**: External dependencies mocked
- **Speed**: Fast (<1s per test)

Key areas tested:
- Request validation
- Error handling
- Data transformations
- Configuration management
- Security decorators

### 2. Integration Tests (tests/integration/)

- **Coverage Target**: >80%
- **Focus**: Component interactions
- **Mocking**: Limited to external services
- **Speed**: Medium (1-5s per test)

Key flows tested:
- API request/response cycles
- Database interactions
- Vector search integration
- LLM communication
- Caching behavior

### 3. End-to-End Tests (tests/e2e/)

- **Coverage Target**: Critical user paths
- **Focus**: Complete user journeys
- **Mocking**: Minimal
- **Speed**: Slow (5-30s per test)

User flows tested:
- Voice to story generation
- Template-based creation
- Multi-user collaboration
- Error recovery flows
- Performance under load

### 4. Security Tests (tests/security/)

- **Coverage Target**: All endpoints and inputs
- **Focus**: Vulnerabilities and exploits
- **Tools**: Custom tests + security scanners

Security areas:
- Input validation (XSS, SQL injection)
- Authentication/authorization
- Rate limiting
- Data protection
- Cryptography
- OWASP Top 10

### 5. Performance Tests (tests/performance/)

- **Targets**: 
  - Response time: <2s average, <5s p95
  - Throughput: >10 req/s
  - Memory: <50MB growth per 100 requests
- **Tools**: pytest + locust for load testing

Performance validation:
- Response time SLAs
- Concurrent user handling
- Memory leak detection
- Database connection pooling
- Caching effectiveness

## Test Fixtures and Utilities

### Fixtures (conftest.py)

```python
@pytest.fixture
def client():
    """Flask test client"""

@pytest.fixture
def mock_pinecone():
    """Mocked Pinecone vector store"""

@pytest.fixture
def mock_bedrock():
    """Mocked AWS Bedrock client"""

@pytest.fixture
def test_config():
    """Test configuration with temp directories"""

@pytest.fixture
def performance_monitor():
    """Performance metrics collector"""
```

### Test Helpers (utils/test_helpers.py)

- `TestDataGenerator`: Generate realistic test data
- `TestValidator`: Validate responses and data
- `TestMetrics`: Collect and analyze metrics
- `APITester`: Simplified API testing
- `MockDataBuilder`: Build complex mock structures

## Coverage Requirements

### Backend Coverage (>80%)

```
Module                  Statements  Missing  Coverage
-----------------------------------------------------
app.py                        150       15      90%
bedrock/bedrock_llm.py         45        3      93%
pinecone/vectorstore.py        30        2      93%
api_utils.py                   80        8      90%
config.py                      60        5      92%
-----------------------------------------------------
TOTAL                         365       33      91%
```

### Frontend Coverage (>80%)

```
File                    % Stmts  % Branch  % Funcs  % Lines
----------------------------------------------------------
components/             88.5     82.3      90.1     87.8
hooks/                  92.1     85.5      94.2     91.3
services/               85.3     78.9      88.7     84.9
stores/                 89.7     83.2      91.5     88.9
----------------------------------------------------------
All files               88.4     82.5      90.2     87.9
```

## Quality Gates

All PRs must pass:

1. **Test Coverage**: >80% for backend and frontend
2. **Unit Tests**: 100% pass rate
3. **Integration Tests**: 100% pass rate
4. **Security Scans**: No high/critical vulnerabilities
5. **Performance**: Meet SLA requirements
6. **Linting**: No errors (flake8, ESLint)
7. **Type Checking**: No errors (mypy, TypeScript)

## CI/CD Integration

Tests run automatically on:
- Every push to main/develop
- Every pull request
- Nightly full test suite
- Pre-deployment validation

GitHub Actions workflow:
1. Linting and formatting
2. Unit tests with coverage
3. Integration tests
4. Security scanning
5. Performance benchmarks
6. Quality gate checks
7. Coverage reporting

## Security Testing Details

### Penetration Testing
- SQL injection attempts
- XSS payload testing
- Command injection
- Path traversal
- XXE attacks
- CSRF validation

### Vulnerability Scanning
- Dependency scanning (Safety)
- Code scanning (Bandit)
- Container scanning (Trivy)
- OWASP ZAP automated scans

### Authentication Testing
- JWT token validation
- Session management
- Authorization levels
- API key security

## Performance Testing Details

### Load Testing Scenarios
- Ramp up: 0-100 users over 60s
- Sustained load: 50 users for 5 minutes
- Spike test: 200 users instantly
- Soak test: 20 users for 1 hour

### Metrics Collected
- Response times (avg, p50, p95, p99)
- Throughput (requests/second)
- Error rates
- CPU/Memory usage
- Database connection pool

### Performance Benchmarks
- Homepage: <100ms
- API health: <50ms
- Story generation: <3s average
- Concurrent users: 100+
- Memory per user: <5MB

## Running Tests Locally

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Install security tools
pip install bandit safety

# Install performance tools
pip install locust psutil

# Start required services
docker-compose up -d redis
```

### Full Test Suite

```bash
# Run complete test suite with report
python tests/run_tests.py --types all --verbose

# View coverage report
open htmlcov/index.html

# View test report
open test-results/test-report.html
```

### Debugging Tests

```bash
# Run with debugging
pytest tests/unit/test_app.py -v -s --pdb

# Run single test
pytest tests/unit/test_app.py::TestHealthEndpoint::test_health_check_returns_200 -v

# Show test output
pytest tests/unit -v -s

# Profile slow tests
pytest --durations=10
```

## Writing New Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestFeatureName:
    """Test suite for feature"""
    
    def test_happy_path(self, client, mock_deps):
        """Test successful scenario"""
        # Arrange
        mock_deps.return_value = "mocked"
        
        # Act
        response = client.post('/endpoint', json={})
        
        # Assert
        assert response.status_code == 200
        assert 'expected' in response.json()
    
    def test_error_handling(self, client):
        """Test error scenarios"""
        # Test various error conditions
        
    @pytest.mark.parametrize("input,expected", [
        ("valid", 200),
        ("invalid", 400),
    ])
    def test_validation(self, client, input, expected):
        """Test input validation"""
        response = client.post('/endpoint', json={'data': input})
        assert response.status_code == expected
```

### Best Practices

1. **Test Naming**: Use descriptive names `test_<scenario>_<expected_result>`
2. **Arrange-Act-Assert**: Clear test structure
3. **One Concept**: Test one thing per test
4. **Mock External**: Mock all external dependencies
5. **Test Data**: Use fixtures and factories
6. **Cleanup**: Ensure tests don't affect each other
7. **Documentation**: Add docstrings explaining the test

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Add parent directory to Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Missing Dependencies**
   ```bash
   pip install -r requirements-test.txt
   ```

3. **Port Already in Use**
   ```bash
   # Kill process on port 5000
   lsof -ti:5000 | xargs kill -9
   ```

4. **Slow Tests**
   ```bash
   # Skip slow tests
   pytest -m "not slow"
   ```

5. **Coverage Not Collecting**
   ```bash
   # Clear coverage data
   coverage erase
   # Re-run with coverage
   pytest --cov=. --cov-report=html
   ```

## Test Maintenance

### Regular Tasks
- Update test dependencies monthly
- Review and update security test payloads
- Refresh performance benchmarks quarterly
- Archive old test reports
- Update test documentation

### Adding New Features
1. Write tests first (TDD)
2. Ensure >80% coverage
3. Add integration tests
4. Update E2E flows if needed
5. Document new test scenarios