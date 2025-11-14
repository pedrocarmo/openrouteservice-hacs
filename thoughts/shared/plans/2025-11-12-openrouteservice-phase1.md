# OpenRouteService HACS Integration - Phase 1 Implementation Plan

## Overview

Phase 1 focuses on building the **core service-only integration** for OpenRouteService with Home Assistant. This phase includes config flow for API key setup, a callable `plan_route` service with automatic address geocoding, and proper error handling. **No caching, no sensors, no options flow** - those are deferred to Phase 2.

**Key Goals:**
- Modern config flow with UI-based API key configuration
- `plan_route` service that accepts addresses (not coordinates)
- Automatic geocoding using Pelias
- Service returns comprehensive route data for use in automations
- Clean, modular code structure following 2024-2025 best practices

## Current State Analysis

Starting from a fresh directory with only:
- `thoughts/` directory containing research
- `node_modules/`, `package.json`, `package-lock.json` (not relevant to Python integration)
- `.claude/` directory for Claude Code configuration

**No existing code** - building from scratch.

### Key Discoveries from Research:

1. **Config Flow Patterns** (`thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md:223-260`):
   - Use `async_get_clientsession(hass)` for API validation
   - Implement `async_set_unique_id()` BEFORE validation
   - Use custom exceptions (`InvalidAuth`, `CannotConnect`) that map to error codes
   - Validate API key with minimal test request during config flow

2. **Service Registration Patterns** (`thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md:290-340`):
   - Register services in `async_setup_entry` (not `async_setup`)
   - Use `SupportsResponse.OPTIONAL` for services that return data
   - Check `call.return_response` to determine if caller wants data
   - Unregister services in `async_unload_entry` when last entry removed

3. **OpenRouteService API** (`thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md:71-138`):
   - Library is **synchronous** - must wrap in executor for async
   - Coordinates are `[longitude, latitude]` order (NOT lat/lon)
   - Pelias geocoding: `client.pelias_search(text="address")` returns features array
   - Directions: `client.directions(coords, profile='driving-car')`
   - Built-in retry logic for rate limits (HTTP 429)

4. **Architecture Decision** (`thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md:707-724`):
   - **Service-only approach** (no coordinator, no sensors)
   - Minimizes API consumption
   - Maximum flexibility for automations
   - Routes calculated only when service is called

## Desired End State

After Phase 1 completion:

1. **File Structure**:
   ```
   custom_components/
   └── openrouteservice/
       ├── __init__.py          # Entry setup, service registration
       ├── manifest.json        # Integration metadata
       ├── const.py             # Constants and defaults
       ├── config_flow.py       # UI configuration flow
       ├── api.py               # Async API client wrapper
       ├── services.yaml        # Service documentation
       └── translations/
           └── en.json          # UI strings
   ```

2. **Functional Integration**:
   - User can add integration via UI (Settings → Integrations → Add Integration)
   - Config flow validates API key during setup
   - `openrouteservice.plan_route` service available in automations
   - Service accepts addresses (strings), automatically geocodes them
   - Service returns route distance, duration, geometry, and segments
   - Proper error handling for invalid addresses, API failures, rate limits

3. **Verification**:
   ```yaml
   # Example automation that uses the service
   automation:
     - alias: "Morning commute check"
       trigger:
         - platform: time
           at: "07:00:00"
       action:
         - service: openrouteservice.plan_route
           data:
             origin: "123 Main St, Berlin, Germany"
             destination: "Alexanderplatz, Berlin, Germany"
             profile: "driving-car"
             preference: "fastest"
           response_variable: route
         - service: notify.mobile_app
           data:
             message: "Commute: {{ (route.duration / 60) | round(0) }} min, {{ (route.distance / 1000) | round(1) }} km"
   ```

## What We're NOT Doing (Phase 2)

- ❌ Route caching (persistent or in-memory)
- ❌ Options flow for user preferences
- ❌ Sensors for stored routes
- ❌ DataUpdateCoordinator
- ❌ Alternative routes parameter
- ❌ Advanced routing features (avoid highways, avoid tolls, etc.)
- ❌ Unit tests (recommend separate testing phase)
- ❌ HACS registration and GitHub Actions

## Implementation Approach

**Strategy**: Build modular, async-first architecture using modern Home Assistant patterns. Wrap synchronous OpenRouteService library with async executor pattern for non-blocking I/O.

