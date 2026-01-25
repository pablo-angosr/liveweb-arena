"""Weather API client with caching support (wttr.in)"""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# Global cache context reference (set by env.py during evaluation)
_cache_context: Optional[Any] = None


def set_weather_cache_context(context: Optional[Any]):
    """Set the cache context for Weather API calls."""
    global _cache_context
    _cache_context = context


def get_weather_cache_context() -> Optional[Any]:
    """Get the current cache context."""
    return _cache_context


class WeatherClient:
    """
    Centralized wttr.in API client with caching support.

    Uses JSON format for structured weather data.
    """

    API_BASE = "https://wttr.in"

    # Rate limiting
    _last_request_time: float = 0
    _min_request_interval: float = 0.5  # seconds between requests
    _lock = asyncio.Lock()

    @classmethod
    async def _rate_limit(cls):
        """Apply rate limiting."""
        async with cls._lock:
            import time
            now = time.time()
            elapsed = now - cls._last_request_time
            if elapsed < cls._min_request_interval:
                await asyncio.sleep(cls._min_request_interval - elapsed)
            cls._last_request_time = time.time()

    @classmethod
    def _normalize_location(cls, location: str) -> str:
        """Normalize location string for cache key matching."""
        # Convert to lowercase and replace spaces with +
        normalized = location.lower().strip()
        normalized = normalized.replace(" ", "+")
        # Remove trailing country specifications for matching
        # e.g., "tokyo,japan" and "tokyo" should match
        return normalized

    @classmethod
    async def get_weather_data(
        cls,
        location: str,
        timeout: float = 15.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather data for a location.

        Args:
            location: Location query (city name, airport code, etc.)
            timeout: Request timeout in seconds

        Returns:
            Weather JSON data or None on error
        """
        # Try cache first
        ctx = get_weather_cache_context()
        if ctx is not None:
            api_data = ctx.get_api_data("weather")
            if api_data:
                locations = api_data.get("locations", {})

                # Try exact match first
                location_data = locations.get(location)
                if location_data:
                    logger.debug(f"Cache hit: Weather {location}")
                    return location_data

                # Try normalized match
                normalized = cls._normalize_location(location)
                for cached_loc, cached_data in locations.items():
                    if cls._normalize_location(cached_loc) == normalized:
                        logger.debug(f"Cache hit (normalized): Weather {location}")
                        return cached_data

                # Try partial match (city name without country)
                city_part = location.split(",")[0].strip().lower()
                for cached_loc, cached_data in locations.items():
                    cached_city = cached_loc.split(",")[0].strip().lower()
                    if cached_city == city_part:
                        logger.debug(f"Cache hit (city match): Weather {location}")
                        return cached_data

                logger.debug(f"Cache miss for Weather {location}, falling back to API")

        # Fall back to live API
        await cls._rate_limit()

        url = f"{cls.API_BASE}/{location}?format=j1"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                if response.status_code == 404:
                    logger.warning(f"Weather location not found: {location}")
                    return None
                if response.status_code != 200:
                    logger.warning(f"Weather API error for {location}: {response.status_code}")
                    return None
                return response.json()

        except httpx.TimeoutException:
            logger.warning(f"Weather timeout for {location}")
            return None
        except Exception as e:
            logger.warning(f"Weather error for {location}: {e}")
            return None
