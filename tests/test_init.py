"""Tests for the OpenRouteService integration setup."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.openrouteservice import async_setup_entry, async_unload_entry
from custom_components.openrouteservice.const import DOMAIN, SERVICE_PLAN_ROUTE


async def test_setup_entry(hass: HomeAssistant, mock_ors_client):
    """Test setting up a config entry."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key"},
        source="user",
        entry_id="test_entry_id",
    )

    assert await async_setup_entry(hass, entry)

    # Verify data is stored
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]
    assert "api" in hass.data[DOMAIN][entry.entry_id]

    # Verify service is registered
    assert hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE)


async def test_setup_entry_only_registers_service_once(hass: HomeAssistant, mock_ors_client):
    """Test that service is only registered once even with multiple entries."""
    entry1 = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key_1"},
        source="user",
        entry_id="test_entry_id_1",
    )

    entry2 = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key_2"},
        source="user",
        entry_id="test_entry_id_2",
    )

    assert await async_setup_entry(hass, entry1)
    assert hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE)

    # Setup second entry
    assert await async_setup_entry(hass, entry2)

    # Service should still exist (not registered twice)
    assert hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE)

    # Both entries should have their own API clients
    assert entry1.entry_id in hass.data[DOMAIN]
    assert entry2.entry_id in hass.data[DOMAIN]


async def test_unload_entry(hass: HomeAssistant, mock_ors_client):
    """Test unloading a config entry."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key"},
        source="user",
        entry_id="test_entry_id",
    )

    await async_setup_entry(hass, entry)
    assert await async_unload_entry(hass, entry)

    # Verify data is removed
    assert entry.entry_id not in hass.data[DOMAIN]

    # Service should be removed when last entry is removed
    assert not hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE)


async def test_unload_entry_keeps_service_with_other_entries(hass: HomeAssistant, mock_ors_client):
    """Test that service persists when other entries exist."""
    entry1 = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key_1"},
        source="user",
        entry_id="test_entry_id_1",
    )

    entry2 = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key_2"},
        source="user",
        entry_id="test_entry_id_2",
    )

    await async_setup_entry(hass, entry1)
    await async_setup_entry(hass, entry2)

    # Unload first entry
    assert await async_unload_entry(hass, entry1)

    # Service should still exist because entry2 is still loaded
    assert hass.services.has_service(DOMAIN, SERVICE_PLAN_ROUTE)
    assert entry2.entry_id in hass.data[DOMAIN]


async def test_service_plan_route_success(hass: HomeAssistant, mock_ors_client):
    """Test successful route planning service call."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key"},
        source="user",
        entry_id="test_entry_id",
    )

    await async_setup_entry(hass, entry)

    # Call the service
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_PLAN_ROUTE,
        {
            "origin": "Berlin, Germany",
            "destination": "Munich, Germany",
            "profile": "driving-car",
            "preference": "fastest",
        },
        blocking=True,
        return_response=True,
    )

    # Verify response
    assert response is not None
    assert "distance" in response
    assert "duration" in response
    assert "geometry" in response
    assert "segments" in response
    assert response["distance"] == 5420.5
    assert response["duration"] == 720.3


async def test_service_plan_route_with_defaults(hass: HomeAssistant, mock_ors_client):
    """Test route planning with default profile and preference."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key"},
        source="user",
        entry_id="test_entry_id",
    )

    await async_setup_entry(hass, entry)

    # Call the service without optional parameters
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_PLAN_ROUTE,
        {
            "origin": "Berlin, Germany",
            "destination": "Munich, Germany",
        },
        blocking=True,
        return_response=True,
    )

    # Verify response with defaults
    assert response is not None
    assert response["profile"] == "driving-car"
    assert response["preference"] == "fastest"


async def test_service_plan_route_geocoding_error(hass: HomeAssistant, mock_ors_client_no_features):
    """Test service call with geocoding error."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key"},
        source="user",
        entry_id="test_entry_id",
    )

    await async_setup_entry(hass, entry)

    # Call the service with address that can't be geocoded
    with pytest.raises(HomeAssistantError, match="Geocoding failed"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PLAN_ROUTE,
            {
                "origin": "invalid address",
                "destination": "Munich, Germany",
            },
            blocking=True,
            return_response=True,
        )


async def test_service_plan_route_api_error(hass: HomeAssistant):
    """Test service call with API connection error."""
    with patch("custom_components.openrouteservice.api.openrouteservice.Client") as mock_client:
        from openrouteservice import exceptions

        client_instance = MagicMock()
        mock_client.return_value = client_instance

        # First call succeeds (for setup validation)
        client_instance.pelias_search.return_value = {"features": [{"geometry": {"coordinates": [13.388860, 52.517037]}}]}

        entry = ConfigEntry(
            version=1,
            domain=DOMAIN,
            title="OpenRouteService",
            data={CONF_API_KEY: "test_api_key"},
            source="user",
            entry_id="test_entry_id",
        )

        await async_setup_entry(hass, entry)

        # Subsequent calls fail
        client_instance.pelias_search.side_effect = exceptions.ApiError("API Error")

        # Call the service
        with pytest.raises(HomeAssistantError, match="API error"):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_PLAN_ROUTE,
                {
                    "origin": "Berlin, Germany",
                    "destination": "Munich, Germany",
                },
                blocking=True,
                return_response=True,
            )


async def test_service_without_return_response(hass: HomeAssistant, mock_ors_client):
    """Test service call without requesting response."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="OpenRouteService",
        data={CONF_API_KEY: "test_api_key"},
        source="user",
        entry_id="test_entry_id",
    )

    await async_setup_entry(hass, entry)

    # Call the service without return_response
    await hass.services.async_call(
        DOMAIN,
        SERVICE_PLAN_ROUTE,
        {
            "origin": "Berlin, Germany",
            "destination": "Munich, Germany",
        },
        blocking=True,
        return_response=False,
    )

    # Should complete without error (response is None)
    # This tests that the service handles both cases correctly