**Key Technical Decisions**:
1. Use `run_in_executor` to wrap sync OpenRouteService client
2. Validate API key during config flow with lightweight request
3. Use voluptuous schemas for service parameter validation
4. Return comprehensive route data for maximum automation flexibility
5. Follow Home Assistant error handling conventions

---

## Phase 1: Core Service-Only Integration

### Overview
Build the minimal viable integration: config flow + `plan_route` service with automatic geocoding.

### Changes Required

#### 1. Project Structure & Metadata

**File**: `custom_components/openrouteservice/manifest.json`
**Changes**: Create integration manifest

```json
{
  "domain": "openrouteservice",
  "name": "OpenRouteService",
  "codeowners": ["@pedrocarmo"],
  "config_flow": true,
  "documentation": "https://github.com/pedrocarmo/open-route-service-hacs",
  "integration_type": "service",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/pedrocarmo/open-route-service-hacs/issues",
  "requirements": ["openrouteservice==2.3.3"],
  "version": "0.1.0"
}
```

**Reasoning**:
- `integration_type: "service"` signals this is service-only (no entities)
- `config_flow: true` enables UI configuration
- `requirements` ensures Home Assistant installs the Python package

---

**File**: `custom_components/openrouteservice/const.py`
**Changes**: Define constants

```python
"""Constants for the OpenRouteService integration."""

DOMAIN = "openrouteservice"

# Config
CONF_API_KEY = "api_key"

# Services
SERVICE_PLAN_ROUTE = "plan_route"

# Service parameters
ATTR_ORIGIN = "origin"
ATTR_DESTINATION = "destination"
ATTR_PROFILE = "profile"
ATTR_PREFERENCE = "preference"

# Defaults
DEFAULT_PROFILE = "driving-car"
DEFAULT_PREFERENCE = "fastest"

# Profiles
PROFILES = [
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "foot-walking",
    "wheelchair",
]

# Preferences
PREFERENCES = [
    "fastest",
    "shortest",
    "recommended",
]

# API
API_BASE_URL = "https://api.openrouteservice.org"
API_TIMEOUT = 30
```

**Reasoning**: Centralized constants prevent magic strings and make changes easier.

---

#### 2. API Client Module

**File**: `custom_components/openrouteservice/api.py`
**Changes**: Create async API wrapper

```python
"""OpenRouteService API client wrapper."""
import asyncio
import logging
from typing import Any

import openrouteservice
from openrouteservice import exceptions

from homeassistant.core import HomeAssistant

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class OpenRouteServiceAPI:
    """Async wrapper for OpenRouteService API."""

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        """Initialize the API client."""
        self.hass = hass
        self.api_key = api_key
        self._client = openrouteservice.Client(
            key=api_key,
            base_url=API_BASE_URL,
            timeout=API_TIMEOUT,
            retry_over_query_limit=True,
        )

    async def validate_api_key(self) -> dict[str, Any]:
        """Validate the API key by making a test request."""
        try:
            # Use pelias_search as a lightweight validation method
            result = await self.hass.async_add_executor_job(
                self._validate_sync
            )
            return result
        except exceptions.ApiError as err:
            if "401" in str(err) or "403" in str(err):
                raise InvalidAuth("Invalid API key") from err
            raise CannotConnect(f"API error: {err}") from err
        except exceptions.Timeout as err:
            raise CannotConnect("Request timeout") from err
        except Exception as err:
            raise CannotConnect(f"Unexpected error: {err}") from err

    def _validate_sync(self) -> dict[str, Any]:
        """Synchronous validation helper."""
        # Make a minimal request to validate the API key
        result = self._client.pelias_search(text="test", size=1, validate=False)
        return {"valid": True, "features_count": len(result.get("features", []))}

    async def geocode_address(self, address: str) -> tuple[float, float]:
        """
        Geocode an address to coordinates.

        Returns (longitude, latitude) tuple.
        Raises ValueError if address cannot be geocoded.
        """
        try:
            result = await self.hass.async_add_executor_job(
                self._geocode_sync, address
            )

            if not result.get("features"):
                raise ValueError(f"Could not geocode address: {address}")

            # Extract coordinates [longitude, latitude]
            coords = result["features"][0]["geometry"]["coordinates"]
            _LOGGER.debug(
                "Geocoded '%s' to [%s, %s]", address, coords[0], coords[1]
            )
            return tuple(coords)

        except exceptions.ApiError as err:
            raise CannotConnect(f"Geocoding API error: {err}") from err
        except exceptions.Timeout as err:
            raise CannotConnect("Geocoding timeout") from err

    def _geocode_sync(self, address: str) -> dict[str, Any]:
        """Synchronous geocoding helper."""
        return self._client.pelias_search(text=address, size=1, validate=False)

    async def get_directions(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str = "driving-car",
        preference: str = "fastest",
    ) -> dict[str, Any]:
        """
        Get directions between two coordinates.

        Args:
            origin: (longitude, latitude) tuple
            destination: (longitude, latitude) tuple
            profile: Transportation mode
            preference: Route optimization preference

        Returns:
            Route information with distance, duration, geometry, etc.
        """
        try:
            result = await self.hass.async_add_executor_job(
                self._directions_sync,
                [origin, destination],
                profile,
                preference,
            )

            if not result.get("routes"):
                raise ValueError("No route found between origin and destination")

            route = result["routes"][0]
            _LOGGER.debug(
                "Route calculated: %.2f km, %.2f min",
                route["summary"]["distance"] / 1000,
                route["summary"]["duration"] / 60,
            )
            return route

        except exceptions.ApiError as err:
            raise CannotConnect(f"Directions API error: {err}") from err
        except exceptions.Timeout as err:
            raise CannotConnect("Directions timeout") from err

    def _directions_sync(
        self,
        coords: list[tuple[float, float]],
        profile: str,
        preference: str,
    ) -> dict[str, Any]:
        """Synchronous directions helper."""
        return self._client.directions(
            coords,
            profile=profile,
            format="geojson",
            preference=preference,
            units="m",
            geometry=True,
            instructions=True,
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate invalid authentication."""
```

