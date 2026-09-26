"""HTTP 전송 계층: urllib 기반 GET 전담 (SRP, 테스트 시 교체 가능)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict


class HttpClient:
    """원본 fetch_text/fetch_json 과 동일한 동작의 얇은 래퍼."""

    user_agent = "OpenClaw-Korea-Air-Quality/0.6"
    timeout = 20

    def fetch_text(
        self,
        url: str,
        params: Dict[str, Any] | None = None,
        raw_query: str | None = None,
    ) -> str:
        if raw_query:
            full_url = f"{url}?{raw_query}" if "?" not in url else f"{url}&{raw_query}"
        elif params:
            query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
            full_url = f"{url}?{query}"
        else:
            full_url = url
        req = urllib.request.Request(full_url, headers={"User-Agent": self.user_agent})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return response.read().decode("utf-8")

    def fetch_json(
        self,
        url: str,
        params: Dict[str, Any] | None = None,
        raw_query: str | None = None,
    ) -> Dict[str, Any]:
        return json.loads(self.fetch_text(url, params, raw_query=raw_query))


_DEFAULT_CLIENT = HttpClient()


def fetch_text(url: str, params: Dict[str, Any] | None = None, raw_query: str | None = None) -> str:
    return _DEFAULT_CLIENT.fetch_text(url, params, raw_query=raw_query)


def fetch_json(url: str, params: Dict[str, Any] | None = None, raw_query: str | None = None) -> Dict[str, Any]:
    return _DEFAULT_CLIENT.fetch_json(url, params, raw_query=raw_query)
