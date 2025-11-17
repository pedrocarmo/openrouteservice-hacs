"""Persistent caching for OpenRouteService API calls."""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class PersistentCache:
    """Base class for persistent JSON cache with TTL."""

    def __init__(
        self,
        hass: HomeAssistant,
        cache_file: str,
        ttl_days: int,
    ) -> None:
        """
        Initialize persistent cache.

        Args:
            hass: Home Assistant instance
            cache_file: Cache file name (e.g., ".openrouteservice_geocoding_cache.json")
            ttl_days: Time-to-live in days (0 = disabled)
        """
        self.hass = hass
        self.ttl_days = ttl_days
        self.cache_path = Path(hass.config.path(cache_file))
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_path.exists():
            _LOGGER.debug("Cache file does not exist: %s", self.cache_path)
            self._cache = {}
            return

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            _LOGGER.info("Loaded cache from %s with %d entries", self.cache_path, len(self._cache))
        except Exception as err:
            _LOGGER.error("Failed to load cache from %s: %s", self.cache_path, err)
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            # Ensure parent directory exists
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            _LOGGER.debug("Saved cache to %s with %d entries", self.cache_path, len(self._cache))
        except Exception as err:
            _LOGGER.error("Failed to save cache to %s: %s", self.cache_path, err)

    def _make_key(self, *args: Any) -> str:
        """
        Create cache key from arguments.

        Args:
            *args: Arguments to hash

        Returns:
            SHA256 hash of arguments
        """
        key_string = "|".join(str(arg) for arg in args)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def _is_expired(self, timestamp: str) -> bool:
        """
        Check if cache entry is expired.

        Args:
            timestamp: ISO format timestamp string

        Returns:
            True if expired or ttl_days is 0
        """
        if self.ttl_days == 0:
            return True  # Cache disabled

        try:
            cached_time = datetime.fromisoformat(timestamp)
            expiry_time = cached_time + timedelta(days=self.ttl_days)
            return datetime.now() >= expiry_time
        except Exception as err:
            _LOGGER.error("Failed to parse timestamp %s: %s", timestamp, err)
            return True  # Treat as expired if we can't parse

    def get(self, *args: Any) -> Any | None:
        """
        Get cached value.

        Args:
            *args: Arguments to create cache key

        Returns:
            Cached value or None if not found or expired
        """
        if self.ttl_days == 0:
            return None  # Cache disabled

        key = self._make_key(*args)
        entry = self._cache.get(key)

        if entry is None:
            _LOGGER.debug("Cache miss for key: %s", key[:16])
            return None

        if self._is_expired(entry["timestamp"]):
            _LOGGER.debug("Cache expired for key: %s", key[:16])
            # Remove expired entry
            del self._cache[key]
            self._save_cache()
            return None

        _LOGGER.debug("Cache hit for key: %s", key[:16])
        return entry["value"]

    def set(self, value: Any, *args: Any) -> None:
        """
        Set cached value.

        Args:
            value: Value to cache
            *args: Arguments to create cache key
        """
        if self.ttl_days == 0:
            return  # Cache disabled

        key = self._make_key(*args)
        self._cache[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        self._save_cache()
        _LOGGER.debug("Cached value for key: %s", key[:16])

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache = {}
        self._save_cache()
        _LOGGER.info("Cleared cache: %s", self.cache_path)

    def update_ttl(self, ttl_days: int) -> None:
        """
        Update TTL and remove expired entries.

        Args:
            ttl_days: New TTL in days
        """
        old_ttl = self.ttl_days
        self.ttl_days = ttl_days
        _LOGGER.info("Updated cache TTL from %d to %d days", old_ttl, ttl_days)

        if ttl_days == 0:
            # Cache disabled, clear everything
            self.clear()
            return

        # Remove expired entries with new TTL
        expired_keys = [
            key for key, entry in self._cache.items()
            if self._is_expired(entry["timestamp"])
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self._save_cache()
            _LOGGER.info("Removed %d expired entries after TTL update", len(expired_keys))


class GeocodingCache(PersistentCache):
    """Cache for geocoding results."""

    def get_coordinates(self, address: str) -> tuple[float, float] | None:
        """
        Get cached coordinates for address.

        Args:
            address: Address string

        Returns:
            (longitude, latitude) tuple or None
        """
        result = self.get(address.lower())  # Case-insensitive
        if result:
            return tuple(result)
        return None

    def set_coordinates(self, address: str, coords: tuple[float, float]) -> None:
        """
        Cache coordinates for address.

        Args:
            address: Address string
            coords: (longitude, latitude) tuple
        """
        self.set(list(coords), address.lower())  # Store as list for JSON


class RouteCache(PersistentCache):
    """Cache for route calculation results."""

    def get_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str,
        units: str,
    ) -> dict[str, Any] | None:
        """
        Get cached route.

        Args:
            origin: (longitude, latitude) tuple
            destination: (longitude, latitude) tuple
            profile: Transportation profile
            units: Distance units

        Returns:
            Route data or None
        """
        return self.get(origin, destination, profile, units)

    def set_route(
        self,
        route: dict[str, Any],
        origin: tuple[float, float],
        destination: tuple[float, float],
        profile: str,
        units: str,
    ) -> None:
        """
        Cache route.

        Args:
            route: Route data from API
            origin: (longitude, latitude) tuple
            destination: (longitude, latitude) tuple
            profile: Transportation profile
            units: Distance units
        """
        self.set(route, origin, destination, profile, units)
