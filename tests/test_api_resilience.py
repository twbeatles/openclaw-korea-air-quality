"""API 변경 내성 + 보완 수정 회귀 테스트 (네트워크 격리, FakeHttp 주입)."""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

import pytest

from airquality import constants, geo, paths, store
from airquality import http as http_module
from airquality.cli import commands, parser
from airquality.providers import airkorea, factory
from airquality.services import regions, summary


class FakeHttp:
    """URL 기준으로 미리 준비한 응답을 돌려주는 가짜 전송 계층."""

    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def fetch_text(self, url, params=None, raw_query=None):
        self.calls.append({"url": url, "params": params, "raw_query": raw_query})
        return self.handler(url, params, raw_query)

    def fetch_json(self, url, params=None, raw_query=None):
        return json.loads(self.fetch_text(url, params, raw_query))


def sido_payload(rows):
    return json.dumps({"response": {"header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"}, "body": {"items": rows}}}, ensure_ascii=False)


def test_normalize_items_variants():
    row = {"stationName": "중구", "pm25Value": "20"}
    assert airkorea.normalize_items([row]) == [row]
    assert airkorea.normalize_items(row) == [row]
    assert airkorea.normalize_items({"item": [row]}) == [row]
    assert airkorea.normalize_items({"item": row}) == [row]
    assert airkorea.normalize_items([]) == []
    assert airkorea.normalize_items(None) == []
    assert airkorea.normalize_items("junk") == []
    assert airkorea.normalize_items([row, "junk", None]) == [row]


def test_sido_name_new_admin_names():
    assert airkorea.sido_name({"admin1": "강원특별자치도"}) == "강원"
    assert airkorea.sido_name({"admin1": "전북특별자치도"}) == "전북"
    assert airkorea.sido_name({"admin1": "세종특별자치시"}) == "세종"
    assert airkorea.sido_name({"admin1": "제주특별자치도"}) == "제주"


def test_key_attempts_new_version_first():
    attempts = airkorea._key_attempts("KEY%2B")
    assert [ver for _, _, ver in attempts].count("1.3") == 2
    assert attempts[0][2] == constants.AIRKOREA_VERSIONS[0]
    assert len(attempts) == 2 * len(constants.AIRKOREA_VERSIONS)


def test_fetch_raw_uses_central_page_size():
    row = {"stationName": "중구", "pm25Value": "20", "pm10Value": "40"}
    fake = FakeHttp(lambda url, params, raw: sido_payload([row]))
    items, err = airkorea.fetch_raw("http://x/sido", "서울", "KEY", False, ver="1.3", http_client=fake)
    assert err is None and items == [row]
    assert fake.calls[0]["params"]["numOfRows"] == constants.AIRKOREA_NUM_ROWS

    fake_raw = FakeHttp(lambda url, params, raw: sido_payload([row]))
    items, err = airkorea.fetch_raw("http://x/sido", "서울", "KEY", True, ver="1.3", http_client=fake_raw)
    assert err is None and items == [row]
    assert f"numOfRows={constants.AIRKOREA_NUM_ROWS}" in fake_raw.calls[0]["raw_query"]


def test_fetch_raw_absorbs_nested_single_item():
    row = {"stationName": "중구", "pm25Value": "20"}
    nested = json.dumps({"response": {"header": {"resultCode": "00", "resultMsg": "OK"}, "body": {"items": {"item": [row]}}}}, ensure_ascii=False)
    fake = FakeHttp(lambda url, params, raw: nested)
    items, err = airkorea.fetch_raw("http://x/sido", "서울", "KEY", False, http_client=fake)
    assert err is None and items == [row]


def _station_daily_payload():
    rows = [
        {"stationName": "성동구", "dataTime": "2026-01-01 09:00", "pm25Value": "-", "pm10Value": "-", "o3Value": "-"},
        {"stationName": "성동구", "dataTime": "2026-01-01 10:00", "pm25Value": "18", "pm10Value": "35", "o3Value": "0.040", "pm25Grade1h": "2", "pm10Grade1h": "2", "khaiValue": "60", "khaiGrade": "2"},
    ]
    return sido_payload(rows)


