"""AirKorea provider: 공공데이터포털 호출 + 4단계 계층형 측정소 매칭 (단일 책임)."""
from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError

from .. import http as http_module
from .. import store as store_module
from ..constants import AIRKOREA_CTPRVN_URL
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
        "numOfRows": 100,
        "pageNo": 1,
        "sidoName": sido,
        "ver": ver,
    }

    raw_query = None
    params = None
    if is_raw_key:
        encoded_sido = urllib.parse.quote(sido)
        raw_query = f"serviceKey={key_to_try}&returnType=json&numOfRows=100&pageNo=1&sidoName={encoded_sido}&ver={ver}"
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
        if items:
            return items, None
    except Exception:
        pass

    # 2. XML 응답 파싱 시도 (returnType=xml 또는 포털 강제 XML 응답)
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


def fetch_airkorea_air_quality(
    lat: float,
    lon: float,
    timezone: str = "Asia/Seoul",
    region: Dict[str, Any] | None = None,
    http_client: http_module.HttpClient | None = None,
    load_cfg=store_module.load_config,
) -> Dict[str, Any]:
    cfg = load_cfg()
    api_key = os.getenv("AIRKOREA_API_KEY") or cfg.get("airkorea_api_key")
    if not api_key:
        raise ValueError("AIRKOREA_API_KEY 또는 config.json의 airkorea_api_key 가 없어 airkorea provider를 사용할 수 없습니다. 'setup-provider openmeteo' 또는 API 키를 설정하세요.")

    sido = sido_name(region)
    url = AIRKOREA_CTPRVN_URL

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
        items, err = fetch_raw(url, sido, key_try, is_raw, ver=ver_try, http_client=http_client)
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
        raise ValueError(f"AirKorea 응답에서 측정 항목을 찾지 못했습니다: sido={sido}")

    chosen = pick_station(items, region)

    pm10_val = to_float(chosen.get("pm10Value"))
    pm25_val = to_float(chosen.get("pm25Value"))
    o3_val = to_float(chosen.get("o3Value"))
    khai_val = to_float(chosen.get("khaiValue"))

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
        "sido_name": sido,
    }
