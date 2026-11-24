"""지역 해석: 정적 지역 -> 로컬 캐시 -> 외부 지오코딩, 좌표 근접 매칭 (SRP).

상위 계층은 이 클래스의 두 메서드만 사용한다 (DIP: HttpClient/store 주입 가능).
"""
from __future__ import annotations

import math
from typing import Any, Dict

from . import http as http_module
from . import store as store_module
from .constants import DISTRICT_FALLBACKS, OPENMETEO_GEOCODING_URL, STATIC_REGIONS
from .parsing import normalize_region_name


class RegionResolver:
    def __init__(
        self,
        http_client: http_module.HttpClient | None = None,
        load_cache=store_module.load_station_cache,
        save_cache=store_module.save_station_cache,
    ) -> None:
        self._http = http_client or http_module.HttpClient()
        self._load_cache = load_cache
        self._save_cache = save_cache

    def geocode(self, region: str) -> Dict[str, Any]:
        normalized = normalize_region_name(region)
        # 1. 정적 정의 지역 우선 확인 (신뢰 데이터)
        if normalized in STATIC_REGIONS:
            return {"query": region, **STATIC_REGIONS[normalized]}
        fallback = DISTRICT_FALLBACKS.get(normalized)
        if fallback and fallback in STATIC_REGIONS:
            return {"query": region, **STATIC_REGIONS[fallback]}

        # 2. 로컬 캐시 확인
        cache = self._load_cache()
        cached = cache.setdefault("regions", {}).get(normalized)
        if cached:
            return cached

        # 3. 외부 지오코딩 API 호출
        payload = self._http.fetch_json(OPENMETEO_GEOCODING_URL, {"name": normalized, "count": 5, "language": "ko", "format": "json", "countryCode": "KR"})
        results = payload.get("results") or []
        if not results and " " in normalized:
            payload = self._http.fetch_json(OPENMETEO_GEOCODING_URL, {"name": normalized.split()[-1], "count": 5, "language": "ko", "format": "json", "countryCode": "KR"})
            results = payload.get("results") or []
        if not results and normalized.endswith(("동", "읍", "면", "구")):
            trimmed = normalized[:-1]
            payload = self._http.fetch_json(OPENMETEO_GEOCODING_URL, {"name": trimmed, "count": 5, "language": "ko", "format": "json", "countryCode": "KR"})
            results = payload.get("results") or []
        if not results:
            raise ValueError(f"대한민국 지역 후보를 찾지 못했습니다: {region}")
        best = results[0]
        resolved = {"query": region, "resolved_name": best.get("name") or normalized, "admin1": best.get("admin1"), "admin2": best.get("admin2"), "admin3": best.get("admin3"), "country": best.get("country"), "latitude": best["latitude"], "longitude": best["longitude"], "timezone": best.get("timezone", "Asia/Seoul")}
        cache.setdefault("regions", {})[normalized] = resolved
        self._save_cache(cache)
        return resolved

    def nearest(self, lat: float, lon: float) -> Dict[str, Any]:
        # 정적 거점을 항상 포함하고 캐시가 있으면 덮어쓴다.
        # (캐시에 1~2개만 있을 때도 전체 후보에서 최인접을 찾도록)
        merged: Dict[str, Dict[str, Any]] = {key: {"query": key, **value} for key, value in STATIC_REGIONS.items()}
        cached = self._load_cache().get("regions", {}) or {}
        for key, value in cached.items():
            if isinstance(value, dict) and value.get("latitude") is not None and value.get("longitude") is not None:
                merged[key] = value
        best_item = None
        best_distance = float("inf")
        for item in merged.values():
            try:
                distance = math.hypot(float(item["latitude"]) - lat, float(item["longitude"]) - lon)
            except (TypeError, ValueError):
                continue
            if distance < best_distance:
                best_distance = distance
                best_item = item
        if not best_item:
            raise ValueError("좌표 기반 지역 추정에 실패했습니다.")
        return dict(best_item, matched_by="cached-nearest")


_DEFAULT_RESOLVER = RegionResolver()


def geocode_region(region: str) -> Dict[str, Any]:
    return _DEFAULT_RESOLVER.geocode(region)


def nearest_known_region(lat: float, lon: float) -> Dict[str, Any]:
    return _DEFAULT_RESOLVER.nearest(lat, lon)
