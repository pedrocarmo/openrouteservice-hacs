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

        # Mock successful directions
        client_instance.directions.return_value = {
            "routes": [
                {
                    "summary": {
                        "distance": 5420.5,
                        "duration": 720.3
                    },
                    "geometry": "test_encoded_polyline",
                    "segments": [
                        {
                            "distance": 5420.5,
                            "duration": 720.3,
                            "steps": []
                        }
                    ]
                }
            ]
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
