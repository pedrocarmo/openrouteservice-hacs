"""Common fixtures for OpenRouteService tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_ors_client():
    """Mock OpenRouteService client."""
    with patch("custom_components.openrouteservice.api.openrouteservice.Client") as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance

        # Mock successful pelias_search for validation
        client_instance.pelias_search.return_value = {
            "features": [
                {
                    "geometry": {"coordinates": [13.388860, 52.517037]},
                    "properties": {"name": "Test Location"}
                }
            ]
        }

        # Mock successful directions (GeoJSON FeatureCollection format)
        client_instance.directions.return_value = {
            "type": "FeatureCollection",
            "bbox": [-8.973121, 38.701823, -8.944642, 38.73037],
            "features": [
                {
                    "type": "Feature",
                    "bbox": [-8.973121, 38.701823, -8.944642, 38.73037],
                    "properties": {
                        "summary": {
                            "distance": 5420.5,
                            "duration": 720.3
                        },
                        "segments": [
                            {
                                "distance": 5420.5,
                                "duration": 720.3,
                                "steps": [
                                    {
                                        "distance": 241.4,
                                        "duration": 22.8,
                                        "type": 11,
                                        "instruction": "Head southeast",
                                        "name": "Test Street",
                                        "way_points": [0, 8]
                                    }
                                ]
                            }
                        ],
                        "way_points": [0, 142]
                    },
                    "geometry": {
                        "coordinates": [
                            [13.388860, 52.517037],
                            [13.397634, 52.529407]
                        ],
                        "type": "LineString"
                    }
                }
            ],
            "metadata": {
                "attribution": "openrouteservice.org | OpenStreetMap contributors",
                "service": "routing",
                "query": {
                    "coordinates": [[13.388860, 52.517037], [13.397634, 52.529407]],
                    "profile": "driving-car",
                    "format": "geojson"
                }
            }
        }

        yield client_instance


@pytest.fixture
def mock_ors_client_auth_error():
    """Mock OpenRouteService client with auth error."""
    with patch("custom_components.openrouteservice.api.openrouteservice.Client") as mock_client:
        from openrouteservice import exceptions

        client_instance = MagicMock()
        mock_client.return_value = client_instance
        client_instance.pelias_search.side_effect = exceptions.ApiError("401 Unauthorized")

        yield client_instance


@pytest.fixture
def mock_ors_client_timeout():
    """Mock OpenRouteService client with timeout."""
    with patch("custom_components.openrouteservice.api.openrouteservice.Client") as mock_client:
        from openrouteservice import exceptions

        client_instance = MagicMock()
        mock_client.return_value = client_instance
        client_instance.pelias_search.side_effect = exceptions.Timeout("Request timeout")

        yield client_instance


@pytest.fixture
def mock_ors_client_no_features():
    """Mock OpenRouteService client with no geocoding results."""
    with patch("custom_components.openrouteservice.api.openrouteservice.Client") as mock_client:
        client_instance = MagicMock()
        mock_client.return_value = client_instance
        client_instance.pelias_search.return_value = {"features": []}

        yield client_instance
