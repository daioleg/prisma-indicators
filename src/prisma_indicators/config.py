from __future__ import annotations

import os
from dataclasses import dataclass, field

from .exceptions import ConfigError

REQUIRED_ENV_VARS = ("PRISMA_BASE_URL", "PRISMA_ACCESS_KEY", "PRISMA_SECRET_KEY")


@dataclass
class PrismaConfig:
    base_url: str
    access_key: str = field(repr=False)
    secret_key: str = field(repr=False)

    @classmethod
    def from_env(cls) -> "PrismaConfig":
        missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
        if missing:
            raise ConfigError(
                "Variáveis de ambiente obrigatórias ausentes: " + ", ".join(missing)
            )
        return cls(
            base_url=os.environ["PRISMA_BASE_URL"].rstrip("/"),
            access_key=os.environ["PRISMA_ACCESS_KEY"],
            secret_key=os.environ["PRISMA_SECRET_KEY"],
        )
