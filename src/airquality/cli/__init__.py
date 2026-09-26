"""cli 패키지 공개 API."""
from .commands import (
    cmd_alert_add,
    cmd_alert_check,
    cmd_alert_list,
    cmd_alert_remove,
    cmd_clear_default,
    cmd_compare,
    cmd_cron_plan,
    cmd_morning_brief,
    cmd_now,
    cmd_resolve_region,
    cmd_save_default,
    cmd_save_location,
    cmd_setup_provider,
    cmd_show_config,
    cmd_show_default,
)
from .parser import build_parser

__all__ = [
    "build_parser",
    "cmd_alert_add",
    "cmd_alert_check",
    "cmd_alert_list",
    "cmd_alert_remove",
    "cmd_clear_default",
    "cmd_compare",
    "cmd_cron_plan",
    "cmd_morning_brief",
    "cmd_now",
    "cmd_resolve_region",
    "cmd_save_default",
    "cmd_save_location",
    "cmd_setup_provider",
    "cmd_show_config",
    "cmd_show_default",
]
