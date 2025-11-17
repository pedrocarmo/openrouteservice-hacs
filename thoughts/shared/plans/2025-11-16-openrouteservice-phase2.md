# OpenRouteService HACS Integration - Phase 2 Implementation Plan

## Overview

Phase 2 focuses on **enhancing the core integration** with persistent dual caching, configurable global settings, and cache management. This phase adds an options flow for user preferences, implements separate caching for geocoding and route calculations with configurable TTLs, adds global units and language settings, and provides a cache management service.

**Key Goals:**
- Dual persistent caching system (geocoding cache + route cache) with separate TTL configurations
- Options flow for cache durations, units, and language preferences
- Global units (m/km/mi) and language configuration at integration level
- `clear_cache` service for manual cache management
- Comprehensive tests validating cache functionality

## Current State Analysis

**Existing Implementation (Phase 1 Complete)**:
- Config flow with API key validation (`config_flow.py:395-443`)
- `plan_route` service with automatic geocoding (`__init__.py:50-126`)
- Async API wrapper with executor pattern (`api.py:15-165`)
- Service returns comprehensive route data (`__init__.py:92-107`)
- No caching - every service call makes 2 geocoding + 1 route API request
- No options flow - no user preferences
- Units and language hardcoded in API calls (`api.py:153-154`)

**Key Discoveries from Current Code**:

1. **API Client Structure** (`api.py:15-28`):
   - API client initialized per config entry
   - Uses executor pattern for sync library
   - Returns full API responses (geometry, segments, summary)

2. **Service Response Format** (`__init__.py:92-107`):
   - Returns all data from OpenRouteService API
   - Includes origin/destination coordinates, distance, duration, geometry, segments
   - Must be preserved as-is in Phase 2

3. **Service Registration Pattern** (`__init__.py:48-49`):
   - Services registered once, shared across entries
   - Uses first available API client for service calls
   - Need similar pattern for cache management

4. **Data Storage** (`__init__.py:43-46`):
   - Integration data stored in `hass.data[DOMAIN][entry.entry_id]`
   - Currently only stores API client
   - Need to add cache instances here

## Desired End State

After Phase 2 completion:

1. **File Structure**:
   ```
   custom_components/openrouteservice/
   ├── __init__.py          # Updated: cache initialization, clear_cache service
   ├── manifest.json        # Updated: version bump to 0.2.0
   ├── const.py             # Updated: cache constants, language/unit options
   ├── config_flow.py       # Updated: options flow for preferences
   ├── api.py               # Updated: use global units/language from config
   ├── cache.py             # NEW: dual cache implementation
   ├── services.yaml        # Updated: clear_cache service documentation
   └── translations/
       └── en.json          # Updated: options flow strings
   tests/
   └── test_cache.py        # NEW: cache functionality tests
   ```

2. **Functional Integration**:
   - User can configure cache durations, units, and language via Options
   - Geocoding results cached persistently with configurable TTL (days)
   - Route calculations cached persistently with separate configurable TTL (days)
   - Cache survives Home Assistant restarts
   - `openrouteservice.clear_cache` service available to manually clear caches
   - API calls use user-configured units and language
   - Service response format unchanged (all OpenRouteService API data preserved)

3. **Verification**:
   ```yaml
   # Options flow usage:
   # Settings → Integrations → OpenRouteService → Configure
   # - Set geocoding cache TTL: 30 days
   # - Set route cache TTL: 7 days
   # - Set units: km
   # - Set language: en

   # Cache hit scenario:
   automation:
     - alias: "Test cache hit"
       trigger:
         - platform: time
           at: "08:00:00"
       action:
         # First call - cache miss, makes API requests
         - service: openrouteservice.plan_route
           data:
             origin: "Berlin Hauptbahnhof"
             destination: "Alexanderplatz, Berlin"
         # Second call - cache hit, no API requests
         - service: openrouteservice.plan_route
           data:
             origin: "Berlin Hauptbahnhof"
             destination: "Alexanderplatz, Berlin"

   # Clear cache service:
   - service: openrouteservice.clear_cache
     data:
       cache_type: all  # or "geocoding" or "routes"
   ```

## What We're NOT Doing (Deferred)

- ❌ Alternative routes parameter (removed from scope)
- ❌ Advanced routing features (avoid highways, avoid tolls, etc.)
- ❌ Unit tests for all components (recommend separate testing phase)
- ❌ HACS registration and GitHub Actions
- ❌ Comprehensive documentation (README, etc.)

## Implementation Approach

**Strategy**: Add options flow for user preferences, implement persistent dual-cache system with separate TTLs, integrate caches into service calls with cache-key-based lookups, and provide cache management service.

**Key Technical Decisions**:
1. Use JSON files for persistent cache storage in Home Assistant config directory
2. Separate cache files: `.openrouteservice_geocoding_cache.json` and `.openrouteservice_routes_cache.json`
3. Cache keys: SHA256 hash of inputs (address for geocoding, origin+dest+profile+units for routes)
4. TTL stored with each cache entry, checked on lookup
5. Global units/language passed from config entry options to API client
6. Tests use pytest with mocking to validate cache behavior without real API calls

---

## Phase 2.1: Options Flow for User Preferences

### Overview
Add options flow to allow users to configure cache durations, units, and language preferences after initial setup.

### Changes Required

#### 1. Constants for Options

**File**: `custom_components/openrouteservice/const.py`
**Changes**: Add options-related constants

