"""리팩토링 동등성 테스트: 단일 파일 시절 동작을 패키지 구조에서 그대로 보장한다.

네트워크를 타지 않는 순수 로직 + 파서 표면 + 저장소 라운드트립만 다룬다.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

from airquality import grading, parsing
from airquality.cli.parser import build_parser
from airquality.providers import airkorea
from airquality.services import alerts, brief, cron, regions, summary

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_grading_boundaries():
    assert grading.grade_pm25(15) == "좋음"
    assert grading.grade_pm25(15.1) == "보통"
    assert grading.grade_pm25(None) == "정보 없음"
    assert grading.grade_pm10(150) == "나쁨"
    assert grading.grade_pm10(151) == "매우나쁨"
    assert grading.grade_ozone(0.030, provider="airkorea") == "좋음"
    assert grading.grade_ozone(0.031, provider="airkorea") == "보통"
    assert grading.grade_khai(100) == "보통"
    assert grading.grade_khai(101) == "나쁨"
    assert grading.overall_grade(None, None) == "정보 없음"
    assert grading.alert_matches(
        {"pm2_5": {"grade": "나쁨"}, "pm10": {"grade": "보통"},
         "ozone": {"grade": "좋음"}, "overall_grade": "나쁨"},
        "pm2_5", "보통",
    )


def test_parsing_shared_location_variants():
    assert parsing.parse_shared_location(None) is None
    assert parsing.parse_shared_location("") is None
    direct = parsing.parse_shared_location("37.5641, 126.9979")
    swapped = parsing.parse_shared_location("126.9979, 37.5641")
    assert direct == swapped == {"lat": 37.5641, "lon": 126.9979, "label": None}
    payload = parsing.parse_shared_location('{"lat": 37.5, "lng": 127.0}')
    assert payload == {"lat": 37.5, "lon": 127.0, "label": None}
    assert parsing.normalize_region_name("홍대") == "서울특별시 마포구 서교동"
    assert parsing.to_float("-") is None
    assert parsing.grade_code_to_str("4") == "매우나쁨"


def test_summary_brief_cron_shapes():
    region = {"resolved_name": "중구", "admin1": "서울특별시", "admin2": "중구",
              "latitude": 37.5641, "longitude": 126.9979}
    air = {"time": "2026-01-01 10:00", "pm10": 40.0, "pm2_5": 20.0, "ozone": 0.05,
           "provider": "airkorea", "station_name": "중구",
           "khai_value": 60.0, "khai_grade": None, "ozone_unit": "ppm"}
    summ = summary.build_summary(region, air, "query")
    assert summ["pm2_5"] == {"value": 20.0, "grade": "보통"}
    assert summ["khai"] == {"value": 60.0, "grade": "보통"}
    assert summ["overall_grade"] == "보통"
    text = summary.render_text(summ)
    assert "중구 (중구 측정소)" in text

    weather = {"current_temp": 10.0, "apparent_temp": 8.0, "today_max": 15.0,
               "today_min": 5.0, "today_weather_code": 2,
               "precipitation_probability_max": 20}
    brief_payload = brief.build_morning_brief(summ, weather)
    assert brief_payload["weather"]["summary"] == "부분적으로 흐림"
    assert "초미세먼지는 보통" in brief_payload["brief"]

    sig = alerts.build_hit_signature({"region": "서울 중구", "metric": "pm2_5"}, summ)
    assert sig == "서울 중구|pm2_5|보통|2026-01-01 10:00"

    plan = cron.build_cron_plan("alert-check", "u1", None, "pm2_5", "나쁨", None, 15)
    assert plan["schedule"]["expr"] == "15 * * * *"
    assert "alert-check --user u1 --json" in plan["payload"]["message"]


def test_airkorea_station_hierarchy():
    items = [
        {"stationName": "중구", "pm25Value": "20", "pm10Value": "40"},
        {"stationName": "명동", "pm25Value": "10", "pm10Value": "20"},
    ]
    region = {"admin1": "서울특별시", "admin2": "중구", "admin3": "명동",
              "resolved_name": "명동"}
    assert airkorea.pick_station(items, region)["stationName"] == "명동"
    assert airkorea.sido_name({"admin1": "서울특별시"}) == "서울"
    assert airkorea.sido_name(None) == "서울"


def test_parser_has_all_subcommands():
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert set(choices) == {
        "now", "morning-brief", "resolve-region", "compare", "save-default",
        "clear-default", "save-location", "show-default", "setup-provider",
        "show-config", "alert-add", "alert-list", "alert-remove",
        "alert-check", "cron-plan",
    }
    for name, sub in choices.items():
        assert sub.get_default("func") is not None, name


def test_resolve_region_priority():
    args = argparse.Namespace(location_text="37.5641, 126.9979", lat=None, lon=None,
                              region=None, user=None)
    region, source = regions.resolve_region(
        args,
        geocode=lambda r: (_ for _ in ()).throw(AssertionError("geocode must not run")),
        nearest=lambda lat, lon: {"resolved_name": "중구"},
    )
    assert source == "shared-location"
    assert region["resolved_name"] == "중구"


def test_store_roundtrip_isolated(tmp_path, monkeypatch):
    from airquality import paths, store

    monkeypatch.setattr(paths, "PREFERENCES_PATH", tmp_path / "user-preferences.json")
    monkeypatch.setattr(paths, "ALERT_RULES_PATH", tmp_path / "alert-rules.json")

    store.save_preferences({"users": {"u1": {"default_region": "서울 중구"}}})
    assert store.load_preferences()["users"]["u1"]["default_region"] == "서울 중구"

    store.save_alert_rules({"rules": [{"id": 1}]})
    assert store.load_alert_rules() == {"rules": [{"id": 1}]}


def test_compat_shim_exposes_original_symbols():
    spec = importlib.util.spec_from_file_location(
        "compat_air_quality", REPO_ROOT / "scripts" / "air_quality.py")
    shim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shim)
    for name in ["main", "build_parser", "geocode_region", "fetch_air_quality",
                 "build_summary", "build_cron_plan", "grade_pm25",
                 "parse_shared_location", "_to_float", "_read_json",
                 "_airkorea_sido_name", "_fetch_airkorea_raw"]:
        assert hasattr(shim, name), name
