---
date: 2025-11-11T15:38:02+0000
researcher: Claude Code
git_commit: N/A (not a git repository)
branch: N/A
repository: code
topic: "Creating a HACS component for Open Route Service with callable actions"
tags: [research, hacs, openrouteservice, home-assistant, integration, routing, service-only]
status: complete-with-decisions
last_updated: 2025-11-11T16:15:00+0000
last_updated_by: Claude Code
decisions_finalized: true
---

# Research: Creating a HACS Component for Open Route Service

**Date**: 2025-11-11T15:38:02+0000
**Researcher**: Claude Code
**Git Commit**: N/A (not a git repository)
**Branch**: N/A
**Repository**: code
**Status**: ✅ Research complete with all design decisions finalized

## Research Question

How do I create a HACS component for Open Route Service that allows
planning routes between 2 addresses and provides callable actions for use
in automations?

## Summary

Creating a modern service-only HACS integration for Open Route Service requires:

1. **API Understanding**: OpenRouteService provides a free routing API
   requiring an API key, supporting multiple transportation modes
   (driving, cycling, walking, wheelchair), with endpoints for directions,
   isochrones, and geocoding (Pelias).

2. **HACS Requirements**: Specific file structure with `manifest.json`,
   `hacs.json`, proper GitHub repository setup, and validation requirements.

3. **Modern HA Patterns**: Use config flow for UI configuration,
   separate API client module with async/await patterns, and service
   registration for callable actions. **NO coordinator or sensors needed**
   for this service-only design.

4. **Callable Actions**: Register `plan_route` service using
   `hass.services.async_register()` with voluptuous schema validation
   and support for response data to return route information to automations.

5. **Key Features**:
   - **Automatic geocoding** (HARD REQUIREMENT): Accepts address strings,
     converts to coordinates automatically
   - **Configurable caching**: Cache routes for N days (0 = disabled) to
     minimize API calls; distance-focused users cache longer, time-focused
     users set to 0
   - **Service-only design**: No sensors, reduces API consumption compared
     to HERE Maps, Google, Waze integrations
   - **Dynamic routing**: No stored routes; addresses provided at service
     call time
   - **Alternative routes**: Optional parameter to request multiple route
     options

6. **Architecture**: The reference implementation (eifinger/open_route_service)
   uses outdated patterns (YAML-only, coordinator, sensor-based, monolithic)
   and should not be directly copied - modern service-first best practices
   should be applied instead.

## Detailed Findings

### Component 1: Open Route Service API

**Capabilities and Key Features**:

- **Authentication**: API key-based authentication via HTTP headers
- **Base URL**: `https://api.openrouteservice.org`
- **Main Endpoint**: `POST /v2/directions/{profile}` where profile
  includes: `driving-car`, `driving-hgv`, `cycling-regular`,
  `foot-walking`, `wheelchair`, etc.

**Required Parameters for Route Planning**:
```json
{
  "coordinates": [[lon1, lat1], [lon2, lat2]],
  "profile": "driving-car"
}
```

**Important Notes**:
- Coordinates are `[longitude, latitude]` order (NOT lat/lon)
- Minimum 2 waypoints, maximum 50 waypoints
- Maximum route distance: 6,000 km (most profiles), 300 km (wheelchair)

**Optional Parameters Available**:
- `preference`: "fastest", "shortest", "recommended"
- `units`: "m", "km", "mi"
- `language`: Instruction language (en, de, es, etc.)
- `alternative_routes`: Get multiple route options
- `avoid_features`: highways, tollways, ferries, fords, steps
- `avoid_borders`: "all" or "controlled"
- `extra_info`: steepness, surface, waytype, tollways, etc.

**Response Structure**:
```json
{
  "routes": [{
    "summary": {
      "distance": 1234.5,
      "duration": 567.8
    },
    "geometry": "encoded_polyline_string",
    "segments": [...],
    "bbox": [...]
  }]
}
```

**Rate Limits (Free Tier)**:
- Daily request caps enforced
- Per-second rate limits
- 6,000 km maximum route distance
- Attribution required: "© openrouteservice.org by HeiGIT | Map data
  © OpenStreetMap contributors"

**Python Client Library**:
```python
import openrouteservice

client = openrouteservice.Client(key='YOUR_API_KEY')
coords = ((lon1, lat1), (lon2, lat2))
routes = client.directions(coords, profile='driving-car')
```

