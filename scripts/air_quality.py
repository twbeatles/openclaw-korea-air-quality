"""하위 호환 진입점: 기존 `python scripts/air_quality.py ...` 명령을 그대로 유지한다.

실제 구현은 `src/airquality/` 패키지에 있으며, 이 파일은 sys.path 연결과
위임만 담당한다. 과거 `scripts.air_quality` 에서 직접 import 하던 코드는
PEP 562 `__getattr__` 을 통해 패키지에서 지연 re-export 된다.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from airquality import parsing as _parsing
from airquality import store as _store
from airquality.app import main
from airquality.providers import airkorea as _airkorea_mod

__all__ = ["main"]

_LAZY_MODULES = (
    "airquality.cli.parser",
    "airquality.cli.commands",
    "airquality.constants",
    "airquality.geo",
    "airquality.grading",
    "airquality.http",
    "airquality.parsing",
    "airquality.paths",
    "airquality.providers.airkorea",
    "airquality.providers.factory",
    "airquality.providers.openmeteo",
    "airquality.services.alerts",
    "airquality.services.brief",
    "airquality.services.cron",
    "airquality.services.regions",
    "airquality.services.summary",
    "airquality.store",
)


# 원본 private 헬퍼 별칭 (구 import 코드 보호)
_to_float = _parsing.to_float
_normalize_lat_lon = _parsing.normalize_lat_lon
_airkorea_sido_name = _airkorea_mod.sido_name
_fetch_airkorea_raw = _airkorea_mod.fetch_raw
_read_json = _store.read_json
_write_json = _store.write_json


def __getattr__(name: str):
    for module_name in _LAZY_MODULES:
        try:
            return getattr(importlib.import_module(module_name), name)
        except AttributeError:
            continue
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    raise SystemExit(main())
