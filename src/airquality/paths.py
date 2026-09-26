"""경로 resolution: 저장소 루트 기준 data 파일 위치 (SRP: 경로만 담당)."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PREFERENCES_PATH = DATA_DIR / "user-preferences.json"
STATION_CACHE_PATH = DATA_DIR / "station-cache.json"
ALERT_RULES_PATH = DATA_DIR / "alert-rules.json"
ALERT_STATE_PATH = DATA_DIR / "alert-state.json"
CONFIG_PATH = DATA_DIR / "config.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
