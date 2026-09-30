#!/usr/bin/env bash
# Roda a analise de indicadores Prisma Cloud CSPM.
#
# Credenciais: nunca hardcoded aqui. Se existir um arquivo .env.local na raiz
# do projeto (fora do git, ver .gitignore), ele e' carregado automaticamente.
# Caso contrario, assume que PRISMA_BASE_URL / PRISMA_ACCESS_KEY /
# PRISMA_SECRET_KEY ja foram exportados no shell antes de chamar este script.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$PROJECT_DIR/.env.local"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

MISSING=0
for var in PRISMA_BASE_URL PRISMA_ACCESS_KEY PRISMA_SECRET_KEY; do
  if [ -z "${!var:-}" ]; then
    echo "[MISSING] $var" >&2
    MISSING=1
  fi
done
if [ "$MISSING" = "1" ]; then
  echo "" >&2
  echo "Defina as variaveis acima no seu shell, ou crie um arquivo" >&2
  echo "$ENV_FILE (ja esta no .gitignore) com:" >&2
  echo "  PRISMA_BASE_URL=..." >&2
  echo "  PRISMA_ACCESS_KEY=..." >&2
  echo "  PRISMA_SECRET_KEY=..." >&2
  exit 1
fi

if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
  echo "Ambiente virtual nao encontrado em .venv - criando..." >&2
  python3 -m venv "$PROJECT_DIR/.venv"
  "$PROJECT_DIR/.venv/bin/pip" install --quiet --upgrade pip
  "$PROJECT_DIR/.venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"
fi

cd "$PROJECT_DIR"
PYTHONPATH=src "$PROJECT_DIR/.venv/bin/python" -m prisma_indicators.cli "$@"
