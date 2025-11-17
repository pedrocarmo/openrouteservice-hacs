"""Tests for OpenRouteService caching."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

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
