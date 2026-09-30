# Indicadores Prisma Cloud CSPM

Indicadores de Cloud Security correlacionando inventário agregado e alertas do
Prisma Cloud, sem nunca listar recursos individuais (ambiente com 10M+ recursos).

## Setup

```
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

## Credenciais

Nunca colocar no código. Exportar como variáveis de ambiente antes de rodar:

```
export PRISMA_BASE_URL=...
export PRISMA_ACCESS_KEY=...
export PRISMA_SECRET_KEY=...
```

## Rodar

```
./run.sh
# ou
PYTHONPATH=src ./.venv/bin/python -m prisma_indicators.cli [--output-dir output]
```

Faz **uma** chamada agregada a `POST /v3/inventory` com
`groupBy = cloud.type, cloud.service, resource.type, cloud.account, cloud.region`
(nunca lista recursos individuais) e gera:

- `output/<provedor>.csv` — um arquivo por `cloudTypeName` retornado pela API
  (não assume que só existem aws/azure/gcp/oci), com as colunas:
  `provedor,service,resource name,conta,região,quantidade`
- no terminal, o total de recursos de cada cloud.

`resource name` é o tipo de recurso (`resourceTypeName`), já que a contagem é
agregada. `conta` usa `accountName` (ou `accountId` se o nome vier vazio).

## Testes

```
PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests -v
```

## Limitações conhecidas

- Os campos `serviceName` / `accountName` / `accountId` na resposta agregada
  seguem a documentação, mas **ainda não foram validados com chamada real**.
  Se vierem com outro nome, a coluna sai como `N/A` (ajustar em `models.py`).
- Não foi validado se `/v3/inventory` pagina quando o `groupBy` é tão
  granular. Se a resposta trouxer `nextPageToken`, o código loga um aviso.
