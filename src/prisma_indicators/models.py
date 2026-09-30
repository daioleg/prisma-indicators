from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

UNKNOWN = "N/A"


def _first(raw: dict[str, Any], *keys: str) -> Optional[str]:
    """Devolve o primeiro valor nao vazio entre as chaves informadas."""
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return None


@dataclass(frozen=True)
class ResourceCount:
    """Uma linha de /v3/inventory agregado por
    provedor + servico + tipo de recurso + conta + regiao.

    Os nomes cloudTypeName / resourceTypeName / regionName foram confirmados
    em chamada real (2026-09-29). serviceName / accountName / accountId seguem
    a convencao da documentacao do Inventory API e ainda nao foram validados
    com chamada real - por isso ha fallbacks para chaves alternativas.
    """

    provider: str
    service: str
    resource_name: str
    account: str
    region: str
    quantity: int

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "ResourceCount":
        return cls(
            provider=_first(raw, "cloudTypeName", "cloudType") or UNKNOWN,
            service=_first(raw, "serviceName", "cloudServiceName", "service") or UNKNOWN,
            resource_name=_first(raw, "resourceTypeName", "resourceType") or UNKNOWN,
            account=_first(raw, "accountName", "accountId", "cloudAccountName")
            or UNKNOWN,
            region=_first(raw, "regionName", "regionId", "region") or UNKNOWN,
            quantity=int(raw.get("totalResources", 0) or 0),
        )
