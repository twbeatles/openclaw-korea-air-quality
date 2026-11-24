"""AirKorea provider: 공공데이터포털 호출 + 4단계 계층형 측정소 매칭 (단일 책임).

엔드포인트·버전·페이지 크기는 constants의 API 메타에서 가져오며,
상류 명세(data.go.kr 15073861) 변경 시 그곳만 고치면 된다.
시도 단위 조회가 비어 있거나 전 항목 결측이면 측정소 직접 조회
(getMsrstnAcctoRltmMesureDnsty)로 폴백한다.
"""
from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError

from .. import constants as constants_module
from .. import http as http_module
from .. import store as store_module
from ..grading import grade_khai, grade_ozone, grade_pm10, grade_pm25
from ..parsing import grade_code_to_str, parse_datago_error, parse_xml_items, to_float


def sido_name(region: Dict[str, Any] | None) -> str:
    admin1 = (region or {}).get("admin1") or "서울특별시"
    mapping = {
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
        "제주특별자치도": "제주",
        "경기도": "경기",
        "강원특별자치도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전북특별자치도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
    }
    return mapping.get(admin1, admin1.replace("특별시", "").replace("광역시", "").replace("특별자치도", "").replace("특별자치시", "").replace("도", ""))


def normalize_items(raw: Any) -> List[Dict[str, Any]]:
    """포털 응답 변형 흡수: 단일 dict / {"item": [...]} 중첩을 리스트로 통일."""
    if raw is None or raw == "":
        return []
    if isinstance(raw, dict):
        if "item" not in raw:
            return [raw]
        return normalize_items(raw["item"])
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    return []


def _sido_url() -> str:
    base = constants_module.AIRKOREA_BASE_URL.rstrip("/")
    return f"{base}/{constants_module.AIRKOREA_OPERATIONS['sido']}"


def _station_url() -> str:
    base = constants_module.AIRKOREA_BASE_URL.rstrip("/")
    return f"{base}/{constants_module.AIRKOREA_OPERATIONS['station']}"


def _key_attempts(raw_key: str) -> List[Tuple[str, bool, str]]:
    """Decoding/Encoding 키 혼용 + ver 신/구 조합의 폴백 순서."""
    unquoted_key = urllib.parse.unquote(raw_key)
    attempts: List[Tuple[str, bool, str]] = []
    for ver in constants_module.AIRKOREA_VERSIONS:
        attempts.append((unquoted_key, False, ver))
        attempts.append((raw_key, True, ver))
    return attempts


def fetch_raw(
    url: str,
    sido: str,
    key_to_try: str,
    is_raw_key: bool,
    ver: str = "1.3",
    http_client: http_module.HttpClient | None = None,
) -> Tuple[List[Dict[str, Any]], str | None]:
    """공공데이터포털 단일 호출 시도 (JSON -> XML 파싱 및 에러 감지)"""
    client = http_client or http_module.HttpClient()
    base_params = {
        "returnType": "json",
        "numOfRows": constants_module.AIRKOREA_NUM_ROWS,
        "pageNo": constants_module.AIRKOREA_PAGE_NO,
        "sidoName": sido,
        "ver": ver,
    }

    raw_query = None
    params = None
    if is_raw_key:
        encoded_sido = urllib.parse.quote(sido)
        raw_query = f"serviceKey={key_to_try}&returnType=json&numOfRows={base_params['numOfRows']}&pageNo={base_params['pageNo']}&sidoName={encoded_sido}&ver={ver}"
    else:
        params = {"serviceKey": key_to_try, **base_params}

    try:
        response_text = client.fetch_text(url, params=params, raw_query=raw_query)
    except HTTPError as exc:
        if exc.code == 401:
            return [], "HTTP 401 Unauthorized"
        return [], f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:
        return [], str(exc)

    err = parse_datago_error(response_text)
    if err:
        return [], err

    # 1. JSON 응답 파싱 시도
    try:
        import json as _json

        payload = _json.loads(response_text)
        items = (((payload or {}).get("response") or {}).get("body") or {}).get("items") or []
        normalized = normalize_items(items)
        if normalized:
            return normalized, None
    except Exception:
        pass

    # 2. XML 응답 파싱 시도 (returnType=xml 또는 포털 강제 XML 응답)
    items = parse_xml_items(response_text)
    if items:
        return items, None

    return [], None


