"""앱 진입점: stdout 인코딩 + 파서 실행 (SRP: 부팅만 담당)."""
from __future__ import annotations

import sys

from .cli.parser import build_parser


def ensure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream and hasattr(stream, "reconfigure"):
            try:
                getattr(stream, "reconfigure")(encoding="utf-8")  # noqa: B009 -- TextIO 스텁에 없음; hasattr 가드+try로 런타임 안전
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
