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

            _LOGGER.debug("Directions API response keys: %s", result.keys())

            if not result.get("routes"):
                # Log the full response for debugging
                _LOGGER.error("No routes in API response. Full response: %s", result)
                raise ValueError("No route found between origin and destination")

            route = result["routes"][0]
            _LOGGER.info(
                "Route calculated: %.2f km, %.2f min",
                route["summary"]["distance"] / 1000,
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
        preference: str,
    ) -> dict[str, Any]:
        """Synchronous directions helper."""
        # Convert tuples to lists for API compatibility
        coords_list = [[coord[0], coord[1]] for coord in coords]
        _LOGGER.debug(
            "Requesting directions with coords: %s, profile: %s, preference: %s",
            coords_list,
            profile,
            preference,
        )
        return self._client.directions(
            coords_list,
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
