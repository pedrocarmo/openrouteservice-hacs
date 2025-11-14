"""Tests for the OpenRouteService API client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.openrouteservice.api import (
    OpenRouteServiceAPI,
    CannotConnect,
    InvalidAuth,
)


async def test_validate_api_key_success(hass: HomeAssistant, mock_ors_client):
    """Test successful API key validation."""
    api = OpenRouteServiceAPI(hass, "test_api_key")
    result = await api.validate_api_key()

    assert result["valid"] is True
    assert "features_count" in result
    mock_ors_client.pelias_search.assert_called_once()


async def test_validate_api_key_invalid_auth(hass: HomeAssistant, mock_ors_client_auth_error):
    """Test API key validation with invalid auth."""
    api = OpenRouteServiceAPI(hass, "invalid_key")

    with pytest.raises(InvalidAuth):
        await api.validate_api_key()


async def test_validate_api_key_timeout(hass: HomeAssistant, mock_ors_client_timeout):
    """Test API key validation with timeout."""
    api = OpenRouteServiceAPI(hass, "test_api_key")

    with pytest.raises(CannotConnect):
        await api.validate_api_key()


async def test_geocode_address_success(hass: HomeAssistant, mock_ors_client):
    """Test successful address geocoding."""
    api = OpenRouteServiceAPI(hass, "test_api_key")
    coords = await api.geocode_address("Berlin, Germany")

    assert isinstance(coords, tuple)
    assert len(coords) == 2
    assert coords[0] == 13.388860  # longitude
    assert coords[1] == 52.517037  # latitude
    mock_ors_client.pelias_search.assert_called_once()


async def test_geocode_address_no_results(hass: HomeAssistant, mock_ors_client_no_features):
    """Test geocoding with no results."""
    api = OpenRouteServiceAPI(hass, "test_api_key")

    with pytest.raises(ValueError, match="Could not geocode address"):
        await api.geocode_address("nonexistent address 12345")


async def test_geocode_address_api_error(hass: HomeAssistant, mock_ors_client_auth_error):
    """Test geocoding with API error."""
    api = OpenRouteServiceAPI(hass, "test_api_key")

    with pytest.raises(CannotConnect):
        await api.geocode_address("Berlin, Germany")


async def test_get_directions_success(hass: HomeAssistant, mock_ors_client):
    """Test successful directions request."""
    api = OpenRouteServiceAPI(hass, "test_api_key")

    origin = (13.388860, 52.517037)
    destination = (13.397634, 52.529407)

    route = await api.get_directions(origin, destination, "driving-car", "fastest")

    assert "summary" in route
    assert route["summary"]["distance"] == 5420.5
    assert route["summary"]["duration"] == 720.3
    assert "geometry" in route
    assert "segments" in route
    mock_ors_client.directions.assert_called_once()


async def test_get_directions_with_different_profile(hass: HomeAssistant, mock_ors_client):
    """Test directions with different travel profile."""
    api = OpenRouteServiceAPI(hass, "test_api_key")

    origin = (13.388860, 52.517037)
    destination = (13.397634, 52.529407)

    route = await api.get_directions(origin, destination, "foot-walking", "shortest")

    assert "summary" in route
    # Verify the profile was passed correctly
    call_args = mock_ors_client.directions.call_args
    assert call_args[1]["profile"] == "foot-walking"
    assert call_args[1]["preference"] == "shortest"


async def test_get_directions_no_route_found(hass: HomeAssistant):
    """Test directions when no route is found."""
    with patch("custom_components.openrouteservice.api.openrouteservice.Client") as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        client_instance.directions.return_value = {"routes": []}

        api = OpenRouteServiceAPI(hass, "test_api_key")
        origin = (13.388860, 52.517037)
        destination = (13.397634, 52.529407)

        with pytest.raises(ValueError, match="No route found"):
            await api.get_directions(origin, destination)


async def test_get_directions_api_error(hass: HomeAssistant, mock_ors_client_auth_error):
    """Test directions with API error."""
    # Mock directions method instead of pelias_search
    with patch("custom_components.openrouteservice.api.openrouteservice.Client") as mock_client:
        from openrouteservice import exceptions

        client_instance = MagicMock()
        mock_client.return_value = client_instance
        client_instance.directions.side_effect = exceptions.ApiError("API Error")

        api = OpenRouteServiceAPI(hass, "test_api_key")
        origin = (13.388860, 52.517037)
        destination = (13.397634, 52.529407)

        with pytest.raises(CannotConnect):
            await api.get_directions(origin, destination)