**Reasoning**:
- Wraps sync OpenRouteService client with `async_add_executor_job`
- Separates sync helpers (`_validate_sync`, `_geocode_sync`, `_directions_sync`)
- Custom exceptions match Home Assistant conventions
- Returns coordinates as tuples for type safety
- Comprehensive logging for debugging

---

#### 3. Config Flow

**File**: `custom_components/openrouteservice/config_flow.py`
**Changes**: Implement UI configuration

```python
"""Config flow for OpenRouteService integration."""
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import CannotConnect, InvalidAuth, OpenRouteServiceAPI
from .const import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)


class OpenRouteServiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenRouteService."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Set unique ID based on API key prefix
                await self.async_set_unique_id(user_input[CONF_API_KEY][:12])
                self._abort_if_unique_id_configured()

                # Validate API key
                api = OpenRouteServiceAPI(self.hass, user_input[CONF_API_KEY])
                await api.validate_api_key()

                return self.async_create_entry(
                    title="OpenRouteService",
                    data=user_input,
                )

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_API_KEY): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "signup_url": "https://openrouteservice.org/sign-up"
            },
        )
```

**File**: `custom_components/openrouteservice/translations/en.json`
**Changes**: UI strings for config flow

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to OpenRouteService",
        "description": "Enter your OpenRouteService API key. Don't have one? Sign up at {signup_url}",
        "data": {
          "api_key": "API Key"
        }
      }
    },
    "error": {
      "invalid_auth": "Invalid API key. Please check your key and try again.",
      "cannot_connect": "Unable to connect to OpenRouteService API. Please check your internet connection and try again.",
      "unknown": "Unexpected error occurred. Please try again."
    },
    "abort": {
      "already_configured": "This API key is already configured."
    }
  }
}
```

**Reasoning**:
- Clean validation flow with proper error mapping
- Uses API key prefix as unique ID to prevent duplicates
- Provides helpful signup URL in description
- Follows Home Assistant translation patterns

---

#### 4. Integration Setup & Service Registration

**File**: `custom_components/openrouteservice/__init__.py`
**Changes**: Setup entry and register service

```python
"""The OpenRouteService integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api import CannotConnect, OpenRouteServiceAPI
from .const import (
    ATTR_DESTINATION,
    ATTR_ORIGIN,
    ATTR_PREFERENCE,
    ATTR_PROFILE,
    DEFAULT_PREFERENCE,
    DEFAULT_PROFILE,
    DOMAIN,
    PREFERENCES,
    PROFILES,
    SERVICE_PLAN_ROUTE,
)

_LOGGER = logging.getLogger(__name__)

# Service schema
PLAN_ROUTE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ORIGIN): cv.string,
        vol.Required(ATTR_DESTINATION): cv.string,
        vol.Optional(ATTR_PROFILE, default=DEFAULT_PROFILE): vol.In(PROFILES),
        vol.Optional(ATTR_PREFERENCE, default=DEFAULT_PREFERENCE): vol.In(
            PREFERENCES
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenRouteService from a config entry."""

    # Create API client
    api = OpenRouteServiceAPI(hass, entry.data[CONF_API_KEY])

    # Store API client
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
    }

    # Register services (only once for all entries)
    if not hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE):
        async def handle_plan_route(call: ServiceCall) -> dict[str, Any] | None:
            """Handle plan_route service call."""
            origin_address = call.data[ATTR_ORIGIN]
            destination_address = call.data[ATTR_DESTINATION]
            profile = call.data[ATTR_PROFILE]
            preference = call.data[ATTR_PREFERENCE]

            # Get the first available API client (any entry)
            entry_data = next(iter(hass.data[DOMAIN].values()))
            api_client: OpenRouteServiceAPI = entry_data["api"]

            try:
                # Step 1: Geocode origin
                _LOGGER.debug("Geocoding origin: %s", origin_address)
                origin_coords = await api_client.geocode_address(origin_address)

                # Step 2: Geocode destination
                _LOGGER.debug("Geocoding destination: %s", destination_address)
                dest_coords = await api_client.geocode_address(destination_address)

                # Step 3: Get directions
                _LOGGER.debug(
                    "Calculating route from %s to %s (profile: %s, preference: %s)",
                    origin_coords,
                    dest_coords,
                    profile,
                    preference,
                )
                route = await api_client.get_directions(
                    origin_coords, dest_coords, profile, preference
                )

                # Return response data if requested
                if call.return_response:
                    return {
                        "origin": {
                            "address": origin_address,
                            "coordinates": origin_coords,
                        },
                        "destination": {
                            "address": destination_address,
                            "coordinates": dest_coords,
                        },
                        "distance": route["summary"]["distance"],
                        "duration": route["summary"]["duration"],
                        "geometry": route.get("geometry"),
                        "segments": route.get("segments", []),
                        "profile": profile,
                        "preference": preference,
                    }

                return None

            except ValueError as err:
                raise HomeAssistantError(f"Geocoding failed: {err}") from err
            except CannotConnect as err:
                raise HomeAssistantError(f"API error: {err}") from err
            except Exception as err:
                _LOGGER.exception("Unexpected error in plan_route")
                raise HomeAssistantError(f"Unexpected error: {err}") from err

        hass.services.async_register(
            DOMAIN,
            SERVICE_PLAN_ROUTE,
            handle_plan_route,
            schema=PLAN_ROUTE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Remove entry data
    hass.data[DOMAIN].pop(entry.entry_id)

    # Unregister services only if this is the last entry
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_PLAN_ROUTE)

    return True
