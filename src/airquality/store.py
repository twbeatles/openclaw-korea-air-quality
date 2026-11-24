"""JSON 파일 저장소: data/*.json 읽기/쓰기 전담 (SRP).

원본의 _read_json/_write_json + load_*/save_* 함수군을 그대로 옮겼다.
상위 계층은 파일 경로를 직접 다루지 않고 이 모듈의 함수에 의존한다 (DIP).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from . import paths


def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    paths.ensure_data_dir()
    if not path.exists():
        return default
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return default
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        _backup_corrupt_file(path)
        return default
    return data if isinstance(data, dict) else default


def _backup_corrupt_file(path: Path) -> None:
    """깨진 설정 파일은 .bak 으로 보존하고 기본값으로 복구 (데이터 손실 방지)."""
    try:
        backup = path.with_name(path.name + ".bak")
        backup.write_bytes(path.read_bytes())
    except OSError:
        pass


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    paths.ensure_data_dir()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_preferences() -> Dict[str, Any]:
    return read_json(paths.PREFERENCES_PATH, {"users": {}})


def save_preferences(payload: Dict[str, Any]) -> None:
    write_json(paths.PREFERENCES_PATH, payload)


def load_station_cache() -> Dict[str, Any]:
    return read_json(paths.STATION_CACHE_PATH, {"regions": {}})


def save_station_cache(payload: Dict[str, Any]) -> None:
    write_json(paths.STATION_CACHE_PATH, payload)


def load_alert_rules() -> Dict[str, Any]:
    return read_json(paths.ALERT_RULES_PATH, {"rules": []})


def save_alert_rules(payload: Dict[str, Any]) -> None:
    write_json(paths.ALERT_RULES_PATH, payload)


def load_alert_state() -> Dict[str, Any]:
    return read_json(paths.ALERT_STATE_PATH, {"lastHits": {}})


def save_alert_state(payload: Dict[str, Any]) -> None:
    write_json(paths.ALERT_STATE_PATH, payload)


def load_config() -> Dict[str, Any]:
    return read_json(paths.CONFIG_PATH, {"provider": "openmeteo", "airkorea_api_key": None})


def save_config(payload: Dict[str, Any]) -> None:
    write_json(paths.CONFIG_PATH, payload)
