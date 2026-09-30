from __future__ import annotations

import csv
import logging
from pathlib import Path

from .models import ResourceCount

logger = logging.getLogger(__name__)

FIELDNAMES = ["provedor", "service", "resource name", "conta", "região", "quantidade"]


def write_provider_csvs(
    counts: list[ResourceCount], output_dir: Path
) -> dict[str, Path]:
    """Escreve um CSV por provedor (nome do arquivo derivado do cloud_type real
    retornado pela API - nao assume que "aws"/"azure"/"gcp"/"oci" sao os unicos
    valores possiveis; o tenant validado retornou tambem "other").

    Encoding utf-8-sig para o Excel abrir corretamente acentos (ex.: "região").
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    by_provider: dict[str, list[ResourceCount]] = {}
    for count in counts:
        by_provider.setdefault(count.provider, []).append(count)

    written: dict[str, Path] = {}
    for provider, rows in sorted(by_provider.items()):
        rows.sort(key=lambda r: (r.service, r.resource_name, r.account, r.region))
        path = output_dir / f"{_safe_filename(provider)}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(FIELDNAMES)
            for row in rows:
                writer.writerow(
                    [
                        row.provider,
                        row.service,
                        row.resource_name,
                        row.account,
                        row.region,
                        row.quantity,
                    ]
                )
        written[provider] = path
        logger.info("CSV escrito: %s (%d linhas)", path, len(rows))
    return written


def totals_by_provider(counts: list[ResourceCount]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for count in counts:
        totals[count.provider] = totals.get(count.provider, 0) + count.quantity
    return dict(sorted(totals.items()))


def _safe_filename(provider: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in provider.lower())
    return cleaned or "unknown"
