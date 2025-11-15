# Seed Planter API - Test Suite

Professional black box test suite for the Seed Planter API.

## Overview

This test suite provides comprehensive black box testing for the Seed Planter API, designed to be used for:
- Local development validation
- CI/CD pipeline verification
- Post-deployment smoke tests
- Integration testing

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_health.py           # Health check and basic endpoint tests
├── test_projects_api.py     # Project creation API tests
├── test_websocket.py        # WebSocket functionality tests
└── test_integration.py      # End-to-end integration tests
```

## Running Tests

### Prerequisites

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Health checks only (fast)
pytest tests/test_health.py

# API tests
pytest tests/test_projects_api.py

# Integration tests
pytest -m integration

# Smoke tests (quick validation)
pytest -m smoke
```

### Run Against Deployed API

```bash
# Set the API URL
export API_BASE_URL=https://seed-planter-api-pmxej6pldq-uc.a.run.app

# Run tests
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html --cov-report=term
```

### Run with Verbose Output

```bash
pytest -v -s
```

## Test Categories

### Health Tests (`test_health.py`)
- ✅ Root endpoint availability
- ✅ Response format validation
- ✅ Service metadata verification
- ✅ CORS headers
- ✅ Response time validation

### Projects API Tests (`test_projects_api.py`)
- ✅ Project creation (happy path)
- ✅ Request validation (422 errors)
- ✅ Response structure validation
- ✅ UUID format verification
- ✅ WebSocket URL format
- ✅ Concurrent request handling
- ✅ Edge cases (empty strings, special characters)

### WebSocket Tests (`test_websocket.py`)
- ✅ WebSocket endpoint availability
- ✅ Connection establishment
- ✅ Progress update reception (requires actual project)
- ✅ URL format validation

### Integration Tests (`test_integration.py`)
- ✅ Complete project creation flow
- ✅ Concurrent request handling
- ✅ Error handling consistency
- ✅ Special character handling
- ✅ Long input handling
- ✅ Health check under load

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run API Tests
  env:
    API_BASE_URL: ${{ steps.deploy.outputs.url }}
  run: |
    cd apps/seed-planter-api
    pip install -r requirements.txt
    pytest -v --tb=short
```

### Post-Deployment Verification

```bash
# Quick smoke test
pytest -m smoke --tb=short

# Full validation
pytest --tb=short
```

## Test Markers

- `@pytest.mark.integration` - Integration tests (may be slower)
- `@pytest.mark.slow` - Slow running tests
- `@pytest.mark.websocket` - WebSocket-specific tests
- `@pytest.mark.smoke` - Quick smoke tests

## Environment Variables

- `API_BASE_URL` - Base URL of the API (default: `http://localhost:8000`)

## Expected Results

All tests should pass on a healthy deployment:
- Health tests: ~10 tests
- Projects API tests: ~20 tests
- WebSocket tests: ~3 tests (some skipped without real projects)
- Integration tests: ~7 tests

Total: **~40 tests** covering all major API functionality

## Troubleshooting

### Connection Refused
```bash
# Check if API is running
curl $API_BASE_URL/

# Check API logs
gcloud logging read "resource.type=cloud_run_revision"
```

### Tests Timing Out
```bash
# Increase timeout in conftest.py
# Or run with longer timeout
pytest --timeout=60
```

### WebSocket Tests Failing
```bash
# WebSocket tests require actual project creation
# Some are marked as @pytest.mark.skip
# Run only non-skipped tests
pytest -v -k "not skip"
```

## Contributing

When adding new tests:
1. Follow the existing naming convention (`test_*`)
2. Add appropriate markers
3. Include docstrings explaining what is tested
4. Keep tests independent and idempotent
5. Use fixtures from `conftest.py`
