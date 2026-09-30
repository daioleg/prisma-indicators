from __future__ import annotations


class ConfigError(Exception):
    """Configuração obrigatória ausente ou inválida."""


class PrismaApiError(Exception):
    """Erro genérico ao chamar a API do Prisma Cloud."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(PrismaApiError):
    """Falha de autenticação (login ou renovação de token)."""


class RateLimitExceededError(PrismaApiError):
    """Rate limit da API excedido mesmo após as tentativas de retry."""
