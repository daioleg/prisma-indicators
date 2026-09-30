"""Utilitarios de mock de HTTP compartilhados pelos testes (sem dependencias externas)."""
from __future__ import annotations

import json as json_module
from typing import Any, Optional


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_data: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.headers = headers or {}
        self.content = b"1" if json_data is not None else b""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("no json body")
        return self._json_data

    @property
    def text(self) -> str:
        return json_module.dumps(self._json_data) if self._json_data is not None else ""


class FakeSession:
    """Substitui requests.Session: devolve respostas pre-programadas em sequencia."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request(self, method, url, params=None, json=None, headers=None, timeout=None):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if not self._responses:
            raise AssertionError("FakeSession esgotou as respostas programadas")
        return self._responses.pop(0)

    def post(self, url, json=None, timeout=None):
        return self.request("POST", url, json=json, timeout=timeout)


class FakeHttpClient:
    """Substitui PrismaHttpClient nos testes dos clients de mais alto nivel."""

    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request_json(self, method, path, *, params=None, json_body=None):
        self.calls.append(
            {"method": method, "path": path, "params": params, "json_body": json_body}
        )
        if not self._responses:
            raise AssertionError("FakeHttpClient esgotou as respostas programadas")
        return self._responses.pop(0)