**Geocoding Support**:
- Pelias-based geocoding endpoint available
- Converts addresses to coordinates: `client.pelias_search(text="address")`
- Reverse geocoding: `client.pelias_reverse(point=(lon, lat))`

### Component 2: HACS Integration Requirements

**Minimum File Structure** (Service-Only Design):
```
your-repository/
├── custom_components/
│   └── openrouteservice/
│       ├── __init__.py          # Required - setup & service registration
│       ├── manifest.json        # Required
│       ├── const.py             # Required - constants
│       ├── config_flow.py       # Required - UI configuration
│       ├── api.py               # Required - API client (geocoding + routing)
│       ├── cache.py             # Required - route caching with TTL
│       ├── services.yaml        # Required - service documentation
│       └── translations/
│           └── en.json          # Required
├── hacs.json                    # Required
├── README.md                    # Required
└── LICENSE                      # Required
```

Note: No `coordinator.py` or `sensor.py` needed for service-only design.

**manifest.json Requirements**:
```json
{
  "domain": "openrouteservice",
  "name": "OpenRouteService",
  "codeowners": ["@yourusername"],
  "config_flow": true,
  "documentation": "https://github.com/user/repo",
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/user/repo/issues",
  "requirements": ["openrouteservice==2.3.3"],
  "version": "1.0.0"
}
```

**hacs.json Configuration**:
```json
{
  "name": "OpenRouteService",
  "homeassistant": "2024.1.0",
  "hacs": "1.32.0"
}
```

**HACS Validation Requirements**:
- Repository must be public on GitHub
- GitHub issues must be enabled
- Repository must have a description
- Repository must have topics/tags
- Must be registered in home-assistant/brands repository for UI assets
- Must pass HACS validation action checks

**GitHub Action for Validation**:
```yaml
name: Validate
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: HACS validation
        uses: hacs/action@main
        with:
          category: integration
```

### Component 3: Home Assistant Integration Patterns

**Modern Integration Architecture** (vs Reference Implementation):

| Aspect | Modern Pattern | Reference (Outdated) |
|--------|---------------|---------------------|
| Configuration | Config flow (UI) | YAML only |
| Data Updates | DataUpdateCoordinator | Manual async_update |
| API Client | Separate PyPI package | Embedded in sensor |
| File Structure | Modular (multiple files) | Monolithic (one file) |
| Entity Base | SensorEntity | Entity (deprecated) |
| HTTP Client | aiohttp (async) | Sync wrapped in executor |
| Error Handling | ConfigEntryNotReady, UpdateFailed | Basic try/except |

**Config Flow Implementation** (`config_flow.py`):
```python
from homeassistant import config_entries
import voluptuous as vol

class OpenRouteServiceConfigFlow(config_entries.ConfigFlow,
                                  domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Validate API key
            try:
                client = OpenRouteServiceClient(
                    user_input["api_key"]
                )
                await client.validate()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="OpenRouteService",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("api_key"): str,
            }),
            errors=errors,
        )
```

**DataUpdateCoordinator Pattern** (`coordinator.py`):
```python
from datetime import timedelta
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

class OpenRouteServiceCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, client):
        super().__init__(
            hass,
            logger,
            name="OpenRouteService",
            update_interval=timedelta(minutes=5),
        )
        self.client = client

    async def _async_update_data(self):
        try:
            async with asyncio.timeout(10):
                return await self.client.fetch_data()
        except ApiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error: {err}") from err
```

**Integration Setup** (`__init__.py`) - Service-Only:
```python
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, SupportsResponse
import voluptuous as vol

from .api import OpenRouteServiceClient
from .cache import RouteCache
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant,
                           entry: ConfigEntry) -> bool:
    # Create API client
    session = async_get_clientsession(hass)
    client = OpenRouteServiceClient(
        api_key=entry.data["api_key"],
        session=session
    )

    # Create cache
    cache = RouteCache(hass, entry.options.get("cache_days", 7))

    # Store client and cache
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "cache": cache,
    }

    # Register services
    await async_register_services(hass, entry)

    return True

async def async_unload_entry(hass: HomeAssistant,
                            entry: ConfigEntry) -> bool:
    # Unregister services (if this is the last entry)
    if len(hass.config_entries.async_entries(DOMAIN)) == 1:
        hass.services.async_remove(DOMAIN, "plan_route")
        hass.services.async_remove(DOMAIN, "clear_cache")

    # Remove data
    hass.data[DOMAIN].pop(entry.entry_id)
    return True

async def async_register_services(hass: HomeAssistant,
                                  entry: ConfigEntry):
    """Register integration services."""
    # Service implementation here (see Component 4 section)
    pass
```

