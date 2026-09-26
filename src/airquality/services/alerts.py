"""알림 도메인: hit 서명 생성 (SRP)."""
from __future__ import annotations

from typing import Any, Dict

from ..grading import grade_value_for_metric


def build_hit_signature(rule: Dict[str, Any], summary: Dict[str, Any]) -> str:
    metric = rule["metric"]
    grade = grade_value_for_metric(summary, metric)
    measured_at = summary.get("measured_at") or "unknown"
    return f"{rule['region']}|{metric}|{grade}|{measured_at}"
