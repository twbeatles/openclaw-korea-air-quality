from __future__ import annotations

import argparse
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PREFERENCES_PATH = DATA_DIR / "user-preferences.json"
STATION_CACHE_PATH = DATA_DIR / "station-cache.json"

OPENMETEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPENMETEO_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

REGION_ALIASES = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "제주": "제주특별자치도",
    "성동구": "서울특별시 성동구",
    "강남구": "서울특별시 강남구",
    "영통": "수원시 영통구",
    "수원 영통": "수원시 영통구",
    "분당": "성남시 분당구",
    "판교": "성남시 분당구 판교동",
    "잠실": "서울특별시 송파구 잠실동",
}

STATIC_REGIONS = {
    "서울특별시 성동구": {"resolved_name": "성동구", "admin1": "서울특별시", "admin2": "성동구", "admin3": None, "country": "대한민국", "latitude": 37.5636, "longitude": 127.0365, "timezone": "Asia/Seoul"},
    "서울특별시 강남구": {"resolved_name": "강남구", "admin1": "서울특별시", "admin2": "강남구", "admin3": None, "country": "대한민국", "latitude": 37.5172, "longitude": 127.0473, "timezone": "Asia/Seoul"},
    "수원시 영통구": {"resolved_name": "영통구", "admin1": "경기도", "admin2": "수원시 영통구", "admin3": None, "country": "대한민국", "latitude": 37.2595, "longitude": 127.0464, "timezone": "Asia/Seoul"},
    "성남시 분당구": {"resolved_name": "분당구", "admin1": "경기도", "admin2": "성남시 분당구", "admin3": None, "country": "대한민국", "latitude": 37.3826, "longitude": 127.1187, "timezone": "Asia/Seoul"},
    "성남시 분당구 판교동": {"resolved_name": "판교동", "admin1": "경기도", "admin2": "성남시 분당구", "admin3": "판교동", "country": "대한민국", "latitude": 37.3943, "longitude": 127.1112, "timezone": "Asia/Seoul"},
    "서울특별시 송파구 잠실동": {"resolved_name": "잠실동", "admin1": "서울특별시", "admin2": "송파구", "admin3": "잠실동", "country": "대한민국", "latitude": 37.5110, "longitude": 127.0811, "timezone": "Asia/Seoul"},
}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _json_default_payload() -> Dict[str, Any]:
    return {"users": {}}


def load_preferences() -> Dict[str, Any]:
    ensure_data_dir()
    if not PREFERENCES_PATH.exists():
        return _json_default_payload()
    return json.loads(PREFERENCES_PATH.read_text(encoding="utf-8"))


def save_preferences(payload: Dict[str, Any]) -> None:
    ensure_data_dir()
    PREFERENCES_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_station_cache() -> Dict[str, Any]:
    ensure_data_dir()
    if not STATION_CACHE_PATH.exists():
        return {"regions": {}}
    return json.loads(STATION_CACHE_PATH.read_text(encoding="utf-8"))


def save_station_cache(payload: Dict[str, Any]) -> None:
    ensure_data_dir()
    STATION_CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": "OpenClaw-Korea-Air-Quality/0.1"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_region_name(region: str) -> str:
    cleaned = " ".join((region or "").strip().split())
    return REGION_ALIASES.get(cleaned, cleaned)


def geocode_region(region: str) -> Dict[str, Any]:
    normalized = normalize_region_name(region)
    cache = load_station_cache()
    cached = cache.setdefault("regions", {}).get(normalized)
    if cached:
        return cached
    if normalized in STATIC_REGIONS:
        resolved = {"query": region, **STATIC_REGIONS[normalized]}
        cache.setdefault("regions", {})[normalized] = resolved
        save_station_cache(cache)
        return resolved
    payload = fetch_json(
        OPENMETEO_GEOCODING_URL,
        {
            "name": normalized,
            "count": 5,
            "language": "ko",
            "format": "json",
            "countryCode": "KR",
        },
    )
    results = payload.get("results") or []
    if not results and " " in normalized:
        payload = fetch_json(
            OPENMETEO_GEOCODING_URL,
            {
                "name": normalized.split()[-1],
                "count": 5,
                "language": "ko",
                "format": "json",
                "countryCode": "KR",
            },
        )
        results = payload.get("results") or []
    if not results:
        raise ValueError(f"대한민국 지역 후보를 찾지 못했습니다: {region}")
    best = results[0]
    resolved = {
        "query": region,
        "resolved_name": best.get("name") or normalized,
        "admin1": best.get("admin1"),
        "admin2": best.get("admin2"),
        "admin3": best.get("admin3"),
        "country": best.get("country"),
        "latitude": best["latitude"],
        "longitude": best["longitude"],
        "timezone": best.get("timezone", "Asia/Seoul"),
    }
    cache.setdefault("regions", {})[normalized] = resolved
    save_station_cache(cache)
    return resolved


