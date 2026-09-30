from __future__ import annotations

import logging
from typing import Sequence

from ..http_client import PrismaHttpClient
from ..models import ResourceCount

logger = logging.getLogger(__name__)

# Validado com chamada real em 2026-09-29. A doc oficial lista "cloudType" (sem
# ponto) como valor aceito de groupBy, mas isso retornou groupedAggregates
# vazio (HTTP 200, sem erro) no tenant testado. "cloud.type" (com ponto, igual
# ao nome usado nos filtros de /filter/v2/inventory/suggest) funcionou.
VALID_GROUP_BY = {
    "cloud.type",
    "cloud.account",
    "cloud.region",
    "cloud.service",
    "resource.type",
}

RESOURCE_COUNT_GROUP_BY = [
    "cloud.type",
    "cloud.service",
    "resource.type",
    "cloud.account",
    "cloud.region",
]


class InventoryClient:
    """Cliente para /v3/inventory (Asset Inventory View V3), somente modo agregado.

    Nunca lista recursos individuais - so usa groupBy para obter contagens,
    o que permite operar em ambientes com 10M+ recursos monitorados.
    """

    def __init__(self, http_client: PrismaHttpClient) -> None:
        self._http = http_client

    def fetch_resource_counts(
        self, group_by: Sequence[str] = RESOURCE_COUNT_GROUP_BY
    ) -> list[ResourceCount]:
        invalid = set(group_by) - VALID_GROUP_BY
        if invalid:
            raise ValueError(
                f"groupBy invalido: {sorted(invalid)}. Valores aceitos: {sorted(VALID_GROUP_BY)}"
            )

        body = self._http.request_json(
            "POST", "/v3/inventory", json_body={"groupBy": list(group_by)}
        )
        body = body or {}
        rows = body.get("groupedAggregates", [])
        logger.info(
            "Inventory: %d grupos retornados para groupBy=%s", len(rows), list(group_by)
        )
        # Paginacao nao foi observada em chamadas reais com groupBy menos
        # granular. Se a API devolver um token de proxima pagina, avisa - os
        # dados podem estar incompletos.
        if body.get("nextPageToken"):
            logger.warning(
                "Resposta de /v3/inventory contem nextPageToken - o resultado pode "
                "estar incompleto (paginacao nao implementada para este endpoint)"
            )
        return [ResourceCount.from_api(row) for row in rows]
