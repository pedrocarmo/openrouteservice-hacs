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
