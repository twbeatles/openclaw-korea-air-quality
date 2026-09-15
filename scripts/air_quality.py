from __future__ import annotations

import argparse
import json
import math
import os
import re
import urllib.parse
import urllib.request
from urllib.error import HTTPError
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PREFERENCES_PATH = DATA_DIR / "user-preferences.json"
STATION_CACHE_PATH = DATA_DIR / "station-cache.json"
ALERT_RULES_PATH = DATA_DIR / "alert-rules.json"
ALERT_STATE_PATH = DATA_DIR / "alert-state.json"
CONFIG_PATH = DATA_DIR / "config.json"

OPENMETEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPENMETEO_AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPENMETEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

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
    "경기": "경기도",
    "강원": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    # 서울 주요 자치구 및 핫스팟
    "성동구": "서울특별시 성동구",
    "강남구": "서울특별시 강남구",
    "동대문구": "서울특별시 동대문구",
    "송파구": "서울특별시 송파구",
    "서초구": "서울특별시 서초구",
    "마포구": "서울특별시 마포구",
    "영등포구": "서울특별시 영등포구",
    "종로구": "서울특별시 종로구",
    "중구": "서울특별시 중구",
    "용산구": "서울특별시 용산구",
    "노원구": "서울특별시 노원구",
    "관악구": "서울특별시 관악구",
    "강서구": "서울특별시 강서구",
    "양천구": "서울특별시 양천구",
    "광진구": "서울특별시 광진구",
    "강북구": "서울특별시 강북구",
    "성북구": "서울특별시 성북구",
    "중랑구": "서울특별시 중랑구",
    "서대문구": "서울특별시 서대문구",
    "은평구": "서울특별시 은평구",
    "동작구": "서울특별시 동작구",
    "구로구": "서울특별시 구로구",
    "금천구": "서울특별시 금천구",
    "도봉구": "서울특별시 도봉구",
    "강동구": "서울특별시 강동구",
    "답십리": "서울특별시 동대문구 답십리동",
    "답십리동": "서울특별시 동대문구 답십리동",
    "장안동": "서울특별시 동대문구 장안동",
    "전농동": "서울특별시 동대문구 전농동",
    "청량리": "서울특별시 동대문구 청량리동",
    "왕십리": "서울특별시 성동구 왕십리동",
    "왕십리역": "서울특별시 성동구 행당동",
    "행당동": "서울특별시 성동구 행당동",
    "잠실": "서울특별시 송파구 잠실동",
    "여의도": "서울특별시 영등포구 여의도동",
    "홍대": "서울특별시 마포구 서교동",
    "신촌": "서울특별시 서대문구 신촌동",
    # 경기 주요 생활권
    "영통": "수원시 영통구",
    "수원 영통": "수원시 영통구",
    "분당": "성남시 분당구",
    "판교": "성남시 분당구 판교동",
    "일산": "고양시 일산동구",
    "동탄": "화성시 동탄동",
    "수지": "용인시 수지구",
    "기흥": "용인시 기흥구",
}

