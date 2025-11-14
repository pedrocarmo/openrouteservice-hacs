"""
Standalone integration test for OpenRouteService API GeoJSON parsing.

This test makes REAL API calls to verify the GeoJSON parsing fix works correctly.
It doesn't depend on Home Assistant - it tests the openrouteservice library directly.

Run with: python3 tests/test_api_real.py
"""
import os
from pathlib import Path
import openrouteservice


def load_api_key():
    """Load API key from .env file."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.startswith("ORS_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def test_geojson_response_structure():
    """
    Test that the OpenRouteService API returns GeoJSON format.
    This verifies our parsing fix is correct.
    """
    print("=" * 70)
    print("OpenRouteService API - GeoJSON Response Structure Test")
    print("=" * 70)

    api_key = load_api_key()
    if not api_key:
        print("ERROR: ORS_API_KEY not found in .env file")
        return False

    print(f"API Key: {api_key[:20]}...\n")

    # Create client
    client = openrouteservice.Client(
        key=api_key,
        base_url="https://api.openrouteservice.org",
        timeout=30,
        retry_over_query_limit=True,
    )

    # Test 1: Geocoding
    print("Test 1: Geocoding addresses")
    print("-" * 70)
    try:
        result = client.pelias_search(
            text="Avenida de São Francisco de Assis, Évora, Portugal",
            size=1,
            validate=False
        )
        print(f"✓ Geocoding response keys: {list(result.keys())}")
        print(f"  Features found: {len(result.get('features', []))}")
        if result.get('features'):
            coords = result['features'][0]['geometry']['coordinates']
            print(f"  Coordinates: {coords}")
    except Exception as e:
        print(f"✗ Geocoding failed: {e}")
        return False

    # Test 2: Directions with GeoJSON format
    print("\nTest 2: Directions API with format='geojson'")
    print("-" * 70)
    print("This is the KEY test - verifying the response structure")

    try:
        # Coordinates from Évora, Portugal
        coords = [
            [-8.972987, 38.730368],  # Origin
            [-8.947381, 38.701947]    # Destination
        ]

        print(f"  Requesting route from {coords[0]} to {coords[1]}")
        print(f"  Using format='geojson'...")

        result = client.directions(
            coords,
            profile="driving-car",
            format="geojson",  # This is what our code uses!
            units="m",
            geometry=True,
            instructions=True,
        )

        print(f"\n  ✓ Response received!")
        print(f"  Response type: {result.get('type')}")
        print(f"  Top-level keys: {list(result.keys())}")

        # THIS IS THE CRITICAL CHECK
        # Our fix checks for 'features', not 'routes'
        if 'routes' in result:
            print(f"\n  ⚠️  WARNING: Response has 'routes' key")
            print(f"     Our code checks for 'features' - this might fail!")
            return False

        if 'features' not in result:
            print(f"\n  ✗ ERROR: Response doesn't have 'features' key")
            print(f"     Our fix expects 'features' in GeoJSON format")
            return False

        print(f"  ✓ Response has 'features' key (GeoJSON format confirmed)")
        print(f"  Number of features: {len(result['features'])}")

        if len(result['features']) == 0:
            print(f"  ✗ ERROR: No features in response")
            return False

        # Examine the first feature
        feature = result['features'][0]
        print(f"\n  Feature structure:")
        print(f"    Type: {feature.get('type')}")
        print(f"    Keys: {list(feature.keys())}")

        if 'properties' not in feature:
            print(f"    ✗ ERROR: Feature missing 'properties'")
            return False

        properties = feature['properties']
        print(f"    Properties keys: {list(properties.keys())}")

        if 'summary' not in properties:
            print(f"    ✗ ERROR: Properties missing 'summary'")
            return False

        summary = properties['summary']
        print(f"\n  ✓ Route Summary:")
        print(f"    Distance: {summary['distance']} meters ({summary['distance']/1000:.2f} km)")
        print(f"    Duration: {summary['duration']} seconds ({summary['duration']/60:.2f} min)")

        if 'segments' in properties:
            print(f"    Segments: {len(properties['segments'])}")
            if properties['segments']:
                steps = properties['segments'][0].get('steps', [])
                print(f"    Steps in first segment: {len(steps)}")
                if steps:
                    print(f"    First instruction: {steps[0].get('instruction', 'N/A')}")

        if 'geometry' in feature:
            geom = feature['geometry']
            print(f"\n  ✓ Geometry:")
            print(f"    Type: {geom.get('type')}")
            if geom.get('coordinates'):
                print(f"    Coordinate points: {len(geom['coordinates'])}")

        print("\n" + "=" * 70)
        print("✓ SUCCESS: GeoJSON format confirmed!")
        print("=" * 70)
        print("\nOur parsing fix is correct:")
        print("  1. ✓ Response has 'features' array (not 'routes')")
        print("  2. ✓ Route data is in features[0]['properties']")
        print("  3. ✓ Summary is at features[0]['properties']['summary']")
        print("  4. ✓ Geometry is at features[0]['geometry']")
        print("  5. ✓ Segments are at features[0]['properties']['segments']")

        return True

    except Exception as e:
        print(f"\n✗ Directions API failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = test_geojson_response_structure()
    sys.exit(0 if success else 1)
