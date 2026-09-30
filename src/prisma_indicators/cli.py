from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .auth import PrismaAuth
from .clients.inventory_client import InventoryClient
from .config import PrismaConfig
from .csv_export import totals_by_provider, write_provider_csvs
from .exceptions import ConfigError, PrismaApiError
from .http_client import PrismaHttpClient

logger = logging.getLogger(__name__)


def run(output_dir: str = "output") -> None:
    try:
        config = PrismaConfig.from_env()
    except ConfigError as exc:
        logger.error("Configuracao invalida: %s", exc)
        raise SystemExit(1) from exc

    auth = PrismaAuth(config)
    http_client = PrismaHttpClient(base_url=config.base_url, token_provider=auth.get_token)
    inventory_client = InventoryClient(http_client)

    try:
        counts = inventory_client.fetch_resource_counts()
    except PrismaApiError as exc:
        logger.error("Falha ao buscar inventario agregado: %s", exc)
        raise SystemExit(1) from exc

    written = write_provider_csvs(counts, Path(output_dir))
    print_summary(totals_by_provider(counts), written)


def print_summary(totals: dict[str, int], written: dict[str, Path]) -> None:
    print()
    print("Quantidade de recursos por cloud")
    print("-" * 50)
    for provider, total in totals.items():
        print(f"{provider:<12} {total:>15,}   {written.get(provider, '')}")
    print("-" * 50)
    print(f"{'TOTAL':<12} {sum(totals.values()):>15,}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera um CSV de quantidade de recursos por provedor (Prisma Cloud)."
    )
    parser.add_argument(
        "--output-dir", default="output", help="Diretorio de saida (padrao: output)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    run(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