STATIC_REGIONS = {
    # 17개 광역시도 대표 거점
    "서울특별시": {"resolved_name": "서울특별시", "admin1": "서울특별시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 37.5665, "longitude": 126.9780, "timezone": "Asia/Seoul"},
    "부산광역시": {"resolved_name": "부산광역시", "admin1": "부산광역시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 35.1796, "longitude": 129.0756, "timezone": "Asia/Seoul"},
    "대구광역시": {"resolved_name": "대구광역시", "admin1": "대구광역시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 35.8714, "longitude": 128.6014, "timezone": "Asia/Seoul"},
    "인천광역시": {"resolved_name": "인천광역시", "admin1": "인천광역시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 37.4563, "longitude": 126.7052, "timezone": "Asia/Seoul"},
    "광주광역시": {"resolved_name": "광주광역시", "admin1": "광주광역시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 35.1595, "longitude": 126.8526, "timezone": "Asia/Seoul"},
    "대전광역시": {"resolved_name": "대전광역시", "admin1": "대전광역시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 36.3504, "longitude": 127.3845, "timezone": "Asia/Seoul"},
    "울산광역시": {"resolved_name": "울산광역시", "admin1": "울산광역시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 35.5384, "longitude": 129.3114, "timezone": "Asia/Seoul"},
    "세종특별자치시": {"resolved_name": "세종특별자치시", "admin1": "세종특별자치시", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 36.4800, "longitude": 127.2890, "timezone": "Asia/Seoul"},
    "경기도": {"resolved_name": "경기도", "admin1": "경기도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 37.2750, "longitude": 127.0094, "timezone": "Asia/Seoul"},
    "강원특별자치도": {"resolved_name": "강원특별자치도", "admin1": "강원특별자치도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 37.8854, "longitude": 127.7298, "timezone": "Asia/Seoul"},
    "충청북도": {"resolved_name": "충청북도", "admin1": "충청북도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 36.6357, "longitude": 127.4917, "timezone": "Asia/Seoul"},
    "충청남도": {"resolved_name": "충청남도", "admin1": "충청남도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 36.6588, "longitude": 126.6728, "timezone": "Asia/Seoul"},
    "전북특별자치도": {"resolved_name": "전북특별자치도", "admin1": "전북특별자치도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 35.8242, "longitude": 127.1480, "timezone": "Asia/Seoul"},
    "전라남도": {"resolved_name": "전라남도", "admin1": "전라남도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 34.8161, "longitude": 126.4629, "timezone": "Asia/Seoul"},
    "경상북도": {"resolved_name": "경상북도", "admin1": "경상북도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 36.5760, "longitude": 128.5056, "timezone": "Asia/Seoul"},
    "경상남도": {"resolved_name": "경상남도", "admin1": "경상남도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 35.2383, "longitude": 128.6925, "timezone": "Asia/Seoul"},
    "제주특별자치도": {"resolved_name": "제주특별자치도", "admin1": "제주특별자치도", "admin2": None, "admin3": None, "country": "대한민국", "latitude": 33.4996, "longitude": 126.5312, "timezone": "Asia/Seoul"},
    # 주요 생활권/자치구
    "서울특별시 성동구": {"resolved_name": "성동구", "admin1": "서울특별시", "admin2": "성동구", "admin3": None, "country": "대한민국", "latitude": 37.5636, "longitude": 127.0365, "timezone": "Asia/Seoul"},
    "서울특별시 강남구": {"resolved_name": "강남구", "admin1": "서울특별시", "admin2": "강남구", "admin3": None, "country": "대한민국", "latitude": 37.5172, "longitude": 127.0473, "timezone": "Asia/Seoul"},
    "서울특별시 동대문구": {"resolved_name": "동대문구", "admin1": "서울특별시", "admin2": "동대문구", "admin3": None, "country": "대한민국", "latitude": 37.5744, "longitude": 127.0396, "timezone": "Asia/Seoul"},
    "서울특별시 동대문구 답십리동": {"resolved_name": "답십리동", "admin1": "서울특별시", "admin2": "동대문구", "admin3": "답십리동", "country": "대한민국", "latitude": 37.5666, "longitude": 127.0569, "timezone": "Asia/Seoul"},
    "서울특별시 동대문구 장안동": {"resolved_name": "장안동", "admin1": "서울특별시", "admin2": "동대문구", "admin3": "장안동", "country": "대한민국", "latitude": 37.5707, "longitude": 127.0682, "timezone": "Asia/Seoul"},
    "서울특별시 동대문구 전농동": {"resolved_name": "전농동", "admin1": "서울특별시", "admin2": "동대문구", "admin3": "전농동", "country": "대한민국", "latitude": 37.5787, "longitude": 127.0471, "timezone": "Asia/Seoul"},
    "서울특별시 동대문구 청량리동": {"resolved_name": "청량리동", "admin1": "서울특별시", "admin2": "동대문구", "admin3": "청량리동", "country": "대한민국", "latitude": 37.5863, "longitude": 127.0446, "timezone": "Asia/Seoul"},
    "서울특별시 성동구 왕십리동": {"resolved_name": "왕십리동", "admin1": "서울특별시", "admin2": "성동구", "admin3": "왕십리동", "country": "대한민국", "latitude": 37.5618, "longitude": 127.0372, "timezone": "Asia/Seoul"},
    "서울특별시 성동구 행당동": {"resolved_name": "행당동", "admin1": "서울특별시", "admin2": "성동구", "admin3": "행당동", "country": "대한민국", "latitude": 37.5587, "longitude": 127.0351, "timezone": "Asia/Seoul"},
    "수원시 영통구": {"resolved_name": "영통구", "admin1": "경기도", "admin2": "수원시 영통구", "admin3": None, "country": "대한민국", "latitude": 37.2595, "longitude": 127.0464, "timezone": "Asia/Seoul"},
    "성남시 분당구": {"resolved_name": "분당구", "admin1": "경기도", "admin2": "성남시 분당구", "admin3": None, "country": "대한민국", "latitude": 37.3826, "longitude": 127.1187, "timezone": "Asia/Seoul"},
    "성남시 분당구 판교동": {"resolved_name": "판교동", "admin1": "경기도", "admin2": "성남시 분당구", "admin3": "판교동", "country": "대한민국", "latitude": 37.3943, "longitude": 127.1112, "timezone": "Asia/Seoul"},
    "서울특별시 송파구 잠실동": {"resolved_name": "잠실동", "admin1": "서울특별시", "admin2": "송파구", "admin3": "잠실동", "country": "대한민국", "latitude": 37.5110, "longitude": 127.0811, "timezone": "Asia/Seoul"},
    "서울특별시 마포구 서교동": {"resolved_name": "서교동", "admin1": "서울특별시", "admin2": "마포구", "admin3": "서교동", "country": "대한민국", "latitude": 37.5563, "longitude": 126.9229, "timezone": "Asia/Seoul"},
    "서울특별시 영등포구 여의도동": {"resolved_name": "여의도동", "admin1": "서울특별시", "admin2": "영등포구", "admin3": "여의도동", "country": "대한민국", "latitude": 37.5216, "longitude": 126.9242, "timezone": "Asia/Seoul"},
    "서울특별시 서대문구 신촌동": {"resolved_name": "신촌동", "admin1": "서울특별시", "admin2": "서대문구", "admin3": "신촌동", "country": "대한민국", "latitude": 37.5598, "longitude": 126.9423, "timezone": "Asia/Seoul"},
    "서울특별시 성동구 성수동": {"resolved_name": "성수동", "admin1": "서울특별시", "admin2": "성동구", "admin3": "성수동", "country": "대한민국", "latitude": 37.5445, "longitude": 127.0560, "timezone": "Asia/Seoul"},
}

DISTRICT_FALLBACKS = {
    "답십리동": "서울특별시 동대문구 답십리동",
    "장안동": "서울특별시 동대문구 장안동",
    "전농동": "서울특별시 동대문구 전농동",
    "청량리동": "서울특별시 동대문구 청량리동",
    "왕십리동": "서울특별시 성동구 왕십리동",
    "행당동": "서울특별시 성동구 행당동",
    "동대문구": "서울특별시 동대문구",
}

GRADE_ORDER = {"좋음": 0, "보통": 1, "나쁨": 2, "매우나쁨": 3, "정보 없음": -1}
WEATHER_CODES = {0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림", 45: "안개", 48: "서리 안개", 51: "이슬비", 53: "이슬비", 55: "강한 이슬비", 61: "비", 63: "비", 65: "강한 비", 71: "눈", 73: "눈", 75: "강한 눈", 80: "소나기", 81: "소나기", 82: "강한 소나기", 95: "뇌우"}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    ensure_data_dir()
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_data_dir()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_preferences() -> Dict[str, Any]:
    return _read_json(PREFERENCES_PATH, {"users": {}})


def save_preferences(payload: Dict[str, Any]) -> None:
    _write_json(PREFERENCES_PATH, payload)


def load_station_cache() -> Dict[str, Any]:
    return _read_json(STATION_CACHE_PATH, {"regions": {}})


def save_station_cache(payload: Dict[str, Any]) -> None:
    _write_json(STATION_CACHE_PATH, payload)


def load_alert_rules() -> Dict[str, Any]:
    return _read_json(ALERT_RULES_PATH, {"rules": []})


def save_alert_rules(payload: Dict[str, Any]) -> None:
    _write_json(ALERT_RULES_PATH, payload)


def load_alert_state() -> Dict[str, Any]:
    return _read_json(ALERT_STATE_PATH, {"lastHits": {}})


def save_alert_state(payload: Dict[str, Any]) -> None:
    _write_json(ALERT_STATE_PATH, payload)


def load_config() -> Dict[str, Any]:
    return _read_json(CONFIG_PATH, {"provider": "openmeteo", "airkorea_api_key": None})


def save_config(payload: Dict[str, Any]) -> None:
    _write_json(CONFIG_PATH, payload)


def fetch_text(url: str, params: Dict[str, Any] | None = None, raw_query: str | None = None) -> str:
    if raw_query:
        full_url = f"{url}?{raw_query}" if "?" not in url else f"{url}&{raw_query}"
    elif params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        full_url = f"{url}?{query}"
    else:
        full_url = url
    req = urllib.request.Request(full_url, headers={"User-Agent": "OpenClaw-Korea-Air-Quality/0.6"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8")


def fetch_json(url: str, params: Dict[str, Any] | None = None, raw_query: str | None = None) -> Dict[str, Any]:
    return json.loads(fetch_text(url, params, raw_query=raw_query))


def parse_xml_items(xml_text: str) -> List[Dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []
    items: List[Dict[str, Any]] = []
    for item in root.findall('.//item'):
        row: Dict[str, Any] = {}
        for child in item:
            row[child.tag] = (child.text or '').strip()
        items.append(row)
    return items


def parse_datago_error(text: str) -> str | None:
    """공공데이터포털 에러 XML 또는 JSON 응답에서 상세 오류 메시지 추출"""
    error_meanings = {
        "01": "APPLICATION_ERROR (어플리케이션 에러)",
        "10": "INVALID_REQUEST_PARAMETER_ERROR (요청 파라미터가 유효하지 않음)",
        "12": "NO_OPENAPI_SERVICE_ERROR (해당 OpenAPI 서비스가 없거나 폐기됨)",
        "20": "SERVICE_ACCESS_DENIED_ERROR (활용신청 승인 대기 중이거나 서비스 접근 거부)",
        "22": "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR (일일 트래픽 한도 초과)",
        "30": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR (등록되지 않은 서비스키)",
        "31": "DEADLINE_HAS_EXPIRED_ERROR (활용 기간 만료)",
        "32": "UNREGISTERED_IP_ERROR (등록되지 않은 IP)",
    }

    # 1. JSON 에러 확인
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            header = ((data.get("response") or {}).get("header")) or data.get("header") or {}
            result_code = str(header.get("resultCode") or "")
            result_msg = str(header.get("resultMsg") or "")
            if result_code and result_code not in ("00", "0"):
                meaning = error_meanings.get(result_code, result_msg)
                return f"공공데이터포털 오류 [코드 {result_code}: {meaning}]"
    except Exception:
        pass

    # 2. XML 에러 확인
    try:
        root = ET.fromstring(text)
        # cmmMsgHeader 구조
        cmm_header = root.find(".//cmmMsgHeader")
        if cmm_header is not None:
            err_msg = (cmm_header.findtext("errMsg") or "").strip()
            return_auth_msg = (cmm_header.findtext("returnAuthMsg") or "").strip()
            return_reason_code = (cmm_header.findtext("returnReasonCode") or "").strip()
            meaning = error_meanings.get(return_reason_code, return_auth_msg or err_msg)
            return f"공공데이터포털 인증 오류 [코드 {return_reason_code}: {meaning}]"

        # response/header 구조
        header = root.find(".//header")
        if header is not None:
            result_code = (header.findtext("resultCode") or "").strip()
            result_msg = (header.findtext("resultMsg") or "").strip()
            if result_code and result_code not in ("00", "0"):
                meaning = error_meanings.get(result_code, result_msg)
                return f"공공데이터포털 오류 [코드 {result_code}: {meaning}]"
    except Exception:
        pass

    return None


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, "", "-", "null"):
            return None
        return float(value)
    except Exception:
        return None


def grade_code_to_str(code: Any) -> str | None:
    return {"1": "좋음", "2": "보통", "3": "나쁨", "4": "매우나쁨"}.get(str(code or "").strip())


def normalize_region_name(region: str) -> str:
    cleaned = " ".join((region or "").strip().split())
    return REGION_ALIASES.get(cleaned, cleaned)


def _normalize_lat_lon(val1: float, val2: float) -> Tuple[float, float]:
    """한국 좌표 특성(위도 30~45, 경도 120~135)을 활용해 위도/경도 순서가 바뀐 경우 자동 보정"""
    if (120.0 <= val1 <= 135.0) and (30.0 <= val2 <= 45.0):
        return val2, val1
    return val1, val2


def parse_shared_location(raw: str | None) -> Dict[str, Any] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            candidates = [payload, payload.get("location") if isinstance(payload.get("location"), dict) else None, payload.get("message") if isinstance(payload.get("message"), dict) else None]
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                nested = candidate.get("location") if isinstance(candidate.get("location"), dict) else candidate
                lat = nested.get("latitude") or nested.get("lat")
                lon = nested.get("longitude") or nested.get("lon") or nested.get("lng")
                if lat is not None and lon is not None:
                    norm_lat, norm_lon = _normalize_lat_lon(float(lat), float(lon))
                    return {"lat": norm_lat, "lon": norm_lon, "label": nested.get("label") or payload.get("label")}
    except Exception:
        pass
    # 지도 쿼리 파라미터 (q=lat,lon 또는 ?c=zoom,lon,lat 등)
    map_c_match = re.search(r"[?&]c=\d+,\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if map_c_match:
        norm_lat, norm_lon = _normalize_lat_lon(float(map_c_match.group(1)), float(map_c_match.group(2)))
        return {"lat": norm_lat, "lon": norm_lon, "label": None}
    match_q = re.search(r"q=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)", text)
    if match_q:
        norm_lat, norm_lon = _normalize_lat_lon(float(match_q.group(1)), float(match_q.group(2)))
        return {"lat": norm_lat, "lon": norm_lon, "label": None}
    match = re.search(r"(-?\d{1,3}\.\d+)\s*[, ]\s*(-?\d{1,3}\.\d+)", text)
    if match:
        norm_lat, norm_lon = _normalize_lat_lon(float(match.group(1)), float(match.group(2)))
        return {"lat": norm_lat, "lon": norm_lon, "label": None}
    return None


def resolve_provider(explicit_provider: str | None) -> str:
    if explicit_provider:
        return explicit_provider
    return load_config().get("provider", "openmeteo")


def _airkorea_sido_name(region: Dict[str, Any] | None) -> str:
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


def _fetch_airkorea_raw(url: str, sido_name: str, key_to_try: str, is_raw_key: bool, ver: str = "1.3") -> Tuple[List[Dict[str, Any]], str | None]:
    """공공데이터포털 단일 호출 시도 (JSON -> XML 파싱 및 에러 감지)"""
    base_params = {
        "returnType": "json",
        "numOfRows": 100,
        "pageNo": 1,
        "sidoName": sido_name,
        "ver": ver,
    }

    raw_query = None
    params = None
    if is_raw_key:
        encoded_sido = urllib.parse.quote(sido_name)
        raw_query = f"serviceKey={key_to_try}&returnType=json&numOfRows=100&pageNo=1&sidoName={encoded_sido}&ver={ver}"
    else:
        params = {"serviceKey": key_to_try, **base_params}

    try:
        response_text = fetch_text(url, params=params, raw_query=raw_query)
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
        payload = json.loads(response_text)
        items = (((payload or {}).get("response") or {}).get("body") or {}).get("items") or []
        if items:
            return items, None
    except Exception:
        pass

    # 2. XML 응답 파싱 시도 (returnType=xml 또는 포털 강제 XML 응답)
    items = parse_xml_items(response_text)
    if items:
        return items, None

    return [], None


def fetch_airkorea_air_quality(lat: float, lon: float, timezone: str = "Asia/Seoul", region: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = load_config()
    api_key = os.getenv("AIRKOREA_API_KEY") or cfg.get("airkorea_api_key")
    if not api_key:
        raise ValueError("AIRKOREA_API_KEY 또는 config.json의 airkorea_api_key 가 없어 airkorea provider를 사용할 수 없습니다. 'setup-provider openmeteo' 또는 API 키를 설정하세요.")

    sido_name = _airkorea_sido_name(region)
    url = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"

    raw_key = str(api_key).strip()
    unquoted_key = urllib.parse.unquote(raw_key)

    # 공공데이터포털 특성상 Decoding/Encoding 키의 URL 인코딩 처리 차이로 인한 인증 에러 방지 (fallback retry)
    key_attempts = [
        (unquoted_key, False, "1.3"),  # unquoted 후 표준 urlencode
        (raw_key, True, "1.3"),         # 전달받은 원문 키를 쿼리에 직접 결합
        (unquoted_key, False, "1.0"),  # ver=1.0 하위 호환 폴백
        (raw_key, True, "1.0"),
    ]

    items: List[Dict[str, Any]] = []
    last_error: str | None = None

    for key_try, is_raw, ver_try in key_attempts:
        items, err = _fetch_airkorea_raw(url, sido_name, key_try, is_raw, ver=ver_try)
        if items:
            break
        if err:
            last_error = err

    if not items:
        if last_error:
            raise ValueError(
                f"AirKorea API 호출 실패: {last_error}\n"
                "참고: 공공데이터포털(data.go.kr)에서 '한국환경공단_에어코리아_대기오염정보(ArpltnInforInqireSvc)' "
                "활용신청 승인 상태 및 발급된 인증키(Encoding/Decoding)를 확인하세요."
            )
        raise ValueError(f"AirKorea 응답에서 측정 항목을 찾지 못했습니다: sido={sido_name}")

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

    pm10_val = _to_float(chosen.get("pm10Value"))
    pm25_val = _to_float(chosen.get("pm25Value"))
    o3_val = _to_float(chosen.get("o3Value"))
    khai_val = _to_float(chosen.get("khaiValue"))

    # 실시간 1시간 등급 우선, 없을 시 24시간 등급, 없을 시 수치 기반 계산
    pm25_grade = grade_code_to_str(chosen.get("pm25Grade1h") or chosen.get("pm25Grade")) or grade_pm25(pm25_val)
    pm10_grade = grade_code_to_str(chosen.get("pm10Grade1h") or chosen.get("pm10Grade")) or grade_pm10(pm10_val)
    o3_grade = grade_code_to_str(chosen.get("o3Grade")) or grade_ozone(o3_val, provider="airkorea")
    khai_grade = grade_code_to_str(chosen.get("khaiGrade")) or grade_khai(khai_val)

    return {
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
        "sido_name": sido_name,
    }


def geocode_region(region: str) -> Dict[str, Any]:
    normalized = normalize_region_name(region)
    # 1. 정적 정의 지역 우선 확인 (신뢰 데이터)
    if normalized in STATIC_REGIONS:
        return {"query": region, **STATIC_REGIONS[normalized]}
    fallback = DISTRICT_FALLBACKS.get(normalized)
    if fallback and fallback in STATIC_REGIONS:
        return {"query": region, **STATIC_REGIONS[fallback]}

    # 2. 로컬 캐시 확인
    cache = load_station_cache()
    cached = cache.setdefault("regions", {}).get(normalized)
    if cached:
        return cached

    # 3. 외부 지오코딩 API 호출
    payload = fetch_json(OPENMETEO_GEOCODING_URL, {"name": normalized, "count": 5, "language": "ko", "format": "json", "countryCode": "KR"})
    results = payload.get("results") or []
    if not results and " " in normalized:
        payload = fetch_json(OPENMETEO_GEOCODING_URL, {"name": normalized.split()[-1], "count": 5, "language": "ko", "format": "json", "countryCode": "KR"})
        results = payload.get("results") or []
    if not results and normalized.endswith(("동", "읍", "면", "구")):
        trimmed = normalized[:-1]
        payload = fetch_json(OPENMETEO_GEOCODING_URL, {"name": trimmed, "count": 5, "language": "ko", "format": "json", "countryCode": "KR"})
        results = payload.get("results") or []
    if not results:
        raise ValueError(f"대한민국 지역 후보를 찾지 못했습니다: {region}")
    best = results[0]
    resolved = {"query": region, "resolved_name": best.get("name") or normalized, "admin1": best.get("admin1"), "admin2": best.get("admin2"), "admin3": best.get("admin3"), "country": best.get("country"), "latitude": best["latitude"], "longitude": best["longitude"], "timezone": best.get("timezone", "Asia/Seoul")}
    cache.setdefault("regions", {})[normalized] = resolved
    save_station_cache(cache)
    return resolved


def nearest_known_region(lat: float, lon: float) -> Dict[str, Any]:
    cache = load_station_cache().get("regions", {})
    if not cache:
        cache = {key: {"query": key, **value} for key, value in STATIC_REGIONS.items()}
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


def fetch_openmeteo_air_quality(lat: float, lon: float, timezone: str = "Asia/Seoul") -> Dict[str, Any]:
    payload = fetch_json(OPENMETEO_AIR_URL, {"latitude": lat, "longitude": lon, "timezone": timezone, "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi", "forecast_days": 1})
    current = payload.get("current") or {}
    return {"time": current.get("time"), "pm10": current.get("pm10"), "pm2_5": current.get("pm2_5"), "ozone": current.get("ozone"), "us_aqi": current.get("us_aqi"), "european_aqi": current.get("european_aqi"), "provider": "openmeteo"}


def fetch_air_quality(lat: float, lon: float, timezone: str = "Asia/Seoul", provider: str | None = None, region: Dict[str, Any] | None = None) -> Dict[str, Any]:
    resolved_provider = resolve_provider(provider)
    if resolved_provider == "airkorea":
        return fetch_airkorea_air_quality(lat, lon, timezone, region=region)
    return fetch_openmeteo_air_quality(lat, lon, timezone)


def fetch_weather(lat: float, lon: float, timezone: str = "Asia/Seoul") -> Dict[str, Any]:
    payload = fetch_json(OPENMETEO_WEATHER_URL, {"latitude": lat, "longitude": lon, "timezone": timezone, "current": "temperature_2m,apparent_temperature,weather_code", "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code", "forecast_days": 1})
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    return {"current_temp": current.get("temperature_2m"), "apparent_temp": current.get("apparent_temperature"), "current_weather_code": current.get("weather_code"), "today_max": (daily.get("temperature_2m_max") or [None])[0], "today_min": (daily.get("temperature_2m_min") or [None])[0], "precipitation_probability_max": (daily.get("precipitation_probability_max") or [None])[0], "today_weather_code": (daily.get("weather_code") or [None])[0]}


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


def grade_ozone(value: float | None, provider: str = "airkorea") -> str:
    if value is None:
        return "정보 없음"
    # 에어코리아는 ppm 단위
    if provider == "airkorea":
        if value <= 0.030:
            return "좋음"
        if value <= 0.090:
            return "보통"
        if value <= 0.150:
            return "나쁨"
        return "매우나쁨"
    # Open-Meteo는 μg/m³ 단위 (대략 1 ppm ≈ 2000 μg/m³)
    if value <= 60:
        return "좋음"
    if value <= 180:
        return "보통"
    if value <= 300:
        return "나쁨"
    return "매우나쁨"


def grade_khai(value: float | None) -> str:
    if value is None:
        return "정보 없음"
    if value <= 50:
        return "좋음"
    if value <= 100:
        return "보통"
    if value <= 250:
        return "나쁨"
    return "매우나쁨"


def overall_grade(pm10: float | None, pm25: float | None, ozone: float | None = None, khai_grade: str | None = None, provider: str = "openmeteo") -> str:
    grades = [grade_pm10(pm10), grade_pm25(pm25)]
    if ozone is not None:
        grades.append(grade_ozone(ozone, provider=provider))
    if khai_grade and khai_grade in GRADE_ORDER:
        grades.append(khai_grade)
    ranked = [g for g in grades if g in ("좋음", "보통", "나쁨", "매우나쁨")]
    return max(ranked, key=lambda g: GRADE_ORDER[g]) if ranked else "정보 없음"


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


def weather_text(code: int | None) -> str:
    if code is None:
        return "날씨 정보 없음"
    return WEATHER_CODES.get(code, "날씨 정보 없음")


def resolve_region(args: argparse.Namespace) -> Tuple[Dict[str, Any], str]:
    shared = parse_shared_location(getattr(args, "location_text", None))
    if shared:
        region = nearest_known_region(float(shared["lat"]), float(shared["lon"]))
        return region, "shared-location"
    if getattr(args, "lat", None) is not None and getattr(args, "lon", None) is not None:
        region = nearest_known_region(args.lat, args.lon)
        return region, "location"
    if getattr(args, "region", None):
        return geocode_region(args.region), "query"
    if getattr(args, "user", None):
        prefs = load_preferences()
        user_info = prefs.get("users", {}).get(args.user, {})
        if user_info.get("default_location"):
            lat = float(user_info["default_location"]["lat"])
            lon = float(user_info["default_location"]["lon"])
            region = nearest_known_region(lat, lon)
            return region, "saved-location"
        if user_info.get("default_region"):
            return geocode_region(user_info["default_region"]), "saved-default"
    raise ValueError("지역을 확인할 수 없습니다. 지역명을 입력하거나 저장된 기본 지역/좌표를 사용하세요.")


def build_summary(region: Dict[str, Any], air: Dict[str, Any], source: str) -> Dict[str, Any]:
    pm10 = air.get("pm10")
    pm25 = air.get("pm2_5")
    ozone = air.get("ozone")
    provider = air.get("provider", "unknown")
    station_name = air.get("station_name")

    pm10_grade = air.get("pm10_grade") or grade_pm10(pm10)
    pm25_grade = air.get("pm2_5_grade") or grade_pm25(pm25)
    ozone_unit = air.get("ozone_unit") or ("ppm" if provider == "airkorea" else "μg/m³")
    ozone_grade = air.get("ozone_grade") or grade_ozone(ozone, provider=provider)
    khai_val = air.get("khai_value")
    khai_grade = air.get("khai_grade") or (grade_khai(khai_val) if khai_val is not None else None)

    overall = overall_grade(pm10, pm25, ozone=ozone, khai_grade=khai_grade, provider=provider)

    summary: Dict[str, Any] = {
        "resolved_region": region.get("resolved_name"),
        "admin1": region.get("admin1"),
        "admin2": region.get("admin2"),
        "station_name": station_name,
        "latitude": region.get("latitude"),
        "longitude": region.get("longitude"),
        "resolved_by": source,
        "measured_at": air.get("time"),
        "provider": provider,
        "pm10": {"value": pm10, "grade": pm10_grade},
        "pm2_5": {"value": pm25, "grade": pm25_grade},
        "ozone": {"value": ozone, "unit": ozone_unit, "grade": ozone_grade},
        "overall_grade": overall,
        "action_tip": action_tip(overall),
    }
    if khai_val is not None or khai_grade is not None:
        summary["khai"] = {"value": khai_val, "grade": khai_grade}
    return summary


def render_text(summary: Dict[str, Any]) -> str:
    region_line = summary["resolved_region"]
    if summary.get("admin1") and summary["admin1"] != summary["resolved_region"]:
        region_line = f"{summary['admin1']} {summary['resolved_region']}"
    if summary.get("station_name"):
        region_line = f"{region_line} ({summary['station_name']} 측정소)"

    lines = [
        f"{region_line} 기준 대기질이야.",
        f"- 측정 시각: {summary.get('measured_at') or '정보 없음'}",
        f"- 초미세먼지(PM2.5): {summary['pm2_5']['value']} μg/m³ · {summary['pm2_5']['grade']}",
        f"- 미세먼지(PM10): {summary['pm10']['value']} μg/m³ · {summary['pm10']['grade']}",
    ]
    oz = summary.get("ozone") or {}
    if oz.get("value") is not None:
        lines.append(f"- 오존: {oz.get('value')} {oz.get('unit', '')} · {oz.get('grade', '')}")

    khai = summary.get("khai")
    if khai and (khai.get("value") is not None or khai.get("grade")):
        lines.append(f"- 통합대기(KHAI): {khai.get('value')} · {khai.get('grade')}")

    lines.extend([
        f"- 종합 판단: {summary['overall_grade']}",
        f"- 한줄 팁: {summary['action_tip']}",
        f"- 지역 결정 방식: {summary['resolved_by']}",
        f"- 공급자: {summary['provider']}",
    ])
    return "\n".join(lines)


def build_morning_brief(summary: Dict[str, Any], weather: Dict[str, Any]) -> Dict[str, Any]:
    station_suffix = f" ({summary['station_name']} 측정소)" if summary.get("station_name") else ""
    region_label = f"{summary.get('admin1') or ''} {summary['resolved_region']}".strip() + station_suffix
    return {
        "region": region_label,
        "measured_at": summary.get("measured_at"),
        "weather": {
            "current_temp": weather.get("current_temp"),
            "apparent_temp": weather.get("apparent_temp"),
            "today_max": weather.get("today_max"),
            "today_min": weather.get("today_min"),
            "summary": weather_text(weather.get("today_weather_code")),
            "precipitation_probability_max": weather.get("precipitation_probability_max"),
        },
        "air": summary,
        "brief": (
            f"오늘 {summary['resolved_region']}은 {weather_text(weather.get('today_weather_code'))}, "
            f"기온 {weather.get('today_min')}~{weather.get('today_max')}°C 정도고 초미세먼지는 {summary['pm2_5']['grade']}, "
            f"미세먼지는 {summary['pm10']['grade']} 수준이야. {summary['action_tip']}"
        ),
    }


def grade_value_for_metric(summary: Dict[str, Any], metric: str) -> str:
    if metric == "pm2_5":
        return summary["pm2_5"]["grade"]
    if metric == "pm10":
        return summary["pm10"]["grade"]
    if metric == "ozone":
        return (summary.get("ozone") or {}).get("grade", "정보 없음")
    if metric == "khai":
        return (summary.get("khai") or {}).get("grade", "정보 없음")
    return summary["overall_grade"]


def alert_matches(summary: Dict[str, Any], metric: str, threshold: str) -> bool:
    current_grade = grade_value_for_metric(summary, metric)
    return GRADE_ORDER.get(current_grade, -1) >= GRADE_ORDER.get(threshold, 99)


def build_hit_signature(rule: Dict[str, Any], summary: Dict[str, Any]) -> str:
    metric = rule["metric"]
    grade = grade_value_for_metric(summary, metric)
    measured_at = summary.get("measured_at") or "unknown"
    return f"{rule['region']}|{metric}|{grade}|{measured_at}"


def build_cron_plan(kind: str, user: str, region: str | None, metric: str | None, threshold: str | None, hour: int | None, minute: int | None) -> Dict[str, Any]:
    skill_dir = str(BASE_DIR)
    if kind == "morning-brief":
        schedule_expr = f"{minute or 0} {hour or 7} * * *"
        command = f"python scripts/air_quality.py morning-brief {region or ''} --user {user}".strip()
        message = f"{skill_dir} 에서 `{command}` 를 실행해. 결과를 한국어로 그대로 전달해."
        name = f"대기질 아침 브리핑 ({user})"
    else:
        schedule_expr = f"{minute or 0} * * * *"
        command = f"python scripts/air_quality.py alert-check --user {user} --json"
        message = f"{skill_dir} 에서 `{command}` 를 실행해. 신규 hit만 한국어로 알려줘. 신규 hit가 없으면 정확히 NO_REPLY 만 출력해."
        name = f"대기질 알림 점검 ({user})"
    return {
        "name": name,
        "schedule": {"kind": "cron", "expr": schedule_expr, "tz": "Asia/Seoul"},
        "payload": {"kind": "agentTurn", "message": message, "timeoutSeconds": 120},
        "sessionTarget": "current",
        "delivery": {"mode": "announce"},
        "notes": {"kind": kind, "region": region, "metric": metric, "threshold": threshold},
    }


def cmd_now(args: argparse.Namespace) -> int:
    region, source = resolve_region(args)
    air = fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
    summary = build_summary(region, air, source)
    print(json.dumps(summary, ensure_ascii=False, indent=2) if args.json else render_text(summary))
    return 0


def cmd_morning_brief(args: argparse.Namespace) -> int:
    region, source = resolve_region(args)
    air = fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
    summary = build_summary(region, air, source)
    weather = fetch_weather(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"))
    brief = build_morning_brief(summary, weather)
    if args.json:
        print(json.dumps(brief, ensure_ascii=False, indent=2))
    else:
        print(f"{brief['region']} 아침 브리핑")
        print(f"- 날씨: {brief['weather']['summary']} / {brief['weather']['today_min']}~{brief['weather']['today_max']}°C")
        print(f"- 강수 확률: {brief['weather']['precipitation_probability_max']}%")
        print(f"- 초미세먼지: {summary['pm2_5']['value']} μg/m³ · {summary['pm2_5']['grade']}")
        print(f"- 미세먼지: {summary['pm10']['value']} μg/m³ · {summary['pm10']['grade']}")
        print(f"- 종합 판단: {summary['overall_grade']}")
        print(f"- 한줄 요약: {brief['brief']}")
    return 0


def cmd_alert_add(args: argparse.Namespace) -> int:
    rules_payload = load_alert_rules()
    rules = rules_payload.setdefault("rules", [])
    rule = {"id": len(rules) + 1, "user": args.user, "region": args.region, "metric": args.metric, "threshold": args.threshold, "created_at": datetime.now().isoformat(timespec="seconds")}
    rules.append(rule)
    save_alert_rules(rules_payload)
    print(json.dumps(rule, ensure_ascii=False, indent=2) if args.json else f"알림 규칙 저장 완료: {args.user} / {args.region} / {args.metric} / {args.threshold} 이상")
    return 0


def cmd_alert_list(args: argparse.Namespace) -> int:
    rules = load_alert_rules().get("rules", [])
    if args.user:
        rules = [rule for rule in rules if rule.get("user") == args.user]
    if args.json:
        print(json.dumps(rules, ensure_ascii=False, indent=2))
        return 0
    if not rules:
        print("등록된 알림 규칙이 없습니다.")
        return 0
    for rule in rules:
        print(f"- #{rule['id']} {rule['user']} / {rule['region']} / {rule['metric']} / {rule['threshold']} 이상")
    return 0


def cmd_alert_check(args: argparse.Namespace) -> int:
    rules = load_alert_rules().get("rules", [])
    state = load_alert_state()
    last_hits = state.setdefault("lastHits", {})
    if args.user:
        rules = [rule for rule in rules if rule.get("user") == args.user]
    hits = []
    for rule in rules:
        region = geocode_region(rule["region"])
        air = fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
        summary = build_summary(region, air, "alert-check")
        if not alert_matches(summary, rule["metric"], rule["threshold"]):
            continue
        signature = build_hit_signature(rule, summary)
        last_signature = last_hits.get(str(rule["id"]))
        if not args.emit_all and signature == last_signature:
            continue
        last_hits[str(rule["id"])] = signature
        hits.append({"rule": rule, "summary": summary, "current_grade": grade_value_for_metric(summary, rule["metric"]), "signature": signature})
    save_alert_state(state)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0
    if getattr(args, "announce_text", False):
        if not hits:
            print("NO_REPLY")
            return 0
        metric_labels = {"pm2_5": "초미세먼지", "pm10": "미세먼지", "ozone": "오존", "khai": "통합대기(KHAI)", "overall": "종합 대기질"}
        lines = []
        for hit in hits:
            summary = hit["summary"]
            rule = hit["rule"]
            m_name = metric_labels.get(rule["metric"], rule["metric"])
            measured_at = summary.get("measured_at") or "측정 시각 없음"
            station_info = f" ({summary['station_name']} 측정소)" if summary.get("station_name") else ""
            lines.append(
                f"{rule['region']}{station_info} {m_name} 알림: 현재 등급 {hit['current_grade']}(기준: {rule['threshold']} 이상), "
                f"초미세먼지 {summary['pm2_5']['value']}㎍/㎥ / 미세먼지 {summary['pm10']['value']}㎍/㎥, 측정 시각 {measured_at}."
            )
        print("\n".join(lines))
        return 0
    if not hits:
        print("현재 조건을 만족하는 신규 알림 항목이 없습니다.")
        return 0
    for hit in hits:
        print(f"- {hit['rule']['region']} / {hit['rule']['metric']} / 현재 {hit['current_grade']} / 기준 {hit['rule']['threshold']} 이상")
        print(f"  초미세먼지 {hit['summary']['pm2_5']['value']}({hit['summary']['pm2_5']['grade']}), 미세먼지 {hit['summary']['pm10']['value']}({hit['summary']['pm10']['grade']})")
    return 0


def cmd_alert_remove(args: argparse.Namespace) -> int:
    rules_payload = load_alert_rules()
    rules = rules_payload.get("rules", [])
    before_count = len(rules)

    if getattr(args, "all", False):
        if args.user:
            rules_payload["rules"] = [r for r in rules if r.get("user") != args.user]
        else:
            rules_payload["rules"] = []
    elif getattr(args, "id", None) is not None:
        target_id = int(args.id)
        if args.user:
            rules_payload["rules"] = [r for r in rules if not (r.get("id") == target_id and r.get("user") == args.user)]
        else:
            rules_payload["rules"] = [r for r in rules if r.get("id") != target_id]
    else:
        raise ValueError("--id <rule_id> 또는 --all 옵션을 지정하세요.")

    removed_count = before_count - len(rules_payload["rules"])
    save_alert_rules(rules_payload)
    msg = f"알림 규칙 삭제 완료 ({removed_count}건 삭제됨)"
    print(json.dumps({"removed_count": removed_count, "remaining_count": len(rules_payload["rules"])}, ensure_ascii=False, indent=2) if args.json else msg)
    return 0


def cmd_cron_plan(args: argparse.Namespace) -> int:
    plan = build_cron_plan(args.kind, args.user, args.region, args.metric, args.threshold, args.hour, args.minute)
    print(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else f"권장 cron expr: {plan['schedule']['expr']}\njob name: {plan['name']}")
    return 0


def cmd_save_default(args: argparse.Namespace) -> int:
    prefs = load_preferences()
    users = prefs.setdefault("users", {})
    info = users.setdefault(args.user, {})
    info["default_region"] = args.region
    save_preferences(prefs)
    print(f"기본 지역 저장 완료: {args.user} -> {args.region}")
    return 0


def cmd_clear_default(args: argparse.Namespace) -> int:
    prefs = load_preferences()
    users = prefs.get("users", {})
    if args.user in users:
        users.pop(args.user, None)
        save_preferences(prefs)
        msg = f"기본 지역 및 위치 삭제 완료: {args.user}"
    else:
        msg = f"저장된 기본 지역/위치 설정이 없습니다: {args.user}"
    print(json.dumps({"user": args.user, "cleared": True}, ensure_ascii=False, indent=2) if args.json else msg)
    return 0


def cmd_save_location(args: argparse.Namespace) -> int:
    shared = parse_shared_location(getattr(args, "location_text", None))
    lat = args.lat
    lon = args.lon
    label = args.label
    if shared:
        lat = shared["lat"]
        lon = shared["lon"]
        label = label or shared.get("label")
    if lat is None or lon is None:
        raise ValueError("위치 좌표를 확인할 수 없습니다. lat/lon 또는 --location-text 를 넣어 주세요.")
    prefs = load_preferences()
    users = prefs.setdefault("users", {})
    info = users.setdefault(args.user, {})
    info["default_location"] = {"lat": lat, "lon": lon, "label": label}
    save_preferences(prefs)
    print(f"기본 위치 저장 완료: {args.user} -> ({lat}, {lon})" + (f" / {label}" if label else ""))
    return 0


def cmd_show_default(args: argparse.Namespace) -> int:
    prefs = load_preferences()
    info = prefs.get("users", {}).get(args.user, {})
    payload = {"user": args.user, "default_region": info.get("default_region"), "default_location": info.get("default_location")}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else (json.dumps(payload, ensure_ascii=False) if info else "저장된 기본 설정이 없습니다."))
    return 0


def cmd_setup_provider(args: argparse.Namespace) -> int:
    cfg = load_config()
    cfg["provider"] = args.provider
    if args.airkorea_api_key is not None:
        cfg["airkorea_api_key"] = args.airkorea_api_key
    save_config(cfg)
    print(json.dumps(cfg, ensure_ascii=False, indent=2) if args.json else f"기본 provider 저장 완료: {args.provider}")
    return 0


def cmd_show_config(args: argparse.Namespace) -> int:
    cfg = load_config()
    redacted = dict(cfg)
    if redacted.get("airkorea_api_key"):
        redacted["airkorea_api_key"] = "***configured***"
    print(json.dumps(redacted, ensure_ascii=False, indent=2) if args.json else f"provider={redacted.get('provider')} airkorea_api_key={redacted.get('airkorea_api_key')}")
    return 0


def cmd_resolve_region(args: argparse.Namespace) -> int:
    region = geocode_region(args.region)
    print(json.dumps(region, ensure_ascii=False, indent=2) if args.json else f"{args.region} -> {region['resolved_name']} ({region['latitude']}, {region['longitude']})")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    results = []
    errors = []
    for region_name in args.regions:
        try:
            region = geocode_region(region_name)
            air = fetch_air_quality(float(region["latitude"]), float(region["longitude"]), region.get("timezone", "Asia/Seoul"), provider=args.provider, region=region)
            results.append(build_summary(region, air, "query"))
        except Exception as exc:
            errors.append({"region": region_name, "error": str(exc)})
    if args.json:
        payload: Any = results if not errors else {"results": results, "errors": errors}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    for item in results:
        print(f"- {item['resolved_region']}: PM2.5 {item['pm2_5']['value']}({item['pm2_5']['grade']}), PM10 {item['pm10']['value']}({item['pm10']['grade']}), 종합 {item['overall_grade']}")
    for err in errors:
        print(f"- [조회 실패] {err['region']}: {err['error']}")
    return 0


def add_provider_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", choices=["openmeteo", "airkorea"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Korea air quality CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("now", help="현재 대기질 조회")
    p.add_argument("region", nargs="?")
    p.add_argument("--user")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--location-text", help="메신저 위치공유 JSON, 위경도 문자열, 지도 링크 등")
    p.add_argument("--json", action="store_true")
    add_provider_args(p)
    p.set_defaults(func=cmd_now)

    p = sub.add_parser("morning-brief", help="날씨+대기질 아침 브리핑")
    p.add_argument("region", nargs="?")
    p.add_argument("--user")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--location-text", help="메신저 위치공유 JSON, 위경도 문자열, 지도 링크 등")
    p.add_argument("--json", action="store_true")
    add_provider_args(p)
    p.set_defaults(func=cmd_morning_brief)

    p = sub.add_parser("resolve-region", help="지역명 해석/좌표 확인")
    p.add_argument("region")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_resolve_region)

    p = sub.add_parser("compare", help="여러 지역 대기질 비교")
    p.add_argument("regions", nargs="+")
    p.add_argument("--json", action="store_true")
    add_provider_args(p)
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("save-default", help="사용자 기본 지역 저장")
    p.add_argument("user")
    p.add_argument("region")
    p.set_defaults(func=cmd_save_default)

    p = sub.add_parser("clear-default", help="사용자 기본 지역/위치 삭제")
    p.add_argument("user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_clear_default)

    p = sub.add_parser("save-location", help="사용자 기본 위치 좌표 저장")
    p.add_argument("user")
    p.add_argument("lat", nargs="?", type=float)
    p.add_argument("lon", nargs="?", type=float)
    p.add_argument("--label")
    p.add_argument("--location-text", help="메신저 위치공유 JSON, 위경도 문자열, 지도 링크 등")
    p.set_defaults(func=cmd_save_location)

    p = sub.add_parser("show-default", help="사용자 기본 지역/위치 조회")
    p.add_argument("user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show_default)

    p = sub.add_parser("setup-provider", help="기본 provider 및 국내 API 키 저장")
    p.add_argument("provider", choices=["openmeteo", "airkorea"])
    p.add_argument("--airkorea-api-key")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_setup_provider)

    p = sub.add_parser("show-config", help="provider 설정 조회")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show_config)

    p = sub.add_parser("alert-add", help="대기질 알림 규칙 추가")
    p.add_argument("user")
    p.add_argument("region")
    p.add_argument("metric", choices=["pm2_5", "pm10", "overall", "ozone", "khai"])
    p.add_argument("threshold", choices=["좋음", "보통", "나쁨", "매우나쁨"])
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_alert_add)

    p = sub.add_parser("alert-list", help="알림 규칙 목록")
    p.add_argument("--user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_alert_list)

    p = sub.add_parser("alert-remove", help="대기질 알림 규칙 삭제")
    p.add_argument("--user")
    p.add_argument("--id", type=int, help="삭제할 규칙 ID")
    p.add_argument("--all", action="store_true", help="모든 규칙 삭제")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_alert_remove)

    p = sub.add_parser("alert-check", help="알림 규칙 점검")
    p.add_argument("--user")
    p.add_argument("--json", action="store_true")
    p.add_argument("--emit-all", action="store_true")
    p.add_argument("--announce-text", action="store_true", help="cron/announce friendly plain text output")
    add_provider_args(p)
    p.set_defaults(func=cmd_alert_check)

    p = sub.add_parser("cron-plan", help="OpenClaw cron job 초안 생성")
    p.add_argument("kind", choices=["morning-brief", "alert-check"])
    p.add_argument("user")
    p.add_argument("--region")
    p.add_argument("--metric", choices=["pm2_5", "pm10", "overall", "ozone", "khai"])
    p.add_argument("--threshold", choices=["좋음", "보통", "나쁨", "매우나쁨"])
    p.add_argument("--hour", type=int)
    p.add_argument("--minute", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_cron_plan)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
