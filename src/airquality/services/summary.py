"""요약 서비스: provider 원시값 -> 통일 summary dict + 텍스트 렌더 (SRP)."""
from __future__ import annotations

from typing import Any, Dict

from ..grading import (
    action_tip,
    grade_khai,
    grade_ozone,
    grade_pm10,
    grade_pm25,
    overall_grade,
)


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