**Async API Client Pattern** (`api.py`):
```python
import aiohttp

class OpenRouteServiceClient:
    def __init__(self, api_key: str, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.session = session
        self.base_url = "https://api.openrouteservice.org"

    async def get_directions(self, coordinates, profile="driving-car"):
        headers = {"Authorization": self.api_key}
        url = f"{self.base_url}/v2/directions/{profile}"

        async with self.session.post(
            url,
            json={"coordinates": coordinates},
            headers=headers,
            timeout=10
        ) as response:
            response.raise_for_status()
            return await response.json()
```

**Sensor Entity** (`sensor.py`):
```python
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

class OpenRouteServiceSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_travel_time"
        self._attr_name = "Travel Time"

    @property
    def native_value(self):
        return self.coordinator.data.get("duration")

    @property
    def extra_state_attributes(self):
        return {
            "distance": self.coordinator.data.get("distance"),
            "route": self.coordinator.data.get("route_description"),
        }
```

### Component 4: Home Assistant Callable Actions/Services

**Service Registration** (in `__init__.py`):
```python
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

# Define service schema
PLAN_ROUTE_SCHEMA = vol.Schema({
    vol.Required("origin"): cv.string,
    vol.Required("destination"): cv.string,
    vol.Optional("profile", default="driving-car"): cv.string,
    vol.Optional("preference", default="fastest"): cv.string,
})

async def async_setup_entry(hass, entry):
    # ... coordinator setup ...

    # Register service
    async def handle_plan_route(call):
        """Handle the plan_route service call."""
        origin = call.data["origin"]
        destination = call.data["destination"]
        profile = call.data["profile"]
        preference = call.data["preference"]

        # Geocode addresses if needed
        origin_coords = await coordinator.client.geocode(origin)
        dest_coords = await coordinator.client.geocode(destination)

        # Get route
        route = await coordinator.client.get_directions(
            coordinates=[origin_coords, dest_coords],
            profile=profile,
            preference=preference
        )

        # Return response data
        if call.return_response:
            return {
                "distance": route["routes"][0]["summary"]["distance"],
                "duration": route["routes"][0]["summary"]["duration"],
                "geometry": route["routes"][0]["geometry"],
                "segments": route["routes"][0]["segments"],
            }

    hass.services.async_register(
        DOMAIN,
        "plan_route",
        handle_plan_route,
        schema=PLAN_ROUTE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    return True
```

**Service Documentation** (`services.yaml`):
```yaml
plan_route:
  name: Plan route
  description: Plan a route between two addresses using OpenRouteService.
  fields:
    origin:
      name: Origin
      description: Starting address or coordinates.
      required: true
      example: "123 Main St, New York, NY"
      selector:
        text:
    destination:
      name: Destination
      description: Destination address or coordinates.
      required: true
      example: "456 Park Ave, New York, NY"
      selector:
        text:
    profile:
      name: Travel mode
      description: Transportation mode for routing.
      default: "driving-car"
      selector:
        select:
          options:
            - "driving-car"
            - "driving-hgv"
            - "cycling-regular"
            - "foot-walking"
            - "wheelchair"
    preference:
      name: Route preference
      description: Route optimization preference.
      default: "fastest"
      selector:
        select:
          options:
            - "fastest"
            - "shortest"
            - "recommended"
```

**Service Translation** (`translations/en.json`):
```json
{
  "services": {
    "plan_route": {
      "name": "Plan route",
      "description": "Plan a route between two addresses.",
      "fields": {
        "origin": {
          "name": "Origin",
          "description": "Starting address or coordinates."
        },
        "destination": {
          "name": "Destination",
          "description": "Destination address or coordinates."
        },
        "profile": {
          "name": "Travel mode",
          "description": "Transportation mode for routing."
        },
        "preference": {
          "name": "Route preference",
          "description": "Route optimization preference."
        }
      }
    }
  }
}
```