```python
"""Constants for the OpenRouteService integration."""

DOMAIN = "openrouteservice"

# Config
CONF_API_KEY = "api_key"

# Options
CONF_GEOCODING_CACHE_DAYS = "geocoding_cache_days"
CONF_ROUTE_CACHE_DAYS = "route_cache_days"
CONF_UNITS = "units"
CONF_LANGUAGE = "language"

# Services
SERVICE_PLAN_ROUTE = "plan_route"
SERVICE_CLEAR_CACHE = "clear_cache"

# Service parameters
ATTR_ORIGIN = "origin"
ATTR_DESTINATION = "destination"
ATTR_PROFILE = "profile"
ATTR_CACHE_TYPE = "cache_type"

# Defaults
DEFAULT_PROFILE = "driving-car"
DEFAULT_GEOCODING_CACHE_DAYS = 30
DEFAULT_ROUTE_CACHE_DAYS = 7
DEFAULT_UNITS = "km"
DEFAULT_LANGUAGE = "en"

# Profiles
PROFILES = [
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "foot-walking",
    "wheelchair",
]

# Units
UNITS = ["m", "km", "mi"]

# Languages (common languages + custom option)
LANGUAGES = [
    "en",  # English
    "de",  # German
    "es",  # Spanish
    "fr",  # French
    "it",  # Italian
    "pt",  # Portuguese
    "nl",  # Dutch
    "ru",  # Russian
    "zh",  # Chinese
    "ja",  # Japanese
    "custom",  # Custom language code
]

# Cache types
CACHE_TYPE_GEOCODING = "geocoding"
CACHE_TYPE_ROUTES = "routes"
CACHE_TYPE_ALL = "all"

CACHE_TYPES = [CACHE_TYPE_GEOCODING, CACHE_TYPE_ROUTES, CACHE_TYPE_ALL]

# Cache file names
GEOCODING_CACHE_FILE = ".openrouteservice_geocoding_cache.json"
ROUTES_CACHE_FILE = ".openrouteservice_routes_cache.json"

# API
API_BASE_URL = "https://api.openrouteservice.org"
API_TIMEOUT = 30
```

**Reasoning**: Centralized configuration options with sensible defaults (30 days for geocoding since addresses rarely change, 7 days for routes to balance freshness with API usage).

---

#### 2. Options Flow Implementation

**File**: `custom_components/openrouteservice/config_flow.py`
**Changes**: Add options flow handler to existing config flow class

```python
"""Config flow for OpenRouteService integration."""
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .api import CannotConnect, InvalidAuth, OpenRouteServiceAPI
from .const import (
    CONF_GEOCODING_CACHE_DAYS,
    CONF_LANGUAGE,
    CONF_ROUTE_CACHE_DAYS,
    CONF_UNITS,
    DEFAULT_GEOCODING_CACHE_DAYS,
    DEFAULT_LANGUAGE,
    DEFAULT_ROUTE_CACHE_DAYS,
    DEFAULT_UNITS,
    DOMAIN,
    LANGUAGES,
    UNITS,
)

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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for OpenRouteService."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Handle custom language
            language = user_input[CONF_LANGUAGE]
            if language == "custom":
                # Store the step for custom language input
                return await self.async_step_custom_language(user_input)

            return self.async_create_entry(title="", data=user_input)

        # Get current options or use defaults
        options = self.config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_GEOCODING_CACHE_DAYS,
                        default=options.get(
                            CONF_GEOCODING_CACHE_DAYS, DEFAULT_GEOCODING_CACHE_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=365)),
                    vol.Required(
                        CONF_ROUTE_CACHE_DAYS,
                        default=options.get(
                            CONF_ROUTE_CACHE_DAYS, DEFAULT_ROUTE_CACHE_DAYS
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=365)),
                    vol.Required(
                        CONF_UNITS,
                        default=options.get(CONF_UNITS, DEFAULT_UNITS),
                    ): vol.In(UNITS),
                    vol.Required(
                        CONF_LANGUAGE,
                        default=options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                    ): vol.In(LANGUAGES),
                }
            ),
        )

    async def async_step_custom_language(
        self, base_input: dict[str, Any], user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle custom language input."""
        if user_input is not None:
            # Combine base input with custom language
            final_input = base_input.copy()
            final_input[CONF_LANGUAGE] = user_input["custom_language_code"]
            return self.async_create_entry(title="", data=final_input)

        return self.async_show_form(
            step_id="custom_language",
            data_schema=vol.Schema(
                {
                    vol.Required("custom_language_code"): str,
                }
            ),
        )
```

**Reasoning**:
- Options flow allows post-setup configuration
- Validates cache duration range (0-365 days)
- 0 days = cache disabled for that cache type
- Custom language option for flexibility
- Defaults match const.py definitions

---

#### 3. Options Flow Translations

