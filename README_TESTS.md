# Running Tests

## Prerequisites

```bash
pip install pytest pytest-asyncio
```

## Run All Tests

```bash
pytest tests/
```

## Run Cache Tests Only

```bash
pytest tests/test_cache.py -v
```

## Run with Coverage

```bash
pytest tests/ --cov=custom_components.openrouteservice --cov-report=html
```

## Test Output

Tests should show:
- Cache disabled when TTL = 0
- Cache hit/miss scenarios work correctly
- Cache persists across restarts
- Expired entries are removed
- Case-insensitive geocoding lookups
- Route cache differentiates by profile and units
