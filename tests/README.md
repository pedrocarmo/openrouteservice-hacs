# OpenRouteService Tests

This directory contains both **unit tests** (mocked) and **integration tests** (real API) for the OpenRouteService Home Assistant integration.

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

### `test_integration.py` - Real API Integration Tests (Optional)
**Requires API key in `.env` file** - These tests make real API calls to OpenRouteService.

- ✅ API key validation (valid and invalid)
- ✅ Real address geocoding (international locations)
- ✅ Coordinate format verification (longitude, latitude)
- ✅ Real route directions (short and long distance)
- ✅ Different transportation profiles (car, walking, cycling)
- ✅ Error handling with real API responses
- ✅ Rate limit and API error scenarios

## Test Types

### Unit Tests (Default)
- **Mocked dependencies** - No API calls
- **Fast execution** (~1 second)
- **No setup required** - Works out of the box
- **Always run** in CI/CD

### Integration Tests (Optional)
- **Real API calls** - Tests actual OpenRouteService API
- **Slower execution** (~30-60 seconds)
- **Requires API key** in `.env` file
- **Optional in CI/CD** - Only runs when API key is available

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements_test.txt
```

### Setup for Integration Tests (Optional)

Create a `.env` file in the project root with your OpenRouteService API key:

```bash
# .env
ORS_API_KEY=your_api_key_here
```

Get your free API key from: https://openrouteservice.org/sign-up/

**Note**: The `.env` file is gitignored and will never be committed.

### Run Unit Tests Only (Default, Fast)

```bash
pytest
# Or explicitly:
pytest tests/test_api.py tests/test_config_flow.py tests/test_init.py
```

### Run Integration Tests Only (Requires API Key)

```bash
pytest -m integration
# Or:
pytest tests/test_integration.py
```

### Run All Tests (Unit + Integration)

```bash
pytest -m "unit or integration"
# Or run all files:
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_api.py
pytest tests/test_config_flow.py
pytest tests/test_init.py
pytest tests/test_integration.py
```

### Run Specific Test Function

```bash
pytest tests/test_integration.py::test_geocode_real_address -v
```

### Run with Coverage

```bash
pytest --cov=custom_components.openrouteservice --cov-report=html
```

### Run with Verbose Output

```bash
pytest -v
pytest -vv  # extra verbose
```

## Test Structure

Tests use pytest fixtures defined in `conftest.py`:
- `mock_ors_client` - Mock successful OpenRouteService client
- `mock_ors_client_auth_error` - Mock client with authentication error
- `mock_ors_client_timeout` - Mock client with timeout error
- `mock_ors_client_no_features` - Mock client with no geocoding results

All tests are async and use the Home Assistant test framework.

## API Rate Limits (Integration Tests)

OpenRouteService free tier has limits:
- **40 requests/minute**
- **2,000 requests/day**

The integration test suite makes approximately **15-20 API requests** per run. You can run it many times per day without hitting limits.

## Troubleshooting Integration Tests

### Tests Are Skipped
```
Skipping integration tests: No API key found in .env file
```
**Solution**: Create a `.env` file with `ORS_API_KEY=your_key_here` in the project root.

### Invalid API Key Error
```
custom_components.openrouteservice.api.InvalidAuth: Invalid API key
```
**Solution**:
1. Verify your API key at https://openrouteservice.org/
2. Check the `.env` file format is correct
3. Try regenerating your API key

### Rate Limit Exceeded
```
openrouteservice.exceptions.ApiError: Rate limit exceeded
```
**Solution**: Wait a few minutes and try again, or run specific tests:
```bash
pytest tests/test_integration.py::test_geocode_real_address -v
```

### Tests Are Slow
Integration tests take 30-60 seconds due to real API calls. This is normal. Run unit tests for fast feedback:
```bash
pytest tests/test_api.py tests/test_init.py tests/test_config_flow.py
```

## Notes

- **Unit tests** mock the OpenRouteService Python library to avoid actual API calls
- **Integration tests** skip automatically if no `.env` file is present
- The `pytest-homeassistant-custom-component` package provides HA test utilities
- Tests verify both success and error scenarios
- Service response data structure is validated
- Integration tests use real-world locations (Berlin, Paris, London, NYC, Sydney)