```

**Reasoning**:
- Service registered once but shared across multiple config entries
- Uses first available API client from any entry for service calls
- Comprehensive error handling with helpful messages
- Returns structured response data for automation use
- Service unregistered only when last entry is removed

---

**File**: `custom_components/openrouteservice/services.yaml`
**Changes**: Service documentation

```yaml
plan_route:
  name: Plan route
  description: Plan a route between two addresses using OpenRouteService. Automatically geocodes addresses and returns route information.
  fields:
    origin:
      name: Origin
      description: Starting address (will be automatically geocoded).
      required: true
      example: "123 Main St, Berlin, Germany"
      selector:
        text:
    destination:
      name: Destination
      description: Destination address (will be automatically geocoded).
      required: true
      example: "Alexanderplatz, Berlin, Germany"
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
  response:
    optional: true
    description: Route information including distance, duration, and geometry
```

**Reasoning**:
- Clear documentation for UI and YAML configuration
- Examples help users understand expected input format
- Response section documents optional return data

---

### Success Criteria

#### Automated Verification:
- [ ] Integration files pass Home Assistant validation: `hass --script check_config`
- [x] No Python syntax errors: `python3 -m py_compile custom_components/openrouteservice/*.py`
- [x] Manifest validates: Check `custom_components/openrouteservice/manifest.json` structure
- [x] Translations validate: Check `custom_components/openrouteservice/translations/en.json` structure

#### Manual Verification:
- [ ] Integration appears in Home Assistant UI: Settings → Integrations → Add Integration → Search "OpenRouteService"
- [ ] Config flow accepts valid API key and creates entry
- [ ] Config flow rejects invalid API key with "Invalid API key" error
- [ ] Config flow shows "Cannot connect" error when API is unreachable
- [ ] Config flow prevents duplicate entries with same API key
- [ ] Service `openrouteservice.plan_route` appears in Developer Tools → Services
- [ ] Service call with addresses returns route data:
  ```yaml
  service: openrouteservice.plan_route
  data:
    origin: "Berlin Hauptbahnhof"
    destination: "Alexanderplatz, Berlin"
    profile: "driving-car"
  response_variable: route
  ```
- [ ] Response includes: `distance`, `duration`, `geometry`, `segments`
- [ ] Service handles invalid addresses gracefully with error message
- [ ] Service respects `profile` parameter (test with "foot-walking")
- [ ] Service respects `preference` parameter (test with "shortest")
- [ ] Automation using `response_variable` can access route data
- [ ] Integration unloads cleanly when removed from UI
- [ ] Service disappears after last entry is removed

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to Phase 2 (caching, options flow).

---

## Testing Strategy

### Manual Testing Steps:

1. **Installation Test**:
   - Copy `custom_components/openrouteservice/` to Home Assistant config directory
   - Restart Home Assistant
   - Check logs for any errors during startup

2. **Config Flow Test**:
   - Navigate to Settings → Integrations → Add Integration
   - Search for "OpenRouteService"
   - Enter a valid API key → Should succeed
   - Try adding same API key again → Should abort with "already configured"
   - Try invalid API key → Should show "Invalid API key" error

3. **Service Call Test** (Developer Tools → Services):
   ```yaml
   service: openrouteservice.plan_route
   data:
     origin: "Brandenburg Gate, Berlin"
     destination: "Berlin Hauptbahnhof"
     profile: "foot-walking"
     preference: "shortest"
   ```
   Expected: Returns route data in service response

4. **Automation Test**:
   ```yaml
   automation:
     - alias: "Test route planning"
       trigger:
         - platform: time
           at: "12:00:00"
       action:
         - service: openrouteservice.plan_route
           data:
             origin: "Unter den Linden 77, Berlin"
             destination: "Alexanderplatz 1, Berlin"
             profile: "driving-car"
           response_variable: my_route
         - service: persistent_notification.create
           data:
             title: "Route Info"
             message: |
               Distance: {{ my_route.distance / 1000 }} km
               Duration: {{ my_route.duration / 60 }} minutes
   ```

5. **Error Handling Test**:
   - Test with invalid address: "asdfasdfasdf123notreal"
   - Test with unreachable coordinates
   - Test with API key that has no quota

6. **Cleanup Test**:
   - Remove integration from UI
   - Verify service no longer appears in Developer Tools
   - Verify no errors in logs during unload

---

## Performance Considerations

**Geocoding Latency**:
- Each service call makes 2 geocoding requests + 1 routing request
- Total expected latency: 1-3 seconds per service call
- Consider timeout of 30 seconds (defined in `const.py:API_TIMEOUT`)

**Rate Limiting**:
- OpenRouteService free tier has daily request limits
- Library has built-in retry logic for HTTP 429 (rate limit)
- Service calls will automatically retry with exponential backoff

**Concurrent Requests**:
- Executor pattern allows non-blocking concurrent requests
- Multiple automations can call service simultaneously

---

## Migration Notes

N/A - This is initial implementation with no prior version.

---

## References

- Research document: `thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md`
- OpenRouteService API docs: https://openrouteservice.org/dev/#/api-docs
- Home Assistant config flow docs: https://developers.home-assistant.io/docs/config_entries_index
- Home Assistant service docs: https://developers.home-assistant.io/docs/dev_101_services

---

## Next Steps (Phase 2 - Out of Scope)

After Phase 1 is complete and manually verified:
- [ ] Add options flow for cache duration configuration
- [ ] Implement route caching with configurable TTL
- [ ] Add `clear_cache` service
- [ ] Add unit tests for all components
- [ ] Create comprehensive README with usage examples
- [ ] Set up GitHub repository with HACS validation
- [ ] Register in home-assistant/brands for UI assets
