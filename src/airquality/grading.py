"""등급 판정 순수 함수군 (IO 없음, SRP)."""
from __future__ import annotations

from typing import Any, Dict

from .constants import GRADE_ORDER, WEATHER_CODES


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