**Usage in Automation**:
```yaml
automation:
  - alias: "Get route to work"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - action: openrouteservice.plan_route
        data:
          origin: "{{ states('zone.home') }}"
          destination: "{{ states('zone.work') }}"
          profile: "driving-car"
          preference: "fastest"
        response_variable: route_info

      - action: notify.mobile_app
        data:
          message: >
            Travel time to work: {{ route_info.duration / 60 }} minutes
            Distance: {{ route_info.distance / 1000 }} km
```

### Component 5: Reference Implementation Analysis

**GitHub Repository**: https://github.com/eifinger/open_route_service

**Status**: Archived on February 18, 2025 (no longer maintained)

**Architecture Assessment**:

**Positive Patterns**:
- Entity resolution for dynamic tracking (device_tracker, person, zone)
- Rich attribute exposure (distance, route description, travel mode)
- Unit conversion support (metric/imperial)
- Delayed startup pattern (waits for Home Assistant start event)

**Outdated Patterns (Do NOT Copy)**:
- YAML-only configuration (no config flow)
- Monolithic single-file structure (all logic in sensor.py)
- No DataUpdateCoordinator usage
- Blocking API calls wrapped in executor (not true async)
- No separate API client module
- Inherits from Entity instead of SensorEntity
- Limited error handling and retry logic
- API logic mixed with data management

**Key Takeaway**: Use this as inspiration for feature ideas (dynamic
entity tracking, rich attributes) but implement with modern Home Assistant
patterns and architecture.

## Code References

All findings are based on external API documentation and Home Assistant
developer documentation - no local codebase references available.

## Architecture Insights

### Recommended Modern Architecture

For a production-ready service-only HACS integration:

1. **Separation of Concerns**:
   - `api.py` - API client with async aiohttp (geocoding + directions)
   - `cache.py` - Route caching with configurable TTL
   - `config_flow.py` - UI configuration with API key validation
   - `const.py` - Constants and configuration
   - `__init__.py` - Integration setup and service registration

2. **Configuration Strategy**:
   - Config flow for API key input and validation
   - Options flow for cache duration (days), default profile, units
   - Store user preferences in config entry
   - No coordinator needed (service-only, no polling)

3. **Service Design**:
   - `plan_route` - Calculate route between two addresses
   - Automatic address geocoding (hard requirement)
   - Configurable route caching (0 days = disabled)
   - Return comprehensive route data (distance, duration, geometry,
     segments) with support for response_variable in automations
   - Optional alternative routes
   - Include proper schema validation with voluptuous

4. **Caching Strategy**:
   - Cache key: hash(origin, destination, profile, preference)
   - Configurable TTL in days (default: TBD, 0 = disabled)
   - Persistent cache storage (JSON file in config directory)
   - `clear_cache` service for manual cache management

5. **Error Handling**:
   - ConfigEntryNotReady for API unavailability during setup
   - ConfigEntryAuthFailed for invalid API keys
   - Service call exceptions for routing errors (with helpful messages)
   - Proper rate limit handling with backoff
   - Geocoding failure handling (address not found)

6. **Testing Strategy**:
   - Config flow tests with mocked API
   - Service call tests with various parameter combinations
   - Geocoding tests (success and failure scenarios)
   - Caching tests (TTL, cache hits/misses, invalidation)
   - Error scenario coverage

## Related Research

No prior research documents found in thoughts/ directory.

## Open Questions (RESOLVED)

1. **Geocoding Strategy**: ✅ **DECISION: YES** - Include automatic address
   geocoding as a hard requirement. This is user-friendly and essential for
   the integration.

2. **Caching Strategy**: ✅ **DECISION: YES** - Implement configurable cache
   duration in days. Routes don't change frequently, especially for distance
   calculations. Users interested in real-time duration can set cache to 0
   days; others can use longer durations to minimize API calls.

3. **Entity Design**: ✅ **DECISION: Service-only** - Focus on services
   without sensors to minimize API requests. This differentiates from other
   mapping integrations (HERE Maps, Google, Waze) which use sensors.

4. **Multi-Route Support**: ✅ **DECISION: NO stored routes** - The service
   action should accept departure and destination addresses dynamically at
   call time. No pre-configured or stored routes.