def fetch_station_raw(
    station_name: str,
    key_to_try: str,
    is_raw_key: bool,
    ver: str = "1.3",
    http_client: http_module.HttpClient | None = None,
) -> Tuple[List[Dict[str, Any]], str | None]:
    """측정소 직접 조회 (stationName + dataTerm=DAILY): 시도 조회 폴백용."""
    client = http_client or http_module.HttpClient()
    base_params = {
        "returnType": "json",
        "numOfRows": constants_module.AIRKOREA_STATION_NUM_ROWS,
        "pageNo": constants_module.AIRKOREA_PAGE_NO,
        "stationName": station_name,
        "dataTerm": constants_module.AIRKOREA_STATION_DATA_TERM,
        "ver": ver,
    }
    raw_query = None
    params = None
    if is_raw_key:
        encoded_station = urllib.parse.quote(station_name)
        raw_query = (
            f"serviceKey={key_to_try}&returnType=json"
            f"&numOfRows={base_params['numOfRows']}&pageNo={base_params['pageNo']}"
            f"&stationName={encoded_station}&dataTerm={base_params['dataTerm']}&ver={ver}"
        )
    else:
        params = {"serviceKey": key_to_try, **base_params}
    try:
        response_text = client.fetch_text(_station_url(), params=params, raw_query=raw_query)
    except HTTPError as exc:
        if exc.code == 401:
            return [], "HTTP 401 Unauthorized"
        return [], f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:
        return [], str(exc)

    err = parse_datago_error(response_text)
    if err:
        return [], err
    try:
        import json as _json

        payload = _json.loads(response_text)
        items = (((payload or {}).get("response") or {}).get("body") or {}).get("items") or []
        normalized = normalize_items(items)
        if normalized:
            return normalized, None
    except Exception:
        pass
    items = parse_xml_items(response_text)
    if items:
        return items, None
    return [], None


def pick_station(items: List[Dict[str, Any]], region: Dict[str, Any] | None) -> Dict[str, Any]:
    # 측정소 다단계 매칭 (Hierarchical Fallback):
    # 1순위: 동/읍/면 단위 이름
    preferred_dong = ((region or {}).get("admin3") or (region or {}).get("resolved_name") or "")
    preferred_dong_clean = preferred_dong.replace("동", "").replace("읍", "").replace("면", "").strip()

    # 2순위: 자치구/시/군 단위 이름 (admin2)
    admin2_name = (region or {}).get("admin2") or ""
    preferred_gu_clean = admin2_name.replace("시", "").replace("군", "").replace("구", "").strip()

    # 3순위: resolved_name 전체
    resolved_clean = ((region or {}).get("resolved_name") or "").replace("동", "").replace("구", "").replace("시", "").strip()

    chosen = None

    # 1순위 검색
    if preferred_dong_clean:
        for item in items:
            station_name = str(item.get("stationName") or "")
            if preferred_dong_clean in station_name:
                chosen = item
                break

    # 2순위 검색 (admin2 구/군 일치)
    if chosen is None and preferred_gu_clean:
        for item in items:
            station_name = str(item.get("stationName") or "")
            if preferred_gu_clean in station_name:
                chosen = item
                break

    # 3순위 검색 (resolved_clean)
    if chosen is None and resolved_clean:
        for item in items:
            station_name = str(item.get("stationName") or "")
            if resolved_clean in station_name:
                chosen = item
                break

    # 4순위 검색: 유효한 pm25 또는 pm10 측정값이 있는 첫 번째 측정소
    if chosen is None:
        for item in items:
            if item.get("pm25Value") not in (None, "", "-") or item.get("pm10Value") not in (None, "", "-"):
                chosen = item
                break

    if chosen is None:
        chosen = items[0]
    return chosen


