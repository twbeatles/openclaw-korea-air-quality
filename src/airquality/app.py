"""앱 진입점: stdout 인코딩 + 파서 실행 (SRP: 부팅만 담당)."""
from __future__ import annotations

import sys

from .cli.parser import build_parser


def ensure_utf8_stdio() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
