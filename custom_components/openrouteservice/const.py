"""Constants for the OpenRouteService integration."""

DOMAIN = "openrouteservice"

# Config
CONF_API_KEY = "api_key"

# Services
SERVICE_PLAN_ROUTE = "plan_route"

# Service parameters
ATTR_ORIGIN = "origin"
ATTR_DESTINATION = "destination"
ATTR_PROFILE = "profile"

# Defaults
DEFAULT_PROFILE = "driving-car"

# Profiles
PROFILES = [
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "foot-walking",
    "wheelchair",
]

# API
API_BASE_URL = "https://api.openrouteservice.org"
API_TIMEOUT = 30
