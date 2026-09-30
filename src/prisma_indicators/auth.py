from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from .config import PrismaConfig
from .exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# Confirmado na documentacao oficial e validado com chamada real em 2026-09-29.
TOKEN_TTL_SECONDS = 600
RENEW_MARGIN_SECONDS = 120


class PrismaAuth:
    """Mantem o JWT do Prisma Cloud em memoria, renovando antes de expirar.

    O token nunca e persistido em disco nem logado. O campo de resposta que
    contem o JWT foi confirmado como "token" numa chamada real a POST /login.
    """

    def __init__(
        self,
        config: PrismaConfig,
        session: Optional[requests.Session] = None,
        connect_timeout: float = 10.0,
        read_timeout: float = 20.0,
    ) -> None:
        self._config = config
        self._session = session or requests.Session()
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._token: Optional[str] = None
        self._obtained_at: float = 0.0

    def get_token(self, force_new: bool = False) -> str:
        if force_new or self._token is None or self._is_near_expiry():
            self._login()
        assert self._token is not None
        return self._token

    def _is_near_expiry(self) -> bool:
        age = time.monotonic() - self._obtained_at
        return age >= (TOKEN_TTL_SECONDS - RENEW_MARGIN_SECONDS)

    def _login(self) -> None:
        url = f"{self._config.base_url}/login"
        try:
            response = self._session.post(
                url,
                json={
                    "username": self._config.access_key,
                    "password": self._config.secret_key,
                },
                timeout=(self._connect_timeout, self._read_timeout),
            )
        except requests.exceptions.RequestException as exc:
            raise AuthenticationError(f"Falha de rede ao autenticar: {exc}") from exc

        if response.status_code != 200:
            raise AuthenticationError(
                f"Autenticacao falhou com HTTP {response.status_code}: "
                f"{self._extract_sanitized_message(response)}",
                status_code=response.status_code,
            )

        body = response.json()
        token = body.get("token")
        if not token:
            raise AuthenticationError(
                "Login retornou HTTP 200 sem campo 'token' na resposta"
            )

        self._token = token
        self._obtained_at = time.monotonic()
        logger.info("Token Prisma Cloud obtido/renovado com sucesso")

    @staticmethod
    def _extract_sanitized_message(response: requests.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return "(corpo de resposta nao e JSON)"
        return str(body.get("message") or body.get("error") or "sem mensagem")
