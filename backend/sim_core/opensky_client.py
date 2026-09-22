"""
OpenSky Network ADS-B Ingestion & Reference Trajectory Service.
Fetches real-world commercial flight tracking data via the OpenSky Network REST API
with local disk caching, rate-limit backoff, and offline recorded flight fallback.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, cast


class OpenSkyClient:
    """
    Client for OpenSky Network REST API.
    Supports anonymous access (rate-limited by IP) and authenticated access
    via environment variables OPENSKY_USERNAME and OPENSKY_PASSWORD.
    """

    BASE_URL = "https://opensky-network.org/api"

    def __init__(self, cache_dir: str = "data/opensky_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.username = os.environ.get("OPENSKY_USERNAME")
        self.password = os.environ.get("OPENSKY_PASSWORD")
        self.last_request_time = 0.0
        # Anonymous users are limited to 1 request per 10 seconds
        self.min_request_interval_s = 5.0 if self.username else 10.0

    def _build_request(self, url: str) -> urllib.request.Request:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "AeroHybrid-Research-Platform/1.0 (Academic/Engineering Analysis)")
        if self.username and self.password:
            auth_str = f"{self.username}:{self.password}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")
            req.add_header("Authorization", f"Basic {b64_auth}")
        return req

    def fetch_live_states(
        self,
        bbox: tuple[float, float, float, float] = (8.0, 68.0, 35.0, 97.0),
        timeout_s: float = 6.0
    ) -> dict[str, Any]:
        """
        Fetches live state vectors within geographical bounding box (min_lat, min_lon, max_lat, max_lon).
        Default bounding box covers India FIR airspace.
        """
        min_lat, min_lon, max_lat, max_lon = bbox
        url = f"{self.BASE_URL}/states/all?lamin={min_lat}&lomin={min_lon}&lamax={max_lat}&lomax={max_lon}"
        cache_key = f"states_{int(min_lat)}_{int(min_lon)}_{int(max_lat)}_{int(max_lon)}.json"
        cache_file = os.path.join(self.cache_dir, cache_key)

        # Enforce rate-limit interval
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_request_interval_s:
            # Check if cache is fresh (< 60s old)
            if os.path.exists(cache_file) and (now - os.path.getmtime(cache_file)) < 60.0:
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    data["source"] = "LOCAL_CACHE"
                    return cast(dict[str, Any], data)

        try:
            req = self._build_request(url)
            self.last_request_time = time.time()
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                data["source"] = "OPENSKY_LIVE"
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                return cast(dict[str, Any], data)
        except Exception as e:
            # Fallback to cache if available
            if os.path.exists(cache_file):
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    data["source"] = "LOCAL_CACHE_FALLBACK"
                    data["warning"] = f"Live OpenSky query failed ({str(e)}). Returned cached states."
                    return cast(dict[str, Any], data)
            return {
                "time": int(time.time()),
                "states": [],
                "source": "EMPTY_FALLBACK",
                "warning": f"OpenSky live query unavailable: {str(e)}"
            }

    def fetch_track(self, icao24: str, target_time: int = 0, timeout_s: float = 6.0) -> dict[str, Any]:
        """
        Fetches aircraft trajectory for a given 24-bit ICAO transponder address.
        """
        url = f"{self.BASE_URL}/tracks/all?icao24={icao24.lower()}&time={target_time}"
        cache_file = os.path.join(self.cache_dir, f"track_{icao24.lower()}.json")

        try:
            req = self._build_request(url)
            self.last_request_time = time.time()
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                data["source"] = "OPENSKY_LIVE"
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                return cast(dict[str, Any], data)
        except Exception as e:
            if os.path.exists(cache_file):
                with open(cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    data["source"] = "LOCAL_CACHE_FALLBACK"
                    data["warning"] = f"Track query failed ({str(e)}). Used cached track."
                    return cast(dict[str, Any], data)
            return {
                "icao24": icao24,
                "path": [],
                "source": "UNAVAILABLE",
                "error": str(e)
            }

    @staticmethod
    def get_reference_route_trajectory(route_id: str) -> dict[str, Any]:
        """
        Loads the verified recorded commercial ADS-B flight profile for an Indian regional sector.
        Guarantees 100% reproducible validation without relying on internet connectivity.
        """
        filename_map = {
            "BOM-PNQ": "BOM_PNQ_recorded.json",
            "BLR-IXG": "BLR_IXG_recorded.json",
            "DEL-DED": "DEL_DED_recorded.json"
        }
        fname = filename_map.get(route_id)
        if not fname:
            raise FileNotFoundError(f"No recorded reference trajectory available for route '{route_id}'")

        file_path = os.path.join("data", "real_flights", fname)
        with open(file_path, encoding="utf-8") as f:
            return cast(dict[str, Any], json.load(f))
