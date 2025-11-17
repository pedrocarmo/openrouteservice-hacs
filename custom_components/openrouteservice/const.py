"""Constants for the OpenRouteService integration."""

DOMAIN = "openrouteservice"

# Config
CONF_API_KEY = "api_key"

# Options
CONF_GEOCODING_CACHE_DAYS = "geocoding_cache_days"
CONF_ROUTE_CACHE_DAYS = "route_cache_days"
CONF_UNITS = "units"
CONF_LANGUAGE = "language"

# Services
SERVICE_PLAN_ROUTE = "plan_route"
SERVICE_CLEAR_CACHE = "clear_cache"

# Service parameters
ATTR_ORIGIN = "origin"
ATTR_DESTINATION = "destination"
ATTR_PROFILE = "profile"
ATTR_CACHE_TYPE = "cache_type"

# Defaults
DEFAULT_PROFILE = "driving-car"
DEFAULT_GEOCODING_CACHE_DAYS = 30
DEFAULT_ROUTE_CACHE_DAYS = 7
DEFAULT_UNITS = "km"
DEFAULT_LANGUAGE = "en"

# Profiles
PROFILES = [
    "driving-car",
    "driving-hgv",
    "cycling-regular",
    "foot-walking",
    "wheelchair",
]

# Units
UNITS = ["m", "km", "mi"]

# Languages (common languages + custom option)
LANGUAGES = [
    "en",  # English
    "de",  # German
    "es",  # Spanish
    "fr",  # French
    "it",  # Italian
    "pt",  # Portuguese
    "nl",  # Dutch
    "ru",  # Russian
    "zh",  # Chinese
    "ja",  # Japanese
    "custom",  # Custom language code
]

# Cache types
CACHE_TYPE_GEOCODING = "geocoding"
CACHE_TYPE_ROUTES = "routes"
CACHE_TYPE_ALL = "all"

CACHE_TYPES = [CACHE_TYPE_GEOCODING, CACHE_TYPE_ROUTES, CACHE_TYPE_ALL]

# Cache file names
GEOCODING_CACHE_FILE = ".openrouteservice_geocoding_cache.json"
ROUTES_CACHE_FILE = ".openrouteservice_routes_cache.json"

# API
API_BASE_URL = "https://api.openrouteservice.org"
API_TIMEOUT = 30
