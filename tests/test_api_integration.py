"""
Integration tests for OpenRouteService API.

These tests make REAL API calls to OpenRouteService using the API key from .env.
They verify that the GeoJSON response parsing works correctly with actual API responses.

Run with: python3 tests/test_api_integration.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import the component
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import api module directly to avoid __init__.py imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    "api",
    Path(__file__).parent.parent / "custom_components" / "openrouteservice" / "api.py"
)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)

OpenRouteServiceAPI = api_module.OpenRouteServiceAPI
CannotConnect = api_module.CannotConnect
InvalidAuth = api_module.InvalidAuth


class MockHass:
    """Minimal mock of Home Assistant for testing."""

    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def async_add_executor_job(self, func, *args):
        """Run blocking function in executor."""
        return await self.loop.run_in_executor(None, func, *args)


async def test_validate_api_key(api: OpenRouteServiceAPI):
    """Test API key validation with real API."""
    print("Testing API key validation...")
    try:
        result = await api.validate_api_key()
        print(f"✓ API key validation successful: {result}")
        return True
    except InvalidAuth as e:
        print(f"✗ API key is invalid: {e}")
        return False
    except CannotConnect as e:
        print(f"✗ Cannot connect to API: {e}")
        return False


async def test_geocode_address(api: OpenRouteServiceAPI):
    """Test address geocoding with real API."""
    print("\nTesting address geocoding...")

    test_addresses = [
        "Avenida de São Francisco de Assis, Évora, Portugal",
        "Praça Pedro Nunes, Évora, Portugal",
        "Berlin, Germany",
    ]

    all_passed = True
    for address in test_addresses:
        try:
            coords = await api.geocode_address(address)
            print(f"✓ Geocoded '{address}' to {coords}")

            # Verify coordinates are tuple of (lon, lat)
            assert isinstance(coords, tuple), "Coordinates must be a tuple"
            assert len(coords) == 2, "Coordinates must have 2 values"
            assert isinstance(coords[0], float), "Longitude must be float"
            assert isinstance(coords[1], float), "Latitude must be float"

        except Exception as e:
            print(f"✗ Failed to geocode '{address}': {e}")
            all_passed = False

    return all_passed


async def test_get_directions_geojson_parsing(api: OpenRouteServiceAPI):
    """Test directions with real API - verifies GeoJSON parsing fix."""
    print("\nTesting directions (GeoJSON parsing)...")

    # Test case from the user's original error
    origin_address = "Avenida de São Francisco de Assis, Évora, Portugal"
    dest_address = "Praça Pedro Nunes, Évora, Portugal"

    try:
        # First geocode the addresses
        print(f"  Geocoding origin: {origin_address}")
        origin = await api.geocode_address(origin_address)
        print(f"  Origin coordinates: {origin}")

        print(f"  Geocoding destination: {dest_address}")
        destination = await api.geocode_address(dest_address)
        print(f"  Destination coordinates: {destination}")

        # Get directions
        print(f"  Requesting route...")
        route = await api.get_directions(origin, destination, "driving-car")

        # Verify the route structure (this is what the fix ensures)
        print(f"  ✓ Route received!")
        print(f"    Keys in route: {list(route.keys())}")

        assert "summary" in route, "Route must have 'summary'"
        assert "distance" in route["summary"], "Summary must have 'distance'"
        assert "duration" in route["summary"], "Summary must have 'duration'"

        distance_km = route["summary"]["distance"] / 1000
        duration_min = route["summary"]["duration"] / 60

        print(f"    Distance: {distance_km:.2f} km")
        print(f"    Duration: {duration_min:.2f} minutes")

        assert "geometry" in route, "Route must have 'geometry'"
        if route["geometry"]:
            print(f"    Geometry: {route['geometry']['type']} with {len(route['geometry']['coordinates'])} points")

        assert "segments" in route, "Route must have 'segments'"
        print(f"    Segments: {len(route['segments'])} segment(s)")

        if route["segments"]:
            steps = route["segments"][0].get("steps", [])
            print(f"    Steps in first segment: {len(steps)}")
            if steps:
                print(f"    First instruction: {steps[0].get('instruction', 'N/A')}")

        print("  ✓ All route data validated successfully!")
        return True

    except Exception as e:
        print(f"  ✗ Failed to get directions: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_different_profiles(api: OpenRouteServiceAPI):
    """Test different routing profiles."""
    print("\nTesting different routing profiles...")

    # Simple route for testing profiles
    origin = (-8.972987, 38.730368)  # Évora coordinates
    destination = (-8.947381, 38.701947)

    profiles = ["driving-car", "foot-walking", "cycling-regular"]

    all_passed = True
    for profile in profiles:
        try:
            route = await api.get_directions(origin, destination, profile)
            distance_km = route["summary"]["distance"] / 1000
            duration_min = route["summary"]["duration"] / 60
            print(f"  ✓ {profile}: {distance_km:.2f} km, {duration_min:.2f} min")
        except Exception as e:
            print(f"  ✗ {profile} failed: {e}")
            all_passed = False

    return all_passed


async def test_no_route_scenario(api: OpenRouteServiceAPI):
    """Test handling of unreachable destinations."""
    print("\nTesting no-route scenario...")

    # Try routing between very distant points that might not be routable
    origin = (-8.972987, 38.730368)  # Évora, Portugal
    destination = (174.763336, -41.286461)  # Wellington, New Zealand

    try:
        route = await api.get_directions(origin, destination, "driving-car")
        print(f"  ? Unexpectedly got a route: {route['summary']}")
        print("    (API might have found a ferry route or similar)")
        return True
    except ValueError as e:
        if "No route found" in str(e):
            print(f"  ✓ Correctly raised ValueError: {e}")
            return True
        else:
            print(f"  ✗ Wrong ValueError message: {e}")
            return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False


async def main():
    """Run all integration tests."""
    # Load API key from .env
    api_key = os.getenv("ORS_API_KEY")
    if not api_key:
        # Try to load from .env file
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith("ORS_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break

    if not api_key:
        print("ERROR: ORS_API_KEY not found in environment or .env file")
        return False

    print("=" * 70)
    print("OpenRouteService API Integration Tests")
    print("=" * 70)
    print(f"API Key: {api_key[:20]}..." )

    # Create mock hass and API client
    hass = MockHass()
    api = OpenRouteServiceAPI(hass, api_key)

    # Run tests
    results = []

    results.append(await test_validate_api_key(api))
    results.append(await test_geocode_address(api))
    results.append(await test_get_directions_geojson_parsing(api))
    results.append(await test_different_profiles(api))
    results.append(await test_no_route_scenario(api))

    # Summary
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} test groups passed")

    if passed == total:
        print("✓ ALL TESTS PASSED!")
        print("\nThe GeoJSON parsing fix is working correctly!")
        return True
    else:
        print("✗ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
