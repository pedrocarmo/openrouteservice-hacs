# OpenRouteService Integration Tests

This directory contains unit tests for the OpenRouteService Home Assistant integration.

## Test Coverage

### `test_api.py` - API Client Tests
- ✅ API key validation (success, invalid auth, timeout)
- ✅ Address geocoding (success, no results, API errors)
- ✅ Route directions (success, different profiles, no route found, API errors)
- ✅ Error handling for all API methods

### `test_config_flow.py` - Configuration Flow Tests
- ✅ Form display
- ✅ Successful configuration
- ✅ Invalid authentication error handling
- ✅ Connection error handling
- ✅ Unknown error handling
- ✅ Duplicate API key prevention
- ✅ Description placeholders

### `test_init.py` - Integration Setup Tests
- ✅ Config entry setup
- ✅ Service registration (single and multiple entries)
- ✅ Config entry unload
- ✅ Service persistence with multiple entries
- ✅ Service calls with various parameters
- ✅ Service calls with default values
- ✅ Error handling (geocoding errors, API errors)
- ✅ Response handling (with and without return_response)

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements_test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_api.py
pytest tests/test_config_flow.py
pytest tests/test_init.py
```

### Run with Coverage

```bash
pytest --cov=custom_components.openrouteservice --cov-report=html
```

### Run with Verbose Output

```bash
pytest -v
```

## Test Structure

Tests use pytest fixtures defined in `conftest.py`:
- `mock_ors_client` - Mock successful OpenRouteService client
- `mock_ors_client_auth_error` - Mock client with authentication error
- `mock_ors_client_timeout` - Mock client with timeout error
- `mock_ors_client_no_features` - Mock client with no geocoding results

All tests are async and use the Home Assistant test framework.

## Notes

- Tests mock the OpenRouteService Python library to avoid actual API calls
- The `pytest-homeassistant-custom-component` package provides HA test utilities
- Tests verify both success and error scenarios
- Service response data structure is validated
