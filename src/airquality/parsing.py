"""순수 파싱 함수군: XML/에러/좌표/지역명 정규화 (IO 없음, SRP)."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Tuple

from .constants import REGION_ALIASES


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


def to_float(value: Any) -> float | None:
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


def normalize_lat_lon(val1: float, val2: float) -> Tuple[float, float]:
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
                    norm_lat, norm_lon = normalize_lat_lon(float(lat), float(lon))
                    return {"lat": norm_lat, "lon": norm_lon, "label": nested.get("label") or payload.get("label")}
    except Exception:
        pass
    # 지도 쿼리 파라미터 (q=lat,lon 또는 ?c=zoom,lon,lat 등)
    map_c_match = re.search(r"[?&]c=\d+,\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if map_c_match:
        norm_lat, norm_lon = normalize_lat_lon(float(map_c_match.group(1)), float(map_c_match.group(2)))
        return {"lat": norm_lat, "lon": norm_lon, "label": None}
    match_q = re.search(r"q=(-?\d{1,3}\.\d+),(-?\d{1,3}\.\d+)", text)
    if match_q:
        norm_lat, norm_lon = normalize_lat_lon(float(match_q.group(1)), float(match_q.group(2)))
        return {"lat": norm_lat, "lon": norm_lon, "label": None}
    match = re.search(r"(-?\d{1,3}\.\d+)\s*[, ]\s*(-?\d{1,3}\.\d+)", text)
    if match:
        norm_lat, norm_lon = normalize_lat_lon(float(match.group(1)), float(match.group(2)))
        return {"lat": norm_lat, "lon": norm_lon, "label": None}
    return None
