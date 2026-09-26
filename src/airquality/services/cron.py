"""cron-plan 조립: OpenClaw 등록용 작업 명세 생성 (SRP).

원본과 동일한 schedule/command 문자열을 유지한다.
"""
from __future__ import annotations

from typing import Any, Dict

from ..paths import BASE_DIR


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
