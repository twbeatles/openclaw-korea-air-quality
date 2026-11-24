"""provider 선택/팩토리: 설정 기반 provider 결정 + fetch 위임 (DIP).

신규 소스 추가는 레지스트리에 한 줄 등록으로 끝나며,
상위 계층(commands/regions)은 이 모듈의 이름 목록에만 의존한다.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from .. import store as store_module
from .airkorea import AirKoreaProvider, fetch_airkorea_air_quality
from .openmeteo import OpenMeteoProvider, fetch_openmeteo_air_quality, fetch_weather

__all__ = [
    "AirKoreaProvider",
    "OpenMeteoProvider",
    "PROVIDER_NAMES",
    "PROVIDER_REGISTRY",
    "fetch_air_quality",
    "fetch_airkorea_air_quality",
    "fetch_openmeteo_air_quality",
    "fetch_weather",
    "resolve_provider",
]

# 이름 -> (표시명, fetch 함수). 신규 provider는 구현 후 여기만 등록.
PROVIDER_REGISTRY: Dict[str, Tuple[str, Callable[..., Dict[str, Any]]]] = {
    "openmeteo": ("Open-Meteo (무키 즉시 실행)", fetch_openmeteo_air_quality),
    "airkorea": ("한국환경공단 에어코리아 실측", fetch_airkorea_air_quality),
}
PROVIDER_NAMES: Tuple[str, ...] = tuple(PROVIDER_REGISTRY)


def resolve_provider(explicit_provider: str | None, load_cfg=store_module.load_config) -> str:
    if explicit_provider:
        if explicit_provider not in PROVIDER_REGISTRY:
            supported = ", ".join(PROVIDER_NAMES)
            raise ValueError(f"지원하지 않는 provider입니다: {explicit_provider} (지원: {supported})")
        return explicit_provider
    configured = load_cfg().get("provider", "openmeteo")
    if configured not in PROVIDER_REGISTRY:
        supported = ", ".join(PROVIDER_NAMES)
        raise ValueError(f"설정의 provider가 유효하지 않습니다: {configured} (지원: {supported})")
    return configured


def fetch_air_quality(
    lat: float,
    lon: float,
    timezone: str = "Asia/Seoul",
    provider: str | None = None,
    region: Dict[str, Any] | None = None,
    http_client=None,
) -> Dict[str, Any]:
    resolved_provider = resolve_provider(provider)
    if resolved_provider == "airkorea":
        return fetch_airkorea_air_quality(lat, lon, timezone, region=region, http_client=http_client)
    return fetch_openmeteo_air_quality(lat, lon, timezone, http_client=http_client)