def test_station_direct_fallback_when_sido_empty():
    def handler(url, params, raw):
        if "getMsrstnAcctoRltmMesureDnsty" in url:
            return _station_daily_payload()
        return json.dumps({"response": {"header": {"resultCode": "00", "resultMsg": "OK"}, "body": {"items": []}}})

    fake = FakeHttp(handler)
    out = airkorea.fetch_airkorea_air_quality(
        37.56, 127.03, region={"admin1": "서울특별시", "admin2": "성동구", "resolved_name": "성동구"},
        http_client=fake, load_cfg=lambda: {"airkorea_api_key": "K"},
    )
    assert out["station_name"] == "성동구"
    assert out["pm2_5"] == 18.0 and out["pm2_5_grade"] == "보통"


def test_all_missing_triggers_station_refine():
    sido_row = {"stationName": "성동구", "dataTime": "2026-01-01 10:00", "pm25Value": "-", "pm10Value": "-", "o3Value": "-", "khaiValue": "-"}

    def handler(url, params, raw):
        if "getMsrstnAcctoRltmMesureDnsty" in url:
            return _station_daily_payload()
        return sido_payload([sido_row])

    fake = FakeHttp(handler)
    out = airkorea.fetch_airkorea_air_quality(
        37.56, 127.03, region={"admin1": "서울특별시", "admin2": "성동구", "resolved_name": "성동구"},
        http_client=fake, load_cfg=lambda: {"airkorea_api_key": "K"},
    )
    assert out["pm2_5"] == 18.0
    assert any("getMsrstnAcctoRltmMesureDnsty" in call["url"] for call in fake.calls)


def test_airkorea_surfaces_extra_pollutants_and_flags():
    row = {"stationName": "중구", "dataTime": "2026-01-01 10:00", "pm25Value": "10", "pm10Value": "20",
           "so2Value": "0.004", "so2Grade": "1", "coValue": "0.5", "no2Value": "0.02",
           "pm25Grade1h": "1", "pm10Grade1h": "1", "mangName": "도시대기", "pm10Flag": "정상"}
    fake = FakeHttp(lambda url, params, raw: sido_payload([row]))
    out = airkorea.fetch_airkorea_air_quality(
        37.56, 126.97, region={"admin1": "서울특별시", "admin2": "중구", "resolved_name": "중구"},
        http_client=fake, load_cfg=lambda: {"airkorea_api_key": "K"},
    )
    assert out["pollutants"]["so2"] == {"value": 0.004, "grade": "좋음"}
    assert out["data_flags"] == {"pm10Flag": "정상"}
    assert out["mang_name"] == "도시대기"


def test_nearest_merges_static_with_sparse_cache():
    pangyo = {"query": "판교", "resolved_name": "판교동", "admin1": "경기도", "latitude": 37.3943, "longitude": 127.1112}
    resolver = geo.RegionResolver(load_cache=lambda: {"regions": {"판교": pangyo}}, save_cache=lambda payload: None)
    near_seoul = resolver.nearest(37.5641, 126.9979)
    assert near_seoul["resolved_name"] != "판교동"
    assert near_seoul["admin1"] == "서울특별시"


def test_resolve_region_pins_exact_coordinates():
    static_like = {"resolved_name": "중구", "admin1": "서울특별시", "admin2": "중구", "latitude": 37.5641, "longitude": 126.9979}
    args = argparse.Namespace(location_text=None, lat=35.1152, lon=129.0422, region=None, user=None)
    region, source = regions.resolve_region(args, nearest=lambda lat, lon: dict(static_like))
    assert source == "location"
    assert (region["latitude"], region["longitude"]) == (35.1152, 129.0422)
    assert region["resolved_name"] == "중구"

    args = argparse.Namespace(location_text="37.1, 127.1", lat=None, lon=None, region=None, user=None)
    region, source = regions.resolve_region(args, nearest=lambda lat, lon: dict(static_like))
    assert source == "shared-location"
    assert (region["latitude"], region["longitude"]) == (37.1, 127.1)