def nearest_known_region(lat: float, lon: float) -> Dict[str, Any]:
    cache = load_station_cache().get("regions", {})
    if not cache:
        raise ValueError("좌표 기반 추정에 사용할 지역 캐시가 없습니다. 먼저 지역명 조회를 한 번 수행하세요.")
    best_item = None
    best_distance = float("inf")
    for item in cache.values():
        distance = math.hypot(float(item["latitude"]) - lat, float(item["longitude"]) - lon)
        if distance < best_distance:
            best_distance = distance
            best_item = item
    if not best_item:
        raise ValueError("좌표 기반 지역 추정에 실패했습니다.")
    return dict(best_item, matched_by="cached-nearest")


def fetch_air_quality(lat: float, lon: float, timezone: str = "Asia/Seoul") -> Dict[str, Any]:
    payload = fetch_json(
        OPENMETEO_AIR_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi",
            "forecast_days": 1,
        },
    )
    current = payload.get("current") or {}
    return {
        "time": current.get("time"),
        "pm10": current.get("pm10"),
        "pm2_5": current.get("pm2_5"),
        "ozone": current.get("ozone"),
        "us_aqi": current.get("us_aqi"),
        "european_aqi": current.get("european_aqi"),
    }


def grade_pm25(value: float | None) -> str:
    if value is None:
        return "정보 없음"
    if value <= 15:
        return "좋음"
    if value <= 35:
        return "보통"
    if value <= 75:
        return "나쁨"
    return "매우나쁨"


def grade_pm10(value: float | None) -> str:
    if value is None:
        return "정보 없음"
    if value <= 30:
        return "좋음"
    if value <= 80:
        return "보통"
    if value <= 150:
        return "나쁨"
    return "매우나쁨"


def overall_grade(pm10: float | None, pm25: float | None) -> str:
    order = ["좋음", "보통", "나쁨", "매우나쁨", "정보 없음"]
    grades = [grade_pm10(pm10), grade_pm25(pm25)]
    ranked = [g for g in grades if g in order[:-1]]
    return max(ranked, key=lambda g: order.index(g)) if ranked else "정보 없음"


def action_tip(overall: str) -> str:
    if overall == "좋음":
        return "야외 활동과 환기를 무난하게 해도 괜찮은 편이에요."
    if overall == "보통":
        return "일반 활동은 무난하지만 민감군은 장시간 야외활동을 조금 조심하는 게 좋아요."
    if overall == "나쁨":
        return "장시간 야외활동은 줄이고, 외출 시 마스크를 챙기는 편이 좋아요."
    if overall == "매우나쁨":
        return "가급적 실외활동을 줄이고, 환기는 짧게 하며 마스크 착용을 권장해요."
    return "추가 데이터 확인이 필요해요."


def resolve_region(args: argparse.Namespace) -> Tuple[Dict[str, Any], str]:
    if args.lat is not None and args.lon is not None:
        region = nearest_known_region(args.lat, args.lon)
        return region, "location"
    if args.region:
        return geocode_region(args.region), "query"
    if getattr(args, "user", None):
        prefs = load_preferences()
        default_region = prefs.get("users", {}).get(args.user, {}).get("default_region")
        if default_region:
            return geocode_region(default_region), "saved-default"
    raise ValueError("지역을 확인할 수 없습니다. 지역명을 입력하거나 저장된 기본 지역을 사용하세요.")


