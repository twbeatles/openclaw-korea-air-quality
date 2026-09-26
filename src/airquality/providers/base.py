"""대기질 provider 추상화 (DIP: 상위 계층은 이 프로토콜에만 의존, OCP: 신규 소스 추가 시 구현체만 추가)."""
from __future__ import annotations

from typing import Any, Dict, Protocol


class AirQualityProvider(Protocol):
    name: str

    def fetch(self, lat: float, lon: float, timezone: str = "Asia/Seoul", region: Dict[str, Any] | None = None) -> Dict[str, Any]:
        ...
