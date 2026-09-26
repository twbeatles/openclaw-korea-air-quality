"""지역 결정 오케스트레이션: shared-location > lat/lon > region > saved (SRP).

argparse Namespace에 직접 의존하던 원본 resolve_region 을 그대로 옮겼다.
"""
from __future__ import annotations

import argparse
from typing import Any, Dict, Tuple

from .. import geo as geo_module
from .. import store as store_module
from ..parsing import parse_shared_location


def resolve_region(
    args: argparse.Namespace,
    geocode=geo_module.geocode_region,
    nearest=geo_module.nearest_known_region,
    load_prefs=store_module.load_preferences,
) -> Tuple[Dict[str, Any], str]:
    shared = parse_shared_location(getattr(args, "location_text", None))
    if shared:
        region = nearest(float(shared["lat"]), float(shared["lon"]))
        return region, "shared-location"
    if getattr(args, "lat", None) is not None and getattr(args, "lon", None) is not None:
        region = nearest(args.lat, args.lon)
        return region, "location"
    if getattr(args, "region", None):
        return geocode(args.region), "query"
    if getattr(args, "user", None):
        prefs = load_prefs()
        user_info = prefs.get("users", {}).get(args.user, {})
        if user_info.get("default_location"):
            lat = float(user_info["default_location"]["lat"])
            lon = float(user_info["default_location"]["lon"])
            region = nearest(lat, lon)
            return region, "saved-location"
        if user_info.get("default_region"):
            return geocode(user_info["default_region"]), "saved-default"
    raise ValueError("지역을 확인할 수 없습니다. 지역명을 입력하거나 저장된 기본 지역/좌표를 사용하세요.")
