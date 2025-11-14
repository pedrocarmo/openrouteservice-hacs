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
                try:
                    origin_coords = await api_client.geocode_address(origin_address)
                    _LOGGER.info("Origin geocoded to: %s", origin_coords)
                except ValueError as err:
                    raise HomeAssistantError(f"Failed to geocode origin '{origin_address}': {err}") from err

                # Step 2: Geocode destination
                _LOGGER.debug("Geocoding destination: %s", destination_address)
                try:
                    dest_coords = await api_client.geocode_address(destination_address)
                    _LOGGER.info("Destination geocoded to: %s", dest_coords)
                except ValueError as err:
                    raise HomeAssistantError(f"Failed to geocode destination '{destination_address}': {err}") from err

                # Step 3: Get directions
                _LOGGER.info(
                    "Calculating route from %s to %s (profile: %s, preference: %s)",
                    origin_coords,
                    dest_coords,
                    profile,
                    preference,
                )
                try:
                    route = await api_client.get_directions(
                        origin_coords, dest_coords, profile, preference
                    )
                except ValueError as err:
                    raise HomeAssistantError(f"Route calculation failed: {err}") from err

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

            except HomeAssistantError:
                # Re-raise our own errors
                raise
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
