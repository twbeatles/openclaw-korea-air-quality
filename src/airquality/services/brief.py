"""아침 브리핑 조립 (SRP)."""
from __future__ import annotations

from typing import Any, Dict

from ..grading import weather_text


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
