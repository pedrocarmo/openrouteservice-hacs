"""Integration tests for OpenRouteService API.

These tests make real API calls to OpenRouteService and require a valid API key.
The API key should be stored in a .env file in the project root.

Run with: pytest -m integration
"""
import os
import pytest
from pathlib import Path

from homeassistant.core import HomeAssistant

from custom_components.openrouteservice.api import (
    OpenRouteServiceAPI,
    CannotConnect,
    InvalidAuth,
)


# Load API key from .env file
def load_api_key() -> str | None:
    """Load API key from .env file."""
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return None

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("ORS_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


API_KEY = load_api_key()
pytestmark = pytest.mark.integration

# Skip all tests in this module if no API key is available
if not API_KEY:
    pytest.skip(
        "Skipping integration tests: No API key found in .env file",
        allow_module_level=True,
    )


@pytest.mark.asyncio
async def test_validate_api_key_real(hass: HomeAssistant):
    """Test API key validation with real API."""
    api = OpenRouteServiceAPI(hass, API_KEY)
    result = await api.validate_api_key()

    assert result["valid"] is True
    assert "features_count" in result


@pytest.mark.asyncio
async def test_validate_invalid_api_key(hass: HomeAssistant):
    """Test that invalid API key is properly rejected."""
    api = OpenRouteServiceAPI(hass, "invalid_key_12345")

    with pytest.raises((InvalidAuth, CannotConnect)):
        await api.validate_api_key()


@pytest.mark.asyncio
async def test_geocode_real_address(hass: HomeAssistant):
    """Test geocoding a real address."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    # Test with a well-known location
    coords = await api.geocode_address("Brandenburg Gate, Berlin, Germany")

    assert isinstance(coords, tuple)
    assert len(coords) == 2

    # Brandenburg Gate coordinates (approximately)
    # longitude: ~13.377, latitude: ~52.516
    lon, lat = coords
    assert 13.0 < lon < 14.0, f"Longitude {lon} out of expected range for Berlin"
    assert 52.0 < lat < 53.0, f"Latitude {lat} out of expected range for Berlin"


@pytest.mark.asyncio
async def test_geocode_multiple_locations(hass: HomeAssistant):
    """Test geocoding various real locations."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    test_addresses = [
        ("Eiffel Tower, Paris, France", (2.0, 3.0), (48.0, 49.0)),  # lon, lat ranges
        ("Big Ben, London, UK", (-1.0, 0.5), (51.0, 52.0)),
        ("Times Square, New York, USA", (-74.5, -73.5), (40.0, 41.0)),
    ]

    for address, lon_range, lat_range in test_addresses:
        coords = await api.geocode_address(address)
        lon, lat = coords

        assert lon_range[0] < lon < lon_range[1], \
            f"{address}: Longitude {lon} not in expected range {lon_range}"
        assert lat_range[0] < lat < lat_range[1], \
            f"{address}: Latitude {lat} not in expected range {lat_range}"


@pytest.mark.asyncio
async def test_geocode_nonexistent_address(hass: HomeAssistant):
    """Test geocoding with an address that doesn't exist."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    # This should either fail or return unexpected coordinates
    with pytest.raises(ValueError, match="Could not geocode address"):
        await api.geocode_address("xyzabc123nonexistentplace456789")


@pytest.mark.asyncio
async def test_get_directions_real_route(hass: HomeAssistant):
    """Test getting directions between real locations."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    # Get coordinates for two locations in Berlin
    origin = await api.geocode_address("Brandenburg Gate, Berlin, Germany")
    destination = await api.geocode_address("Berlin Hauptbahnhof, Germany")

    # Get directions
    route = await api.get_directions(origin, destination, "driving-car")

    # Verify response structure
    assert "summary" in route
    assert "distance" in route["summary"]
    assert "duration" in route["summary"]
    assert "geometry" in route

    # The route should be reasonable (not too long for this short distance)
    # Brandenburg Gate to Hauptbahnhof is about 2-3 km
    distance_km = route["summary"]["distance"] / 1000
    assert 1.0 < distance_km < 10.0, f"Distance {distance_km}km seems unreasonable"

    # Duration should be reasonable (a few minutes by car)
    duration_min = route["summary"]["duration"] / 60
    assert 1.0 < duration_min < 30.0, f"Duration {duration_min}min seems unreasonable"


@pytest.mark.asyncio
async def test_get_directions_different_profiles(hass: HomeAssistant):
    """Test routing with different transportation profiles."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    # Use consistent coordinates for comparison
    origin = (13.377704, 52.516275)  # Brandenburg Gate
    destination = (13.394800, 52.520008)  # Alexanderplatz

    profiles_to_test = ["driving-car", "foot-walking", "cycling-regular"]
    results = {}

    for profile in profiles_to_test:
        route = await api.get_directions(origin, destination, profile)
        results[profile] = {
            "distance": route["summary"]["distance"],
            "duration": route["summary"]["duration"],
        }

    # Walking should generally take longer than driving or cycling for same distance
    # (though route distances might differ slightly)
    assert results["foot-walking"]["duration"] > results["driving-car"]["duration"]

    # All routes should have reasonable distances (approximately same)
    for profile, data in results.items():
        distance_km = data["distance"] / 1000
        assert 1.0 < distance_km < 5.0, \
            f"{profile}: Distance {distance_km}km seems unreasonable"


@pytest.mark.asyncio
async def test_coordinate_format_correctness(hass: HomeAssistant):
    """Test that coordinates are in correct format (longitude, latitude)."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    # Geocode a location
    coords = await api.geocode_address("Sydney Opera House, Australia")
    lon, lat = coords

    # Sydney is in the eastern hemisphere (positive longitude)
    # and southern hemisphere (negative latitude)
    assert 150.0 < lon < 152.0, f"Sydney longitude {lon} incorrect"
    assert -34.0 < lat < -33.0, f"Sydney latitude {lat} incorrect"

    # Now test that routing works with these coordinates
    # Route within Sydney
    origin = (151.2093, -33.8688)  # Sydney Opera House
    destination = (151.1852, -33.8915)  # Sydney Harbour Bridge

    route = await api.get_directions(origin, destination, "foot-walking")

    assert "summary" in route
    distance_km = route["summary"]["distance"] / 1000
    # Should be walkable distance (around 1-2 km)
    assert 0.5 < distance_km < 5.0


@pytest.mark.asyncio
async def test_api_error_handling(hass: HomeAssistant):
    """Test that API errors are properly handled."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    # Test with invalid coordinates (should fail or return error)
    invalid_origin = (999.0, 999.0)  # Invalid coordinates
    valid_destination = (13.377704, 52.516275)

    # This should raise an error
    with pytest.raises((CannotConnect, ValueError)):
        await api.get_directions(invalid_origin, valid_destination)


@pytest.mark.asyncio
async def test_long_distance_route(hass: HomeAssistant):
    """Test routing between distant cities."""
    api = OpenRouteServiceAPI(hass, API_KEY)

    # Berlin to Munich (roughly 500+ km)
    origin = await api.geocode_address("Berlin, Germany")
    destination = await api.geocode_address("Munich, Germany")

    route = await api.get_directions(origin, destination, "driving-car")

    # Verify reasonable distance and duration
    distance_km = route["summary"]["distance"] / 1000
    duration_hours = route["summary"]["duration"] / 3600

    assert 500 < distance_km < 700, f"Berlin-Munich distance {distance_km}km unreasonable"
    assert 4 < duration_hours < 10, f"Berlin-Munich duration {duration_hours}h unreasonable"
