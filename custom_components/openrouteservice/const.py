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
ATTR_PREFERENCE = "preference"

# Defaults
DEFAULT_PROFILE = "driving-car"
DEFAULT_PREFERENCE = "fastest"

# Profiles
PROFILES = [
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "foot-walking",
    "wheelchair",
]

# Preferences
PREFERENCES = [
    "fastest",
    "shortest",
    "recommended",
]

# API
API_BASE_URL = "https://api.openrouteservice.org"
API_TIMEOUT = 30