5. **Alternative Routes**: ✅ **DECISION: Optional feature** - Include as
   an optional parameter (similar to cache duration), allowing users to
   request multiple route options when needed.

6. **Traffic Data**: ✅ **DECISION: Document it** - Clearly document that
   OpenRouteService provides routing based on OpenStreetMap data without
   live traffic information, but present this as a feature description
   rather than a limitation.

## Recommendations (UPDATED)

### Phase 1: Core Integration
1. Implement config flow with API key validation
2. Create async API client wrapper with:
   - Automatic address geocoding using Pelias endpoint (HARD REQUIREMENT)
   - Directions/routing endpoint support
   - Proper error handling for rate limits and auth failures
3. Register `plan_route` service with parameters:
   - `origin` (address string)
   - `destination` (address string)
   - `profile` (travel mode)
   - `preference` (fastest/shortest/recommended)
   - `alternative_routes` (optional boolean)
4. Implement route caching with configurable TTL (in days):
   - Cache key: hash of (origin, destination, profile, preference)
   - Default cache duration configurable in options flow
   - Setting to 0 disables caching for real-time data
5. Add proper error handling and logging

### Phase 2: Enhanced Features
1. Implement options flow for:
   - Default cache duration (days)
   - Default travel profile
   - Default route preference
   - Units (metric/imperial)
2. Add advanced service parameters:
   - `avoid_features` (highways, tollways, ferries, etc.)
   - `avoid_borders` (all/controlled)
   - `units` (m/km/mi)
   - `language` for route instructions
3. Expose rich route data in service response:
   - Distance and duration
   - Turn-by-turn instructions
   - Geometry (polyline)
   - Segments with elevation/surface info
4. Add cache management service (e.g., `clear_cache`)

### Phase 3: Polish & Documentation
1. Add comprehensive translations
2. Add unit tests for all components
3. Register in home-assistant/brands
4. Create detailed documentation:
   - **Routing Data Source**: Clearly explain that routing is based on
     OpenStreetMap data, providing accurate distance calculations and
     estimated travel times without live traffic data
   - Caching strategy explanation and recommendations
   - Service usage examples in automations
   - Attribution requirements for OpenRouteService
5. Add GitHub Actions for validation
6. Submit to HACS

### Architecture Decision: Service-Only Approach ✅

Based on user requirements, implementing a **service-only architecture**:

- **Primary interface**: `plan_route` service (no sensors)
- **Dynamic routing**: No stored routes; addresses provided at call time
- **Focus**: Minimize API requests and provide flexibility for automations
- **Benefit**: Zero polling overhead; routes calculated only when needed
- **Differentiation**: Unlike HERE Maps, Google, and Waze integrations
  which use sensors

This approach:
- Reduces API consumption (important for free tier)
- Provides maximum flexibility (addresses specified per automation)
- Aligns with modern Home Assistant service patterns
- Avoids unnecessary entity creation

## Attribution Requirements

When using OpenRouteService free API, the integration must ensure users
provide proper attribution in their Home Assistant installations:

```
© openrouteservice.org by HeiGIT | Map data © OpenStreetMap contributors
```

Consider adding this to the integration's README and as a note in the
config flow.

## Final Summary

Creating a modern service-only HACS integration for OpenRouteService requires:

- **Modern HA patterns**: Config flow, async API client, service registration
  (NO coordinator or sensors needed)
- **Service-only design**: Callable actions for dynamic route planning
- **Automatic geocoding**: Hard requirement for address-to-coordinate conversion
- **Intelligent caching**: Configurable TTL in days (0 = disabled) to reduce
  API calls while providing flexibility
- **Proper structure**: Modular files (api.py, cache.py, config_flow.py)
  following HACS requirements
- **Error handling**: Graceful degradation, rate limit handling, retry logic
- **Documentation**: services.yaml, translations, comprehensive README with
  routing data source explanation (not framed as limitation)

The reference implementation provides useful feature ideas but uses
outdated architectural patterns (sensors, coordinator, YAML-only). A
ground-up implementation using modern Home Assistant service-first best
practices is recommended.

**Key Differentiators**: Unlike HERE Maps, Google Maps, and Waze
integrations that use sensors and polling, this integration uses a
service-only approach to minimize API consumption and maximize flexibility.
