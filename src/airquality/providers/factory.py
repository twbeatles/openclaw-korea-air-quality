"""provider 선택/팩토리: 설정 기반 provider 결정 + fetch 위임 (DIP)."""
from __future__ import annotations

from typing import Any, Dict

from .. import store as store_module
from .airkorea import AirKoreaProvider, fetch_airkorea_air_quality
from .openmeteo import OpenMeteoProvider, fetch_openmeteo_air_quality, fetch_weather

__all__ = [
    "AirKoreaProvider",
    "OpenMeteoProvider",
    "fetch_air_quality",
    "fetch_airkorea_air_quality",
    "fetch_openmeteo_air_quality",
    "fetch_weather",
    "resolve_provider",
]


def resolve_provider(explicit_provider: str | None, load_cfg=store_module.load_config) -> str:
    if explicit_provider:
        return explicit_provider
    return load_cfg().get("provider", "openmeteo")


def fetch_air_quality(
    lat: float,
    lon: float,
    timezone: str = "Asia/Seoul",
    provider: str | None = None,
    region: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    resolved_provider = resolve_provider(provider)
    if resolved_provider == "airkorea":
        return fetch_airkorea_air_quality(lat, lon, timezone, region=region)
    return fetch_openmeteo_air_quality(lat, lon, timezone)
