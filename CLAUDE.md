# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant Custom Component (HACS integration) for **OpenRouteService**, a free routing service based on OpenStreetMap data. The integration provides a service-only architecture (no sensors) that allows users to plan routes between addresses in Home Assistant automations.

**Key Design Decisions:**
- Service-only approach (no coordinator, no sensors, no polling)
- Automatic address geocoding using Pelias
- Configurable route caching to minimize API consumption
- Modern Home Assistant patterns (config flow, async API wrapper)

## Repository Structure

```
custom_components/openrouteservice/  # HA integration files
├── __init__.py                      # Entry setup & service registration
├── manifest.json                    # Integration metadata
├── const.py                         # Constants and defaults
├── config_flow.py                   # UI configuration flow
├── api.py                           # Async API client wrapper
├── cache.py                         # Route caching (Phase 2)
├── services.yaml                    # Service documentation
└── translations/
    └── en.json                      # UI strings

thoughts/                            # Research and planning
├── shared/
│   ├── research/                    # Research documents
│   └── plans/                       # Implementation plans
```

## Key Commands

### Development Setup
```bash
# Install dependencies (for development tools only)
npm install

# No build/compile step - Python integration
# Copy to Home Assistant config for testing:
# cp -r custom_components/openrouteservice /path/to/homeassistant/config/custom_components/
```

### Testing
```bash
# Validate Python syntax
python3 -m py_compile custom_components/openrouteservice/*.py

# Check Home Assistant config (requires HA installation)
hass --script check_config --config /path/to/config

# Manual testing via Home Assistant UI:
# Settings → Integrations → Add Integration → OpenRouteService
# Developer Tools → Services → openrouteservice.plan_route
```

## Architecture

### Service-Only Design

Unlike typical integrations with sensors and coordinators, this integration is **service-only**:
- No DataUpdateCoordinator (no polling)
- No sensor entities
- Routes calculated only when `openrouteservice.plan_route` service is called
- Minimizes API consumption and provides maximum flexibility

### Async Wrapper Pattern

The OpenRouteService Python library is **synchronous**, so we use `hass.async_add_executor_job` to wrap blocking calls:

```python
# In api.py
async def geocode_address(self, address: str) -> tuple[float, float]:
    result = await self.hass.async_add_executor_job(
        self._geocode_sync, address
    )
    # Process result...

def _geocode_sync(self, address: str) -> dict[str, Any]:
    return self._client.pelias_search(text=address, size=1)
```

**Pattern:** Every async method has a corresponding `_sync` helper that does the actual synchronous work.

### Coordinate Order

OpenRouteService uses `[longitude, latitude]` order (NOT `[latitude, longitude]`):
```python
# Correct
coords = (8.681495, 50.110924)  # (lon, lat) for Frankfurt

# Wrong (will fail or give incorrect routes)
coords = (50.110924, 8.681495)  # (lat, lon)
```

### Service Registration

Services are registered **once** and shared across multiple config entries:
```python
# In __init__.py async_setup_entry
if not hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE):
    # Register service
    hass.services.async_register(...)

# In async_unload_entry - only unregister if last entry
if not hass.data[DOMAIN]:
    hass.services.async_remove(DOMAIN, SERVICE_PLAN_ROUTE)
```

## Important Patterns

### Config Flow Validation

API key validation during setup:
```python
# Set unique ID BEFORE validation
await self.async_set_unique_id(user_input[CONF_API_KEY][:12])
self._abort_if_unique_id_configured()

# Then validate
api = OpenRouteServiceAPI(self.hass, user_input[CONF_API_KEY])
await api.validate_api_key()
```

### Error Handling

Use custom exceptions that map to UI error messages:
- `InvalidAuth` → "invalid_auth" in translations
- `CannotConnect` → "cannot_connect" in translations
- `ValueError` → Geocoding failures, invalid addresses
- `HomeAssistantError` → Wrap for service call errors

### Service Response Data

Services support `response_variable` for automation use:
```python
if call.return_response:
    return {
        "distance": route["summary"]["distance"],
        "duration": route["summary"]["duration"],
        "geometry": route.get("geometry"),
        "segments": route.get("segments"),
    }
```

## API Characteristics

### OpenRouteService API
- Base URL: `https://api.openrouteservice.org`
- Authentication: API key in header (`Authorization: <key>`)
- Free tier with daily request limits
- Built-in retry logic for rate limits (HTTP 429)

### Key Endpoints Used
1. **Pelias Geocoding**: `client.pelias_search(text="address")`
   - Converts addresses to coordinates
   - Returns array of features with geometry

2. **Directions**: `client.directions(coords, profile='driving-car')`
   - Requires list of (longitude, latitude) tuples
   - Returns routes with distance, duration, geometry

### Profiles
- `driving-car` - Default, car routing
- `driving-hgv` - Heavy goods vehicle
- `cycling-regular` - Bicycle routing
- `foot-walking` - Pedestrian routing
- `wheelchair` - Wheelchair-accessible routing

## Phase Implementation Status

### Phase 1: Core Integration ✅ (Planned)
- Config flow with API key validation
- `plan_route` service with automatic geocoding
- Async API wrapper with executor pattern
- Service response data for automations
- Error handling and logging

### Phase 2: Enhanced Features (Future)
- Route caching with configurable TTL
- Options flow for user preferences
- `clear_cache` service
- Advanced routing parameters (avoid highways, etc.)
- Alternative routes support

### Phase 3: Polish (Future)
- Unit tests
- HACS registration
- GitHub Actions for validation
- Comprehensive documentation

## Critical Gotchas

1. **Coordinate Order**: Always `[longitude, latitude]`, never `[latitude, longitude]`
2. **Sync Library**: OpenRouteService library is synchronous - always use `async_add_executor_job`
3. **Service Registration**: Check `has_service()` before registering to avoid duplicates
4. **Unique ID**: Must be set BEFORE validation in config flow
5. **Geocoding Failures**: Handle gracefully - not all addresses can be geocoded
6. **Rate Limits**: Free tier has limits - library retries automatically but may eventually fail

## Testing Guidelines

### Manual Testing Flow
1. Copy `custom_components/openrouteservice/` to HA config
2. Restart Home Assistant
3. Add integration via UI with valid API key
4. Test service in Developer Tools → Services:
   ```yaml
   service: openrouteservice.plan_route
   data:
     origin: "Brandenburg Gate, Berlin"
     destination: "Berlin Hauptbahnhof"
     profile: "driving-car"
   ```
5. Verify response includes `distance`, `duration`, `geometry`
6. Test in automation with `response_variable`

### Error Scenarios to Test
- Invalid API key → Should show "Invalid API key" error
- Invalid address → Should show geocoding error
- Unreachable API → Should show "Cannot connect" error
- Duplicate API key → Should abort with "already configured"

## Research Documents

All research and planning documents are in `thoughts/shared/`:
- **Research**: `thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md`
  - Comprehensive research on OpenRouteService API
  - HACS requirements and validation
  - Modern Home Assistant patterns
  - Service-only architecture decision

- **Phase 1 Plan**: `thoughts/shared/plans/2025-11-12-openrouteservice-phase1.md`
  - Detailed implementation plan
  - File-by-file code specifications
  - Success criteria and testing strategy

## Attribution Requirements

OpenRouteService free tier requires attribution:
```
© openrouteservice.org by HeiGIT | Map data © OpenStreetMap contributors
```

Should be documented in README and noted during config flow.