def _station_candidates(region: Dict[str, Any] | None) -> List[str]:
    """측정소 직접 조회용 후보 이름 (정확 일치 우선)."""
    admin2 = ((region or {}).get("admin2") or "").strip()
    admin3 = ((region or {}).get("admin3") or "").strip()
    resolved = ((region or {}).get("resolved_name") or "").strip()
    candidates: List[str] = []
    for name in (admin3, admin2, resolved):
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def _first_valid(rows: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    for row in rows:
        if row.get("pm25Value") not in (None, "", "-") or row.get("pm10Value") not in (None, "", "-"):
            return row
    return None


def refine_via_station_api(
    region: Dict[str, Any] | None,
    key_attempts: List[Tuple[str, bool, str]],
    http_client: http_module.HttpClient | None = None,
) -> Dict[str, Any] | None:
    """시도 조회 실패/전 항목 결측 시 측정소 직접 조회로 복구 시도."""
    for candidate in _station_candidates(region):
        for key_try, is_raw, ver_try in key_attempts:
            rows, _err = fetch_station_raw(candidate, key_try, is_raw, ver=ver_try, http_client=http_client)
            valid = _first_valid(rows) if rows else None
            if valid is not None:
                return valid
    return None


class AirKoreaProvider:
    name = "airkorea"

    def __init__(
        self,
        http_client: http_module.HttpClient | None = None,
        load_cfg=store_module.load_config,
    ) -> None:
        self._http = http_client or http_module.HttpClient()
        self._load_cfg = load_cfg

    def fetch(self, lat: float, lon: float, timezone: str = "Asia/Seoul", region: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return fetch_airkorea_air_quality(lat, lon, timezone, region=region, http_client=self._http, load_cfg=self._load_cfg)


def _resolve_api_key(load_cfg) -> str | None:
    cfg = load_cfg()
    return os.getenv("AIRKOREA_API_KEY") or cfg.get("airkorea_api_key")


def fetch_airkorea_air_quality(
    lat: float,
    lon: float,
    timezone: str = "Asia/Seoul",
    region: Dict[str, Any] | None = None,
    http_client: http_module.HttpClient | None = None,
    load_cfg=store_module.load_config,
) -> Dict[str, Any]:
    api_key = _resolve_api_key(load_cfg)
    if not api_key:
        raise ValueError("AIRKOREA_API_KEY 또는 config.json의 airkorea_api_key 가 없어 airkorea provider를 사용할 수 없습니다. 'setup-provider openmeteo' 또는 API 키를 설정하세요.")

    sido = sido_name(region)
    url = _sido_url()

    raw_key = str(api_key).strip()
    key_attempts = _key_attempts(raw_key)

    items: List[Dict[str, Any]] = []
    last_error: str | None = None

    for key_try, is_raw, ver_try in key_attempts:
        items, err = fetch_raw(url, sido, key_try, is_raw, ver=ver_try, http_client=http_client)
        if items:
            break
        if err:
            last_error = err

    chosen: Dict[str, Any] | None = None
    if items:
        chosen = pick_station(items, region)

    if chosen is None or all(
        chosen.get(k) in (None, "", "-") for k in ("pm25Value", "pm10Value", "o3Value", "khaiValue")
    ):
        refined = refine_via_station_api(region, key_attempts, http_client=http_client)
        if refined is not None:
            chosen = refined

    if chosen is None:
        if last_error:
            raise ValueError(
                f"AirKorea API 호출 실패: {last_error}\n"
                "참고: 공공데이터포털(data.go.kr)에서 '한국환경공단_에어코리아_대기오염정보(ArpltnInforInqireSvc)' "
                "활용신청 승인 상태 및 발급된 인증키(Encoding/Decoding)를 확인하세요."
            )
        raise ValueError(f"AirKorea 응답에서 측정 항목을 찾지 못했습니다: sido={sido}")

    pm10_val = to_float(chosen.get("pm10Value"))
    pm25_val = to_float(chosen.get("pm25Value"))
    o3_val = to_float(chosen.get("o3Value"))
    khai_val = to_float(chosen.get("khaiValue"))

    # 실시간 1시간 등급 우선, 없을 시 24시간 등급, 없을 시 수치 기반 계산
    pm25_grade = grade_code_to_str(chosen.get("pm25Grade1h") or chosen.get("pm25Grade")) or grade_pm25(pm25_val)
    pm10_grade = grade_code_to_str(chosen.get("pm10Grade1h") or chosen.get("pm10Grade")) or grade_pm10(pm10_val)
    o3_grade = grade_code_to_str(chosen.get("o3Grade")) or grade_ozone(o3_val, provider="airkorea")
    khai_grade = grade_code_to_str(chosen.get("khaiGrade")) or grade_khai(khai_val)

    pollutants: Dict[str, Any] = {}
    for key, grade_key in (
        ("so2Value", "so2Grade"),
        ("coValue", "coGrade"),
        ("no2Value", "no2Grade"),
    ):
        val = to_float(chosen.get(key))
        grade = grade_code_to_str(chosen.get(grade_key))
        if val is not None or grade is not None:
            pollutants[key.replace("Value", "")] = {"value": val, "grade": grade}

    data_flags = {
        key: chosen.get(key)
        for key in ("so2Flag", "coFlag", "o3Flag", "no2Flag", "pm10Flag", "pm25Flag")
        if chosen.get(key) not in (None, "")
    }

    result: Dict[str, Any] = {
        "time": chosen.get("dataTime") or chosen.get("dataTm"),
        "pm10": pm10_val,
        "pm10_grade": pm10_grade,
        "pm2_5": pm25_val,
        "pm2_5_grade": pm25_grade,
        "ozone": o3_val,
        "ozone_unit": "ppm",
        "ozone_grade": o3_grade,
        "khai_value": khai_val,
        "khai_grade": khai_grade,
        "us_aqi": None,
        "european_aqi": None,
        "provider": "airkorea",
        "station_name": chosen.get("stationName"),
        "sido_name": sido,
    }
    if pollutants:
        result["pollutants"] = pollutants
    if data_flags:
        result["data_flags"] = data_flags
    if chosen.get("mangName"):
        result["mang_name"] = chosen.get("mangName")
    if to_float(chosen.get("pm10Value24")) is not None:
        result["pm10_24h"] = to_float(chosen.get("pm10Value24"))
    if to_float(chosen.get("pm25Value24")) is not None:
        result["pm25_24h"] = to_float(chosen.get("pm25Value24"))
    return result
