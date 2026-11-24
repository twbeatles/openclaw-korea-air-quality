"""Open-Meteo provider + 날씨 조회 (단일 책임: Open-Meteo API 매핑).

요청 필드는 constants의 OPENMETEO_*_FIELDS에서 관리하므로,
상류 변수 추가/변경 시 그곳만 고치면 된다.
"""
from __future__ import annotations

from typing import Any, Dict

from .. import constants as constants_module
from .. import http as http_module
from ..constants import OPENMETEO_AIR_URL, OPENMETEO_WEATHER_URL


class OpenMeteoProvider:
    name = "openmeteo"

    def __init__(self, http_client: http_module.HttpClient | None = None) -> None:
        self._http = http_client or http_module.HttpClient()

    def fetch(self, lat: float, lon: float, timezone: str = "Asia/Seoul", region: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = self._http.fetch_json(OPENMETEO_AIR_URL, {"latitude": lat, "longitude": lon, "timezone": timezone, "current": constants_module.OPENMETEO_AIR_CURRENT_FIELDS, "forecast_days": 1})
        current = payload.get("current") or {}
        result: Dict[str, Any] = {"time": current.get("time"), "pm10": current.get("pm10"), "pm2_5": current.get("pm2_5"), "ozone": current.get("ozone"), "us_aqi": current.get("us_aqi"), "european_aqi": current.get("european_aqi"), "provider": "openmeteo"}
        pollutants = {
            key: current.get(key)
            for key in ("carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide")
            if current.get(key) is not None
        }
        if pollutants:
            result["pollutants"] = pollutants
        return result


def fetch_openmeteo_air_quality(lat: float, lon: float, timezone: str = "Asia/Seoul", http_client: http_module.HttpClient | None = None) -> Dict[str, Any]:
    return OpenMeteoProvider(http_client=http_client).fetch(lat, lon, timezone)


def fetch_weather(lat: float, lon: float, timezone: str = "Asia/Seoul", http_client: http_module.HttpClient | None = None) -> Dict[str, Any]:
    client = http_client or http_module.HttpClient()
    payload = client.fetch_json(OPENMETEO_WEATHER_URL, {"latitude": lat, "longitude": lon, "timezone": timezone, "current": constants_module.OPENMETEO_WEATHER_CURRENT_FIELDS, "daily": constants_module.OPENMETEO_WEATHER_DAILY_FIELDS, "forecast_days": 1})
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    return {"current_temp": current.get("temperature_2m"), "apparent_temp": current.get("apparent_temperature"), "current_weather_code": current.get("weather_code"), "today_max": (daily.get("temperature_2m_max") or [None])[0], "today_min": (daily.get("temperature_2m_min") or [None])[0], "precipitation_probability_max": (daily.get("precipitation_probability_max") or [None])[0], "today_weather_code": (daily.get("weather_code") or [None])[0]}
