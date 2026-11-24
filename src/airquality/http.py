"""HTTP 전송 계층: urllib 기반 GET 전담 (SRP, 테스트 시 교체 가능).

일시 장애(429/5xx/타임아웃)는 지수 백오프로 재시도하고,
인증·요청 오류(400/401/403/404)는 즉시 반환한다.
운영 값(타임아웃/재시도/UA)은 constants에서 한 곳으로 관리한다.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict

from . import constants as constants_module


class HttpClient:
    """원본 fetch_text/fetch_json 과 동일한 동작의 얇은 래퍼."""

    user_agent = constants_module.HTTP_USER_AGENT
    timeout = constants_module.HTTP_TIMEOUT_SECONDS
    max_retries = constants_module.HTTP_MAX_RETRIES

    def __init__(
        self,
        user_agent: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        if user_agent is not None:
            self.user_agent = user_agent
        if timeout is not None:
            self.timeout = timeout
        if max_retries is not None:
            self.max_retries = max_retries
        self._sleep = sleep or time.sleep

    def _should_retry(self, exc: BaseException) -> bool:
        if isinstance(exc, urllib.error.HTTPError):
            if exc.code in constants_module.HTTP_NO_RETRY_STATUS:
                return False
            return True
        return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError))

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
        attempts = max(1, int(self.max_retries))
        last_exc: BaseException | None = None
        for attempt in range(attempts):
            try:
                req = urllib.request.Request(full_url, headers={"User-Agent": self.user_agent})
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    return response.read().decode("utf-8")
            except Exception as exc:  # noqa: BLE001 -- 전송 오류는 재시도 판정 후 그대로 전달
                last_exc = exc
                if attempt >= attempts - 1 or not self._should_retry(exc):
                    raise
                self._sleep(constants_module.HTTP_RETRY_BACKOFF_SECONDS * (2**attempt))
        assert last_exc is not None  # pragma: no cover -- 루프는 항상 예외 또는 반환으로 종료
        raise last_exc

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
