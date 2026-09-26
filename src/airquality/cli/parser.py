"""argparse 정의: 서브커맨드/옵션 선언만 담당 (SRP). 동작은 commands 에 위임 (OCP)."""
from __future__ import annotations

import argparse

from . import commands


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
    p.set_defaults(func=commands.cmd_now)

    p = sub.add_parser("morning-brief", help="날씨+대기질 아침 브리핑")
    p.add_argument("region", nargs="?")
    p.add_argument("--user")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--location-text", help="메신저 위치공유 JSON, 위경도 문자열, 지도 링크 등")
    p.add_argument("--json", action="store_true")
    add_provider_args(p)
    p.set_defaults(func=commands.cmd_morning_brief)

    p = sub.add_parser("resolve-region", help="지역명 해석/좌표 확인")
    p.add_argument("region")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_resolve_region)

    p = sub.add_parser("compare", help="여러 지역 대기질 비교")
    p.add_argument("regions", nargs="+")
    p.add_argument("--json", action="store_true")
    add_provider_args(p)
    p.set_defaults(func=commands.cmd_compare)

    p = sub.add_parser("save-default", help="사용자 기본 지역 저장")
    p.add_argument("user")
    p.add_argument("region")
    p.set_defaults(func=commands.cmd_save_default)

    p = sub.add_parser("clear-default", help="사용자 기본 지역/위치 삭제")
    p.add_argument("user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_clear_default)

    p = sub.add_parser("save-location", help="사용자 기본 위치 좌표 저장")
    p.add_argument("user")
    p.add_argument("lat", nargs="?", type=float)
    p.add_argument("lon", nargs="?", type=float)
    p.add_argument("--label")
    p.add_argument("--location-text", help="메신저 위치공유 JSON, 위경도 문자열, 지도 링크 등")
    p.set_defaults(func=commands.cmd_save_location)

    p = sub.add_parser("show-default", help="사용자 기본 지역/위치 조회")
    p.add_argument("user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_show_default)

    p = sub.add_parser("setup-provider", help="기본 provider 및 국내 API 키 저장")
    p.add_argument("provider", choices=["openmeteo", "airkorea"])
    p.add_argument("--airkorea-api-key")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_setup_provider)

    p = sub.add_parser("show-config", help="provider 설정 조회")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_show_config)

    p = sub.add_parser("alert-add", help="대기질 알림 규칙 추가")
    p.add_argument("user")
    p.add_argument("region")
    p.add_argument("metric", choices=["pm2_5", "pm10", "overall", "ozone", "khai"])
    p.add_argument("threshold", choices=["좋음", "보통", "나쁨", "매우나쁨"])
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_alert_add)

    p = sub.add_parser("alert-list", help="알림 규칙 목록")
    p.add_argument("--user")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_alert_list)

    p = sub.add_parser("alert-remove", help="대기질 알림 규칙 삭제")
    p.add_argument("--user")
    p.add_argument("--id", type=int, help="삭제할 규칙 ID")
    p.add_argument("--all", action="store_true", help="모든 규칙 삭제")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_alert_remove)

    p = sub.add_parser("alert-check", help="알림 규칙 점검")
    p.add_argument("--user")
    p.add_argument("--json", action="store_true")
    p.add_argument("--emit-all", action="store_true")
    p.add_argument("--announce-text", action="store_true", help="cron/announce friendly plain text output")
    add_provider_args(p)
    p.set_defaults(func=commands.cmd_alert_check)

    p = sub.add_parser("cron-plan", help="OpenClaw cron job 초안 생성")
    p.add_argument("kind", choices=["morning-brief", "alert-check"])
    p.add_argument("user")
    p.add_argument("--region")
    p.add_argument("--metric", choices=["pm2_5", "pm10", "overall", "ozone", "khai"])
    p.add_argument("--threshold", choices=["좋음", "보통", "나쁨", "매우나쁨"])
    p.add_argument("--hour", type=int)
    p.add_argument("--minute", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=commands.cmd_cron_plan)

    return parser