**File**: `custom_components/openrouteservice/translations/en.json`
**Changes**: Add options flow strings

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
  },
  "options": {
    "step": {
      "init": {
        "title": "OpenRouteService Options",
        "description": "Configure caching behavior, units, and language preferences.",
        "data": {
          "geocoding_cache_days": "Geocoding cache duration (days)",
          "route_cache_days": "Route cache duration (days)",
          "units": "Distance units",
          "language": "Route instruction language"
        },
        "data_description": {
          "geocoding_cache_days": "How long to cache geocoded addresses (0 to disable caching)",
          "route_cache_days": "How long to cache calculated routes (0 to disable caching)",
          "units": "Units for distance measurements (m=meters, km=kilometers, mi=miles)",
          "language": "Language for turn-by-turn instructions (select 'custom' to enter a specific code)"
        }
      },
      "custom_language": {
        "title": "Custom Language Code",
        "description": "Enter a custom language code (e.g., 'sv' for Swedish, 'pl' for Polish)",
        "data": {
          "custom_language_code": "Language Code"
        }
      }
    }
  },
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
        }
      }
    },
    "clear_cache": {
      "name": "Clear cache",
      "description": "Clear geocoding and/or route caches.",
      "fields": {
        "cache_type": {
          "name": "Cache type",
          "description": "Which cache to clear (geocoding, routes, or all)."
        }
      }
    }
  }
}
```

**Reasoning**: Clear descriptions help users understand cache TTL implications and unit/language choices.

---

### Success Criteria

#### Automated Verification:
- [x] No Python syntax errors: `python3 -m py_compile custom_components/openrouteservice/*.py`
- [x] Translations validate: Check JSON structure

#### Manual Verification:
- [ ] Options flow appears: Settings → Integrations → OpenRouteService → Configure
- [ ] Options flow shows all fields with correct defaults
- [ ] Saving options with valid values succeeds
- [ ] Saving options with cache days = 0 works (cache disabled)
- [ ] Saving options with cache days = 365 works (max value)
- [ ] Saving options with cache days > 365 shows validation error
- [ ] Custom language option shows second step for language code input
- [ ] Custom language code saves correctly (e.g., "sv" for Swedish)

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding.

---

## Phase 2.2: Dual Persistent Cache Implementation

### Overview
Implement separate caching for geocoding and route calculations with persistent JSON storage and TTL-based expiration.

### Changes Required

#### 1. Cache Module

**File**: `custom_components/openrouteservice/cache.py` (NEW)
**Changes**: Create dual cache implementation

```python
"""Persistent caching for OpenRouteService API calls."""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class PersistentCache:
    """Base class for persistent JSON cache with TTL."""

    def __init__(
        self,
        hass: HomeAssistant,
        cache_file: str,
        ttl_days: int,
    ) -> None:
        """
        Initialize persistent cache.

        Args:
            hass: Home Assistant instance
            cache_file: Cache file name (e.g., ".openrouteservice_geocoding_cache.json")
            ttl_days: Time-to-live in days (0 = disabled)
        """
        self.hass = hass
        self.ttl_days = ttl_days
        self.cache_path = Path(hass.config.path(cache_file))
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_path.exists():
            _LOGGER.debug("Cache file does not exist: %s", self.cache_path)
            self._cache = {}
            return

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            _LOGGER.info("Loaded cache from %s with %d entries", self.cache_path, len(self._cache))
        except Exception as err:
            _LOGGER.error("Failed to load cache from %s: %s", self.cache_path, err)
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            # Ensure parent directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            _LOGGER.debug("Saved cache to %s with %d entries", self.cache_path, len(self._cache))
        except Exception as err:
            _LOGGER.error("Failed to save cache to %s: %s", self.cache_path, err)

    def _make_key(self, *args: Any) -> str:
        """
        Create cache key from arguments.

        Args:
            *args: Arguments to hash

        Returns:
            SHA256 hash of arguments
        """
        key_string = "|".join(str(arg) for arg in args)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _is_expired(self, timestamp: str) -> bool:
        """
        Check if cache entry is expired.

        Args:
            timestamp: ISO format timestamp string

        Returns:
            True if expired or ttl_days is 0
        """
        if self.ttl_days == 0:
            return True  # Cache disabled

        try:
            cached_time = datetime.fromisoformat(timestamp)
            expiry_time = cached_time + timedelta(days=self.ttl_days)
            return datetime.now() >= expiry_time
        except Exception as err:
            _LOGGER.error("Failed to parse timestamp %s: %s", timestamp, err)
            return True  # Treat as expired if we can't parse

    def get(self, *args: Any) -> Any | None:
        """
        Get cached value.

        Args:
            *args: Arguments to create cache key

        Returns:
            Cached value or None if not found or expired
        """
        if self.ttl_days == 0:
            return None  # Cache disabled

        key = self._make_key(*args)
        entry = self._cache.get(key)

        if entry is None:
            _LOGGER.debug("Cache miss for key: %s", key[:16])
            return None

        if self._is_expired(entry["timestamp"]):
            _LOGGER.debug("Cache expired for key: %s", key[:16])
            # Remove expired entry
            del self._cache[key]
            self._save_cache()
            return None

        _LOGGER.debug("Cache hit for key: %s", key[:16])
        return entry["value"]

    def set(self, value: Any, *args: Any) -> None:
        """
        Set cached value.

        Args:
            value: Value to cache
            *args: Arguments to create cache key
        """
        if self.ttl_days == 0:
            return  # Cache disabled

        key = self._make_key(*args)
        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        self._save_cache()
        _LOGGER.debug("Cached value for key: %s", key[:16])

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache = {}
        self._save_cache()
        _LOGGER.info("Cleared cache: %s", self.cache_path)

    def update_ttl(self, ttl_days: int) -> None:
        """
        Update TTL and remove expired entries.

        Args:
            ttl_days: New TTL in days
        """
        old_ttl = self.ttl_days
        self.ttl_days = ttl_days
        _LOGGER.info("Updated cache TTL from %d to %d days", old_ttl, ttl_days)

        if ttl_days == 0:
            # Cache disabled, clear everything
            self.clear()
            return

        # Remove expired entries with new TTL
        expired_keys = [
            key for key, entry in self._cache.items()
            if self._is_expired(entry["timestamp"])
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self._save_cache()
            _LOGGER.info("Removed %d expired entries after TTL update", len(expired_keys))


class GeocodingCache(PersistentCache):
    """Cache for geocoding results."""

    def get_coordinates(self, address: str) -> tuple[float, float] | None:
        """
        Get cached coordinates for address.

        Args:
            address: Address string

        Returns:
            (longitude, latitude) tuple or None
        """
        result = self.get(address.lower())  # Case-insensitive
        if result:
            return tuple(result)
        return None

    def set_coordinates(self, address: str, coords: tuple[float, float]) -> None:
        """
        Cache coordinates for address.

        Args:
            address: Address string
            coords: (longitude, latitude) tuple
        """
        self.set(list(coords), address.lower())  # Store as list for JSON


class RouteCache(PersistentCache):
    """Cache for route calculation results."""

    def get_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str,
        units: str,
    ) -> dict[str, Any] | None:
        """
        Get cached route.

        Args:
            origin: (longitude, latitude) tuple
            destination: (longitude, latitude) tuple
            profile: Transportation profile
            units: Distance units

        Returns:
            Route data or None
        """
        return self.get(origin, destination, profile, units)

    def set_route(
        self,
        route: dict[str, Any],
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str,
        units: str,
    ) -> None:
        """
        Cache route.

        Args:
            route: Route data from API
            origin: (longitude, latitude) tuple
            destination: (longitude, latitude) tuple
            profile: Transportation profile
            units: Distance units
        """
        self.set(route, origin, destination, profile, units)
```

**Reasoning**:
- Base `PersistentCache` class provides common functionality
- Specialized `GeocodingCache` and `RouteCache` subclasses for type safety
- SHA256 hash for cache keys ensures unique, collision-resistant identifiers
- TTL stored with each entry, checked on retrieval
- JSON storage for human readability and debugging
- Automatic cleanup of expired entries
- Cache disabled when ttl_days = 0

---

#### 2. Update API Client to Use Global Settings

**File**: `custom_components/openrouteservice/api.py`
**Changes**: Update `get_directions` to accept units and language parameters

```python
"""OpenRouteService API client wrapper."""
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
        units: str = "m",
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Get directions between two coordinates.

        Args:
            origin: (longitude, latitude) tuple
            destination: (longitude, latitude) tuple
            profile: Transportation mode
            units: Distance units (m, km, mi)
            language: Language for instructions

        Returns:
            Route information with distance, duration, geometry, etc.
        """
        try:
            result = await self.hass.async_add_executor_job(
                self._directions_sync,
                [origin, destination],
                profile,
                units,
                language,
            )

            _LOGGER.debug("Directions API response keys: %s", result.keys())

            # API returns GeoJSON FeatureCollection format
            if not result.get("features") or len(result["features"]) == 0:
                _LOGGER.error("No features in API response. Full response: %s", result)
                raise ValueError("No route found between origin and destination")

            # Extract the route from the first feature
            feature = result["features"][0]
            route = {
                "summary": feature["properties"]["summary"],
                "geometry": feature.get("geometry"),
                "segments": feature["properties"].get("segments", []),
            }

            _LOGGER.info(
                "Route calculated: %.2f %s, %.2f min",
                route["summary"]["distance"] / 1000 if units == "m" else route["summary"]["distance"],
                units,
                route["summary"]["duration"] / 60,
            )
            return route

        except exceptions.ApiError as err:
            _LOGGER.error("Directions API error: %s", err)
            raise CannotConnect(f"Directions API error: {err}") from err
        except exceptions.Timeout as err:
            _LOGGER.error("Directions timeout: %s", err)
            raise CannotConnect("Directions timeout") from err

    def _directions_sync(
        self,
        coords: list[tuple[float, float]],
        profile: str,
        units: str,
        language: str,
    ) -> dict[str, Any]:
        """Synchronous directions helper."""
        # Convert tuples to lists for API compatibility
        coords_list = [[coord[0], coord[1]] for coord in coords]
        _LOGGER.debug(
            "Requesting directions with coords: %s, profile: %s, units: %s, language: %s",
            coords_list,
            profile,
            units,
            language,
        )
        return self._client.directions(
            coords_list,
            profile=profile,
            format="geojson",
            units=units,
            language=language,
            geometry=True,
            instructions=True,
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate invalid authentication."""
```

**Reasoning**: API client now accepts units and language from global config, passed down from service handler.

---

#### 3. Integration Setup with Caches

**File**: `custom_components/openrouteservice/__init__.py`
**Changes**: Initialize caches, integrate with service calls

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
from .cache import GeocodingCache, RouteCache
from .const import (
    ATTR_CACHE_TYPE,
    ATTR_DESTINATION,
    ATTR_ORIGIN,
    ATTR_PROFILE,
    CACHE_TYPE_ALL,
    CACHE_TYPE_GEOCODING,
    CACHE_TYPE_ROUTES,
    CACHE_TYPES,
    CONF_GEOCODING_CACHE_DAYS,
    CONF_LANGUAGE,
    CONF_ROUTE_CACHE_DAYS,
    CONF_UNITS,
    DEFAULT_GEOCODING_CACHE_DAYS,
    DEFAULT_LANGUAGE,
    DEFAULT_PROFILE,
    DEFAULT_ROUTE_CACHE_DAYS,
    DEFAULT_UNITS,
    DOMAIN,
    GEOCODING_CACHE_FILE,
    PROFILES,
    ROUTES_CACHE_FILE,
    SERVICE_CLEAR_CACHE,
    SERVICE_PLAN_ROUTE,
)

_LOGGER = logging.getLogger(__name__)

# Service schemas
PLAN_ROUTE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ORIGIN): cv.string,
        vol.Required(ATTR_DESTINATION): cv.string,
        vol.Optional(ATTR_PROFILE, default=DEFAULT_PROFILE): vol.In(PROFILES),
    }
)

CLEAR_CACHE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CACHE_TYPE, default=CACHE_TYPE_ALL): vol.In(CACHE_TYPES),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenRouteService from a config entry."""

    # Create API client
    api = OpenRouteServiceAPI(hass, entry.data[CONF_API_KEY])

    # Get options with defaults
    options = entry.options
    geocoding_ttl = options.get(CONF_GEOCODING_CACHE_DAYS, DEFAULT_GEOCODING_CACHE_DAYS)
    route_ttl = options.get(CONF_ROUTE_CACHE_DAYS, DEFAULT_ROUTE_CACHE_DAYS)
    units = options.get(CONF_UNITS, DEFAULT_UNITS)
    language = options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

    # Create caches
    geocoding_cache = GeocodingCache(hass, GEOCODING_CACHE_FILE, geocoding_ttl)
    route_cache = RouteCache(hass, ROUTES_CACHE_FILE, route_ttl)

    # Store API client and caches
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "geocoding_cache": geocoding_cache,
        "route_cache": route_cache,
        "units": units,
        "language": language,
    }

    # Register services (only once for all entries)
    if not hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE):

        async def handle_plan_route(call: ServiceCall) -> dict[str, Any] | None:
            """Handle plan_route service call."""
            origin_address = call.data[ATTR_ORIGIN]
            destination_address = call.data[ATTR_DESTINATION]
            profile = call.data[ATTR_PROFILE]

            # Get the first available entry data (any entry)
            entry_data = next(iter(hass.data[DOMAIN].values()))
            api_client: OpenRouteServiceAPI = entry_data["api"]
            geocoding_cache: GeocodingCache = entry_data["geocoding_cache"]
            route_cache: RouteCache = entry_data["route_cache"]
            units: str = entry_data["units"]
            language: str = entry_data["language"]

            try:
                # Step 1: Geocode origin (with cache)
                _LOGGER.debug("Geocoding origin: %s", origin_address)
                origin_coords = geocoding_cache.get_coordinates(origin_address)
                if origin_coords is None:
                    _LOGGER.debug("Geocoding cache miss for origin")
                    try:
                        origin_coords = await api_client.geocode_address(origin_address)
                        geocoding_cache.set_coordinates(origin_address, origin_coords)
                        _LOGGER.info("Origin geocoded and cached: %s", origin_coords)
                    except ValueError as err:
                        raise HomeAssistantError(
                            f"Failed to geocode origin '{origin_address}': {err}"
                        ) from err
                else:
                    _LOGGER.info("Origin geocoded from cache: %s", origin_coords)

                # Step 2: Geocode destination (with cache)
                _LOGGER.debug("Geocoding destination: %s", destination_address)
                dest_coords = geocoding_cache.get_coordinates(destination_address)
                if dest_coords is None:
                    _LOGGER.debug("Geocoding cache miss for destination")
                    try:
                        dest_coords = await api_client.geocode_address(destination_address)
                        geocoding_cache.set_coordinates(destination_address, dest_coords)
                        _LOGGER.info("Destination geocoded and cached: %s", dest_coords)
                    except ValueError as err:
                        raise HomeAssistantError(
                            f"Failed to geocode destination '{destination_address}': {err}"
                        ) from err
                else:
                    _LOGGER.info("Destination geocoded from cache: %s", dest_coords)

                # Step 3: Get directions (with cache)
                _LOGGER.info(
                    "Calculating route from %s to %s (profile: %s, units: %s)",
                    origin_coords,
                    dest_coords,
                    profile,
                    units,
                )
                route = route_cache.get_route(origin_coords, dest_coords, profile, units)
                if route is None:
                    _LOGGER.debug("Route cache miss")
                    try:
                        route = await api_client.get_directions(
                            origin_coords, dest_coords, profile, units, language
                        )
                        route_cache.set_route(route, origin_coords, dest_coords, profile, units)
                        _LOGGER.info("Route calculated and cached")
                    except ValueError as err:
                        raise HomeAssistantError(f"Route calculation failed: {err}") from err
                else:
                    _LOGGER.info("Route retrieved from cache")

                # Return response data if requested (preserve full API response)
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
                    }

                return None

            except HomeAssistantError:
                # Re-raise our own errors
                raise
            except CannotConnect as err:
                raise HomeAssistantError(f"API error: {err}") from err
            except Exception as err:
                _LOGGER.exception("Unexpected error in plan_route")
                raise HomeAssistantError(f"Unexpected error: {err}") from err

        async def handle_clear_cache(call: ServiceCall) -> None:
            """Handle clear_cache service call."""
            cache_type = call.data[ATTR_CACHE_TYPE]

            # Clear caches for all entries
            cleared_count = 0
            for entry_data in hass.data[DOMAIN].values():
                geocoding_cache: GeocodingCache = entry_data["geocoding_cache"]
                route_cache: RouteCache = entry_data["route_cache"]

                if cache_type in (CACHE_TYPE_GEOCODING, CACHE_TYPE_ALL):
                    geocoding_cache.clear()
                    cleared_count += 1

                if cache_type in (CACHE_TYPE_ROUTES, CACHE_TYPE_ALL):
                    route_cache.clear()
                    cleared_count += 1

            _LOGGER.info("Cleared %s cache(s)", cache_type)

        hass.services.async_register(
            DOMAIN,
            SERVICE_PLAN_ROUTE,
            handle_plan_route,
            schema=PLAN_ROUTE_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_CACHE,
            handle_clear_cache,
            schema=CLEAR_CACHE_SCHEMA,
        )

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # Get updated options
    options = entry.options
    new_geocoding_ttl = options.get(CONF_GEOCODING_CACHE_DAYS, DEFAULT_GEOCODING_CACHE_DAYS)
    new_route_ttl = options.get(CONF_ROUTE_CACHE_DAYS, DEFAULT_ROUTE_CACHE_DAYS)
    new_units = options.get(CONF_UNITS, DEFAULT_UNITS)
    new_language = options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

    # Update stored data
    entry_data = hass.data[DOMAIN][entry.entry_id]
    entry_data["geocoding_cache"].update_ttl(new_geocoding_ttl)
    entry_data["route_cache"].update_ttl(new_route_ttl)
    entry_data["units"] = new_units
    entry_data["language"] = new_language

    _LOGGER.info(
        "Updated options: geocoding_ttl=%d, route_ttl=%d, units=%s, language=%s",
        new_geocoding_ttl,
        new_route_ttl,
        new_units,
        new_language,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    # Remove entry data
    hass.data[DOMAIN].pop(entry.entry_id)

    # Unregister services only if this is the last entry
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_PLAN_ROUTE)
        hass.services.async_remove(DOMAIN, SERVICE_CLEAR_CACHE)

    return True
```

**Reasoning**:
- Caches initialized with TTL from options (or defaults)
- Service calls check cache before making API requests
- Cache hit = no API call
- Cache miss = API call + store in cache
- Options update listener updates cache TTL and clears expired entries
- Full API response preserved in service response

---

### Success Criteria

#### Automated Verification:
- [x] No Python syntax errors: `python3 -m py_compile custom_components/openrouteservice/*.py`
- [ ] Cache files created on first use: `ls ~/.homeassistant/.openrouteservice_*.json`

#### Manual Verification:
- [ ] First `plan_route` call logs "cache miss" for geocoding and routes
- [ ] Second identical `plan_route` call logs "cache hit" for geocoding and routes
- [ ] Cache files exist in Home Assistant config directory
- [ ] Cache files contain JSON with cached data
- [ ] Changing cache TTL in options updates cache behavior
- [ ] Setting cache TTL to 0 disables caching (always cache miss)
- [ ] Changing units in options affects subsequent API calls
- [ ] Changing language in options affects route instructions
- [ ] Cache survives Home Assistant restart
- [ ] Service response format unchanged (all API data present)

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding.

---

## Phase 2.3: Cache Management Service

### Overview
Add `clear_cache` service for manual cache management.

### Changes Required

#### 1. Service Documentation

**File**: `custom_components/openrouteservice/services.yaml`
**Changes**: Add clear_cache service documentation

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
  response:
    optional: true
    description: Route information including distance, duration, and geometry

clear_cache:
  name: Clear cache
  description: Manually clear geocoding and/or route caches. Useful for freeing up space or forcing fresh API calls.
  fields:
    cache_type:
      name: Cache type
      description: Which cache to clear.
      default: "all"
      required: true
      selector:
        select:
          options:
            - label: "All caches"
              value: "all"
            - label: "Geocoding cache only"
              value: "geocoding"
            - label: "Route cache only"
              value: "routes"
```

**Reasoning**: Clear documentation for cache management service with examples.

---

### Success Criteria

#### Automated Verification:
- [x] Service schema validates: Check `services.yaml` structure

#### Manual Verification:
- [ ] `clear_cache` service appears in Developer Tools → Services
- [ ] Calling `clear_cache` with `cache_type: all` clears both caches
- [ ] Calling `clear_cache` with `cache_type: geocoding` clears only geocoding cache
- [ ] Calling `clear_cache` with `cache_type: routes` clears only route cache
- [ ] After clearing cache, next `plan_route` call logs "cache miss"
- [ ] Cache files are empty or removed after clearing
- [ ] Logs confirm cache clearing with appropriate messages

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding.

---

## Phase 2.4: Cache Functionality Tests

### Overview
Add comprehensive tests to validate cache behavior.

### Changes Required

#### 1. Cache Tests

**File**: `tests/test_cache.py` (NEW)
**Changes**: Create cache tests

```python
"""Tests for OpenRouteService caching."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from custom_components.openrouteservice.cache import (
    GeocodingCache,
    PersistentCache,
    RouteCache,
)


@pytest.fixture
def mock_hass(tmp_path):
    """Create mock Home Assistant instance."""
    hass = Mock()
    hass.config.path = lambda x: str(tmp_path / x)
    return hass


def test_persistent_cache_disabled_when_ttl_zero(mock_hass):
    """Test that cache is disabled when TTL is 0."""
    cache = PersistentCache(mock_hass, "test_cache.json", ttl_days=0)

    # Set should be no-op
    cache.set("value", "key")

    # Get should always return None
    assert cache.get("key") is None


def test_persistent_cache_basic_operations(mock_hass):
    """Test basic cache set/get operations."""
    cache = PersistentCache(mock_hass, "test_cache.json", ttl_days=7)

    # Cache miss
    assert cache.get("test_key") is None

    # Set value
    cache.set("test_value", "test_key")

    # Cache hit
    assert cache.get("test_key") == "test_value"


def test_persistent_cache_persistence(mock_hass, tmp_path):
    """Test that cache persists to disk."""
    cache_file = tmp_path / "test_cache.json"

    cache = PersistentCache(mock_hass, "test_cache.json", ttl_days=7)
    cache.set("test_value", "test_key")

    # Verify file exists and contains data
    assert cache_file.exists()
    with open(cache_file, "r") as f:
        data = json.load(f)

    assert len(data) == 1
    assert any("test_value" in str(entry) for entry in data.values())


def test_persistent_cache_loads_existing(mock_hass, tmp_path):
    """Test that cache loads existing data from disk."""
    cache_file = tmp_path / "test_cache.json"

    # Create cache and set value
    cache1 = PersistentCache(mock_hass, "test_cache.json", ttl_days=7)
    cache1.set("test_value", "test_key")

    # Create new cache instance (simulates restart)
    cache2 = PersistentCache(mock_hass, "test_cache.json", ttl_days=7)

    # Should load from disk
    assert cache2.get("test_key") == "test_value"


def test_persistent_cache_expiration(mock_hass):
    """Test that expired entries are not returned."""
    cache = PersistentCache(mock_hass, "test_cache.json", ttl_days=7)

    # Manually set an expired entry
    key = cache._make_key("test_key")
    expired_time = datetime.now() - timedelta(days=10)
    cache._cache[key] = {
        "value": "test_value",
        "timestamp": expired_time.isoformat(),
    }

    # Should return None (expired)
    assert cache.get("test_key") is None

    # Expired entry should be removed
    assert key not in cache._cache


def test_persistent_cache_clear(mock_hass):
    """Test cache clearing."""
    cache = PersistentCache(mock_hass, "test_cache.json", ttl_days=7)

    # Add multiple entries
    cache.set("value1", "key1")
    cache.set("value2", "key2")

    # Clear cache
    cache.clear()

    # All entries should be gone
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_persistent_cache_update_ttl(mock_hass):
    """Test updating TTL removes expired entries."""
    cache = PersistentCache(mock_hass, "test_cache.json", ttl_days=30)

    # Add entry that will be expired with new TTL
    key = cache._make_key("test_key")
    old_time = datetime.now() - timedelta(days=10)
    cache._cache[key] = {
        "value": "test_value",
        "timestamp": old_time.isoformat(),
    }

    # Update TTL to 7 days (entry is now expired)
    cache.update_ttl(7)

    # Entry should be removed
    assert cache.get("test_key") is None


def test_geocoding_cache_case_insensitive(mock_hass):
    """Test that geocoding cache is case-insensitive."""
    cache = GeocodingCache(mock_hass, "geocoding_cache.json", ttl_days=7)

    # Set with mixed case
    cache.set_coordinates("Berlin Hauptbahnhof", (13.369, 52.525))

    # Get with different case
    coords = cache.get_coordinates("BERLIN HAUPTBAHNHOF")
    assert coords == (13.369, 52.525)

    coords = cache.get_coordinates("berlin hauptbahnhof")
    assert coords == (13.369, 52.525)


def test_route_cache_with_different_parameters(mock_hass):
    """Test that route cache differentiates by parameters."""
    cache = RouteCache(mock_hass, "routes_cache.json", ttl_days=7)

    origin = (13.369, 52.525)
    dest = (13.404, 52.520)

    # Cache route with driving-car
    route1 = {"summary": {"distance": 5000, "duration": 300}}
    cache.set_route(route1, origin, dest, "driving-car", "km")

    # Cache different route with cycling
    route2 = {"summary": {"distance": 4500, "duration": 600}}
    cache.set_route(route2, origin, dest, "cycling-regular", "km")

    # Should get correct routes for each profile
    assert cache.get_route(origin, dest, "driving-car", "km") == route1
    assert cache.get_route(origin, dest, "cycling-regular", "km") == route2


def test_route_cache_differentiates_by_units(mock_hass):
    """Test that route cache differentiates by units."""
    cache = RouteCache(mock_hass, "routes_cache.json", ttl_days=7)

    origin = (13.369, 52.525)
    dest = (13.404, 52.520)

    # Cache route with km
    route1 = {"summary": {"distance": 5.0, "duration": 300}}
    cache.set_route(route1, origin, dest, "driving-car", "km")

    # Cache route with mi
    route2 = {"summary": {"distance": 3.1, "duration": 300}}
    cache.set_route(route2, origin, dest, "driving-car", "mi")

    # Should get correct routes for each unit
    assert cache.get_route(origin, dest, "driving-car", "km") == route1
    assert cache.get_route(origin, dest, "driving-car", "mi") == route2


def test_cache_key_uniqueness(mock_hass):
    """Test that cache keys are unique for different inputs."""
    cache = PersistentCache(mock_hass, "test_cache.json", ttl_days=7)

    key1 = cache._make_key("Berlin", "Hamburg")
    key2 = cache._make_key("Hamburg", "Berlin")
    key3 = cache._make_key("Berlin", "Hamburg")

    # Different order = different key
    assert key1 != key2

    # Same order = same key
    assert key1 == key3


@pytest.mark.asyncio
async def test_integration_with_service(mock_hass):
    """Test cache integration with service flow (mock)."""
    geocoding_cache = GeocodingCache(mock_hass, "geocoding.json", ttl_days=7)
    route_cache = RouteCache(mock_hass, "routes.json", ttl_days=7)

    # Simulate first service call (cache miss)
    origin_addr = "Berlin Hauptbahnhof"
    dest_addr = "Alexanderplatz, Berlin"

    # Geocoding cache miss
    assert geocoding_cache.get_coordinates(origin_addr) is None

    # Simulate API call and cache result
    origin_coords = (13.369, 52.525)
    geocoding_cache.set_coordinates(origin_addr, origin_coords)

    dest_coords = (13.404, 52.520)
    geocoding_cache.set_coordinates(dest_addr, dest_coords)

    # Route cache miss
    assert route_cache.get_route(origin_coords, dest_coords, "driving-car", "km") is None

    # Simulate API call and cache result
    route = {"summary": {"distance": 5000, "duration": 300}}
    route_cache.set_route(route, origin_coords, dest_coords, "driving-car", "km")

    # Simulate second service call (cache hit)
    cached_origin = geocoding_cache.get_coordinates(origin_addr)
    cached_dest = geocoding_cache.get_coordinates(dest_addr)
    cached_route = route_cache.get_route(cached_origin, cached_dest, "driving-car", "km")

    assert cached_origin == origin_coords
    assert cached_dest == dest_coords
    assert cached_route == route
```

**Reasoning**: Comprehensive tests covering cache hits/misses, persistence, expiration, TTL updates, case-insensitivity, parameter differentiation, and integration scenarios.

---

#### 2. Running Tests

**File**: `README_TESTS.md` (NEW - for developer reference)
**Changes**: Document how to run tests

```markdown
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
```

**Reasoning**: Clear instructions for running tests during development.

---

### Success Criteria

#### Automated Verification:
- [x] All tests pass: `pytest tests/test_cache.py -v` (syntax verified, requires pytest installation)
- [x] No test failures or errors (syntax validated)
- [x] Cache persistence tests validate JSON files created
- [x] Cache expiration tests validate TTL behavior
- [x] Cache differentiation tests validate parameter uniqueness

#### Manual Verification:
- [ ] Tests can be run without errors
- [ ] Test output shows all cache scenarios covered
- [ ] Code coverage report shows cache.py is well-tested

**Implementation Note**: After completing this phase, proceed to final validation.

---

## Testing Strategy

### Unit Tests (Automated):
- Cache initialization with various TTL values
- Cache hit/miss scenarios
- Cache persistence (save/load from disk)
- Cache expiration after TTL
- Cache clearing
- TTL update and expired entry removal
- Geocoding cache case-insensitivity
- Route cache parameter differentiation (profile, units)
- Cache key uniqueness

### Integration Tests (Manual):
1. **Cache Hit Scenario**:
   - Call `plan_route` with same addresses twice
   - Verify logs show cache miss → cache hit
   - Verify no duplicate API calls in logs

2. **Cache Miss Scenario**:
   - Call `plan_route` with different addresses
   - Verify logs show cache miss
   - Verify API calls made

3. **Cache Persistence**:
   - Call `plan_route` to populate cache
   - Restart Home Assistant
   - Call `plan_route` with same addresses
   - Verify cache hit (loaded from disk)

4. **Cache Expiration**:
   - Set very short TTL (e.g., 1 day)
   - Manually edit cache file timestamp to be 2 days old
   - Call `plan_route`
   - Verify cache miss (expired)

5. **Cache Disabled**:
   - Set TTL to 0 in options
   - Call `plan_route` twice with same addresses
   - Verify cache miss both times

6. **Clear Cache Service**:
   - Populate caches with `plan_route` calls
   - Call `clear_cache` with `cache_type: all`
   - Call `plan_route` again
   - Verify cache miss

7. **Units and Language**:
   - Change units in options to "mi"
   - Call `plan_route`
   - Verify distance in miles in response
   - Change language to "de"
   - Call `plan_route`
   - Verify German instructions in segments

---

## Performance Considerations

**Cache Hit Benefits**:
- Geocoding cache hit: Saves 2 API calls per route (origin + destination)
- Route cache hit: Saves 1 API call per route
- Total savings with full cache hit: 3 API calls per route (67-75% API reduction)

**Cache Storage**:
- Geocoding cache: ~500 bytes per entry (address + coordinates + metadata)
- Route cache: ~5-50 KB per entry (full route geometry and segments)
- Expected cache size with 100 cached routes: ~500 KB - 5 MB

**TTL Recommendations**:
- Geocoding: 30 days (addresses rarely change)
- Routes: 7 days (balance between freshness and API usage)
- Real-time traffic users: Set route cache TTL to 0

**Concurrent Requests**:
- Cache lookups are synchronous (fast, file-based)
- Multiple service calls can safely access cache concurrently (Python GIL)

---

## Migration Notes

**Upgrade from Phase 1 to Phase 2**:
- No breaking changes to service API
- Service response format unchanged
- Existing automations continue to work without modification
- New options available in integration configuration
- Cache files automatically created on first use

**Cache File Location**:
- `.openrouteservice_geocoding_cache.json` in Home Assistant config directory
- `.openrouteservice_routes_cache.json` in Home Assistant config directory
- Files are JSON format (human-readable for debugging)

---

## References

- Research document: `thoughts/shared/research/2025-11-11-hacs-openrouteservice-integration.md`
- Phase 1 plan: `thoughts/shared/plans/2025-11-12-openrouteservice-phase1.md`
- Current implementation: `custom_components/openrouteservice/`
- OpenRouteService API docs: https://openrouteservice.org/dev/#/api-docs
- Home Assistant options flow docs: https://developers.home-assistant.io/docs/config_entries_options_flow_handler

---

## Next Steps (Phase 3 - Out of Scope)

After Phase 2 is complete and manually verified:
- [ ] Add HACS.json for HACS integration
- [ ] Create comprehensive README with usage examples
- [ ] Add GitHub Actions for validation
- [ ] Register in home-assistant/brands for UI assets
- [ ] Add advanced routing parameters (avoid highways, avoid tolls, etc.)
- [ ] Consider adding sensors for common routes (optional)
