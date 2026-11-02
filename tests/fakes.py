from __future__ import annotations

import time
from typing import Any


class FakeClient:
    def __init__(self, fail: bool = False, delay: float = 0.0) -> None:
        self.fail = fail
        self.delay = delay
        self.calls: list[dict[str, Any]] = []

    def log(
        self,
        message: str,
        *,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("network down")
        self.calls.append({"message": message, "severity": severity, "context": context or {}})
        return {}