def test_alert_add_uses_max_plus_one(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "ALERT_RULES_PATH", tmp_path / "alert-rules.json")
    store.save_alert_rules({"rules": [{"id": 1, "user": "u", "region": "서울", "metric": "pm2_5", "threshold": "나쁨"}, {"id": 3, "user": "u", "region": "수원", "metric": "pm10", "threshold": "보통"}]})
    args = argparse.Namespace(user="u", region="부산", metric="ozone", threshold="나쁨", json=True)
    assert commands.cmd_alert_add(args) == 0
    ids = [rule["id"] for rule in store.load_alert_rules()["rules"]]
    assert ids == [1, 3, 4]


def test_corrupt_store_file_backs_up_and_recovers(tmp_path, monkeypatch):
    target = tmp_path / "user-preferences.json"
    target.write_text("{깨진 json", encoding="utf-8")
    monkeypatch.setattr(paths, "PREFERENCES_PATH", target)
    assert store.load_preferences() == {"users": {}}
    assert target.with_name(target.name + ".bak").exists()


def test_provider_registry_rejects_unknown():
    with pytest.raises(ValueError, match="지원하지 않는 provider"):
        factory.resolve_provider("nasa")
    with pytest.raises(ValueError, match="지원"):
        factory.resolve_provider(None, load_cfg=lambda: {"provider": "nasa"})
    assert factory.resolve_provider("airkorea") == "airkorea"
    assert set(factory.PROVIDER_NAMES) == {"openmeteo", "airkorea"}


def test_parser_provider_choices_follow_registry():
    built = parser.build_parser()
    for name in ("now", "setup-provider"):
        action = next(act for act in built._subparsers._group_actions[0].choices[name]._optionals._actions if "--provider" in act.option_strings or act.dest == "provider")
        assert set(action.choices) == set(factory.PROVIDER_NAMES)


def test_factory_passes_http_client():
    seen = {}

    class CapHttp:
        def fetch_json(self, url, params=None, raw_query=None):
            seen.update(params or {})
            return {"current": {"time": "t", "pm10": 1.0, "pm2_5": 1.0, "ozone": 10.0, "us_aqi": 10, "european_aqi": 5}}

    out = factory.fetch_air_quality(37.5, 127.0, provider="openmeteo", http_client=CapHttp())
    assert out["provider"] == "openmeteo"
    assert seen["current"] == constants.OPENMETEO_AIR_CURRENT_FIELDS


def test_summary_passes_through_aqi_pollutants_and_quality():
    region = {"resolved_name": "중구", "admin1": "서울특별시", "admin2": "중구", "latitude": 37.56, "longitude": 126.99}
    air = {"time": "2026-01-01 10:00", "pm10": 40.0, "pm2_5": 20.0, "ozone": 58.0, "provider": "openmeteo",
           "station_name": None, "us_aqi": 72, "european_aqi": 19,
           "pollutants": {"carbon_monoxide": 194.0}, "data_flags": {"pm10Flag": "정상"}, "mang_name": "도시대기"}
    summ = summary.build_summary(region, air, "query")
    assert summ["aqi"] == {"us_aqi": 72, "european_aqi": 19}
    assert summ["pollutants"] == {"carbon_monoxide": 194.0}
    assert summ["data_quality"] == {"flags": {"pm10Flag": "정상"}}
    assert summ["network"] == "도시대기"
    text = summary.render_text(summ)
    assert "대기질지수(AQI): US 72, EU 19" in text
    assert "일산화탄소" not in text and "CO 194.0" in text


def test_http_retries_transient_and_not_auth_errors(monkeypatch):
    calls = {"count": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b'{"ok": true}'

    def flaky_429(request, timeout=None):
        calls["count"] += 1
        if calls["count"] < 2:
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", flaky_429)
    client = http_module.HttpClient(max_retries=3, sleep=lambda seconds: None)
    assert client.fetch_text("http://x") == '{"ok": true}'
    assert calls["count"] == 2

    def always_401(request, timeout=None):
        calls["count"] += 1
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", always_401)
    before = calls["count"]
    with pytest.raises(urllib.error.HTTPError):
        http_module.HttpClient(max_retries=3, sleep=lambda seconds: None).fetch_text("http://x")
    assert calls["count"] == before + 1
