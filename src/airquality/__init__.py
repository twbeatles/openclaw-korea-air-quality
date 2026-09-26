"""korea-air-quality 패키지 공개 API (하위 호환 re-export 포함)."""
from . import geo, grading, http, parsing, paths, providers, services, store
from .app import main
from .cli.parser import build_parser
from .constants import (
    DISTRICT_FALLBACKS,
    GRADE_ORDER,
    REGION_ALIASES,
    STATIC_REGIONS,
    WEATHER_CODES,
)

__all__ = [
    "DISTRICT_FALLBACKS",
    "GRADE_ORDER",
    "REGION_ALIASES",
    "STATIC_REGIONS",
    "WEATHER_CODES",
    "build_parser",
    "constants",
    "geo",
    "grading",
    "http",
    "main",
    "parsing",
    "paths",
    "providers",
    "services",
    "store",
]
