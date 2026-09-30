from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

import requests

from .exceptions import AuthenticationError, PrismaApiError, RateLimitExceededError

logger = logging.getLogger(__name__)

AUTH_HEADER = "x-redlock-auth"


@dataclass
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0


class PrismaHttpClient:
    """Wrapper de requests.Session com timeout, retry e backoff exponencial.

    Trata 401 (renova o token uma vez via token_provider e repete a chamada),
    429 (respeita Retry-After quando presente, senao backoff exponencial) e
    5xx (retry com backoff). Nunca loga headers, tokens ou corpo de request/response.
    """

    def __init__(
        self,
        base_url: str,
        token_provider: Callable[..., str],
        connect_timeout: float = 10.0,
        read_timeout: float = 30.0,
        retry_policy: Optional[RetryPolicy] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._retry_policy = retry_policy or RetryPolicy()
        self._session = session or requests.Session()

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        attempt = 0
        used_token_retry = False
        force_new_token = False

        while True:
            attempt += 1
            token = self._token_provider(force_new=force_new_token)
            force_new_token = False
            headers = {AUTH_HEADER: token, "Content-Type": "application/json"}

            try:
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=(self._connect_timeout, self._read_timeout),
                )
            except requests.exceptions.RequestException as exc:
                if attempt >= self._retry_policy.max_attempts:
                    raise PrismaApiError(
                        f"Falha de rede apos {attempt} tentativas em {method} {path}: {exc}"
                    ) from exc
                self._sleep_backoff(attempt)
                continue

            if response.status_code == 401:
                if used_token_retry:
                    raise AuthenticationError(
                        "Token renovado ainda recebeu HTTP 401", status_code=401
                    )
                logger.warning(
                    "HTTP 401 em %s %s, renovando token e tentando novamente uma vez",
                    method,
                    path,
                )
                used_token_retry = True
                force_new_token = True
                continue

            if response.status_code == 429:
                if attempt >= self._retry_policy.max_attempts:
                    raise RateLimitExceededError(
                        f"Rate limit excedido apos {attempt} tentativas em {method} {path}",
                        status_code=429,
                    )
                delay = self._delay_from_headers(response.headers)
                if delay is None:
                    delay = self._backoff_delay(attempt)
                logger.info(
                    "HTTP 429 em %s %s, aguardando %.1fs (tentativa %d/%d)",
                    method,
                    path,
                    delay,
                    attempt,
                    self._retry_policy.max_attempts,
                )
                time.sleep(delay)
                continue

            if 500 <= response.status_code < 600:
                if attempt >= self._retry_policy.max_attempts:
                    raise PrismaApiError(
                        f"Erro de servidor persistente HTTP {response.status_code} em {method} {path}",
                        status_code=response.status_code,
                    )
                logger.warning(
                    "HTTP %d em %s %s, tentativa %d/%d",
                    response.status_code,
                    method,
                    path,
                    attempt,
                    self._retry_policy.max_attempts,
                )
                self._sleep_backoff(attempt)
                continue

            if not response.ok:
                raise PrismaApiError(
                    f"HTTP {response.status_code} inesperado em {method} {path}",
                    status_code=response.status_code,
                )

            if not response.content:
                return None
            return response.json()

    def _sleep_backoff(self, attempt: int) -> None:
        time.sleep(self._backoff_delay(attempt))

    def _backoff_delay(self, attempt: int) -> float:
        delay = min(
            self._retry_policy.base_delay_seconds * (2 ** (attempt - 1)),
            self._retry_policy.max_delay_seconds,
        )
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter

    @staticmethod
    def _delay_from_headers(headers: Mapping[str, str]) -> Optional[float]:
        retry_after = headers.get("Retry-After")
        if not retry_after:
            return None
        try:
            return float(retry_after)
        except ValueError:
            return None