def build_summary(region: Dict[str, Any], air: Dict[str, Any], source: str) -> Dict[str, Any]:
    pm10 = air.get("pm10")
    pm25 = air.get("pm2_5")
    ozone = air.get("ozone")
    overall = overall_grade(pm10, pm25)
    return {
        "resolved_region": region.get("resolved_name"),
        "admin1": region.get("admin1"),
        "admin2": region.get("admin2"),
        "latitude": region.get("latitude"),
        "longitude": region.get("longitude"),
        "resolved_by": source,
        "measured_at": air.get("time"),
        "pm10": {"value": pm10, "grade": grade_pm10(pm10)},
        "pm2_5": {"value": pm25, "grade": grade_pm25(pm25)},
        "ozone": {"value": ozone},
        "overall_grade": overall,
        "action_tip": action_tip(overall),
    }


def render_text(summary: Dict[str, Any]) -> str:
    region_line = summary["resolved_region"]
    if summary.get("admin1") and summary["admin1"] != summary["resolved_region"]:
        region_line = f"{summary['admin1']} {summary['resolved_region']}"
    lines = [
        f"{region_line} 기준 대기질이야.",
        f"- 측정 시각: {summary.get('measured_at') or '정보 없음'}",
        f"- 초미세먼지(PM2.5): {summary['pm2_5']['value']} μg/m³ · {summary['pm2_5']['grade']}",
        f"- 미세먼지(PM10): {summary['pm10']['value']} μg/m³ · {summary['pm10']['grade']}",
        f"- 오존: {summary['ozone']['value']}",
        f"- 종합 판단: {summary['overall_grade']}",
        f"- 한줄 팁: {summary['action_tip']}",
        f"- 지역 결정 방식: {summary['resolved_by']}",
    ]
    return "\n".join(lines)


def cmd_now(args: argparse.Namespace) -> int:
    region, source = resolve_region(args)
    air = fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"))
    summary = build_summary(region, air, source)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))
    return 0


def cmd_resolve_region(args: argparse.Namespace) -> int:
    region = geocode_region(args.region)
    print(json.dumps(region, ensure_ascii=False, indent=2) if args.json else f"{args.region} -> {region['resolved_name']} ({region['latitude']}, {region['longitude']})")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    results = []
    for region_name in args.regions:
        region = geocode_region(region_name)
        air = fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"))
        results.append(build_summary(region, air, "query"))
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    lines = []
    for item in results:
        lines.append(f"- {item['resolved_region']}: PM2.5 {item['pm2_5']['value']}({item['pm2_5']['grade']}), PM10 {item['pm10']['value']}({item['pm10']['grade']}), 종합 {item['overall_grade']}")
    print("\n".join(lines))
    return 0


def cmd_save_default(args: argparse.Namespace) -> int:
    prefs = load_preferences()
    users = prefs.setdefault("users", {})
    users[args.user] = {"default_region": args.region}
    save_preferences(prefs)
    print(f"기본 지역 저장 완료: {args.user} -> {args.region}")
    return 0


def cmd_show_default(args: argparse.Namespace) -> int:
    prefs = load_preferences()
    region = prefs.get("users", {}).get(args.user, {}).get("default_region")
    if args.json:
        print(json.dumps({"user": args.user, "default_region": region}, ensure_ascii=False, indent=2))
    else:
        print(region or "저장된 기본 지역이 없습니다.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Korea air quality CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("now", help="현재 대기질 조회")
    p.add_argument("region", nargs="?")
    p.add_argument("--user", help="저장된 기본 지역을 불러올 사용자 키")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_now)

    p = sub.add_parser("resolve-region", help="지역명 해석/좌표 확인")
    p.add_argument("region")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_resolve_region)

    p = sub.add_parser("compare", help="여러 지역 대기질 비교")
    p.add_argument("regions", nargs="+")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("save-default", help="사용자 기본 지역 저장")
    p.add_argument("user")
    p.add_argument("region")
    p.set_defaults(func=cmd_save_default)

    p = sub.add_parser("show-default", help="사용자 기본 지역 조회")
    p.add_argument("user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show_default)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
