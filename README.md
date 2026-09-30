# Inventário de recursos Prisma Cloud CSPM

Gera um CSV por provedor de cloud (AWS, Azure, GCP, OCI, ...) com a
**quantidade de recursos** monitorados pelo Prisma Cloud, quebrada por serviço,
tipo de recurso, conta e região, e mostra no terminal o total de cada cloud.

O código usa **apenas a API agregada** do inventário: nunca lista recursos
individuais, o que permite rodar em ambientes com 10M+ recursos.

## Como funciona

```
run.sh ──► cli.py
             │
             ├─ 1. config.py          lê PRISMA_BASE_URL / ACCESS_KEY / SECRET_KEY do ambiente
             ├─ 2. auth.py            POST /login → JWT em memória (renova antes dos 10 min)
             ├─ 3. inventory_client   POST /v3/inventory com groupBy agregado
             │        (via http_client: timeout, retry, backoff, renovação em 401)
             ├─ 4. models.py          converte cada grupo da resposta em ResourceCount
             ├─ 5. csv_export.py      separa por provedor e escreve output/<provedor>.csv
             └─ 6. cli.py             imprime o total de recursos por cloud
```

1. **Configuração** — as credenciais vêm só de variáveis de ambiente (ou do
   `.env.local`, carregado pelo `run.sh`). Se faltar alguma, o programa para
   com erro indicando qual.
2. **Autenticação** — faz login no Prisma Cloud e guarda o token só em memória.
   O token nunca é gravado em disco nem aparece nos logs.
3. **Consulta agregada** — faz **uma única** chamada:

   ```json
   POST /v3/inventory
   { "groupBy": ["cloud.type", "cloud.service", "resource.type", "cloud.account", "cloud.region"] }
   ```

   A API devolve um grupo para cada combinação de
   provedor + serviço + tipo de recurso + conta + região, com o campo
   `totalResources`.
4. **Normalização** — cada grupo vira um `ResourceCount`. Campos ausentes ficam
   como `N/A`.
5. **Exportação** — os grupos são separados por provedor. Cada provedor gera
   seu próprio arquivo, ordenado por serviço, recurso, conta e região. O nome
   do arquivo vem do provedor que a API devolveu, então provedores como
   `other` também ganham arquivo.
6. **Resumo** — imprime no terminal a quantidade de recursos de cada cloud e o
   total geral.

### Formato do CSV

`output/aws.csv`, `output/azure.csv`, `output/gcp.csv`, ...

```
provedor,service,resource name,conta,região,quantidade
aws,Amazon EC2,AWS EC2 Instance,prod-account,AWS Virginia,120
```

| Coluna          | Origem na API                               |
|-----------------|---------------------------------------------|
| `provedor`      | `cloudTypeName`                             |
| `service`       | `serviceName`                               |
| `resource name` | `resourceTypeName` (tipo do recurso)        |
| `conta`         | `accountName` (ou `accountId` se vazio)     |
| `região`        | `regionName`                                |
| `quantidade`    | `totalResources`                            |

`resource name` é o **tipo** do recurso (ex.: "AWS EC2 Instance"), e não o nome
de cada recurso, porque a contagem é agregada. Os arquivos saem em UTF-8 com
BOM para o Excel exibir os acentos corretamente.

### Exemplo de saída no terminal

```
Quantidade de recursos por cloud
--------------------------------------------------
aws                1,234,567   output/aws.csv
azure                456,789   output/azure.csv
gcp                   98,765   output/gcp.csv
--------------------------------------------------
TOTAL              1,790,121
```

## Estrutura do projeto

```
.
├── run.sh                      # ponto de entrada: carrega .env.local, cria .venv e roda o CLI
├── requirements.txt            # dependências (requests)
├── pyproject.toml
├── src/prisma_indicators/
│   ├── cli.py                  # orquestra o fluxo e imprime o resumo; argumento --output-dir
│   ├── config.py               # PrismaConfig: lê e valida as variáveis de ambiente
│   ├── auth.py                 # PrismaAuth: login e renovação do JWT
│   ├── http_client.py          # PrismaHttpClient: timeout, retry com backoff, 401/429/5xx
│   ├── exceptions.py           # ConfigError, PrismaApiError, AuthenticationError, RateLimitExceededError
│   ├── models.py               # ResourceCount: uma linha do CSV
│   ├── csv_export.py           # escreve um CSV por provedor e calcula os totais
│   └── clients/
│       └── inventory_client.py # InventoryClient: chamada agregada a /v3/inventory
├── tests/                      # testes unitários (sem rede; usam fakes em testing_utils.py)
└── output/                     # CSVs gerados (fora do git)
```

### Resiliência das chamadas HTTP (`http_client.py`)

- **401**: renova o token uma vez e repete a chamada.
- **429**: respeita o header `Retry-After`. Sem o header, usa backoff exponencial.
- **5xx / erro de rede**: retry com backoff exponencial e jitter (até 5 tentativas).
- Headers, tokens e corpos de request/response nunca são logados.

## Como rodar

### 1. Pré-requisitos

- Python 3.9+
- Uma Access Key do Prisma Cloud com permissão de leitura no inventário

### 2. Credenciais

Nunca coloque as credenciais no código. Há duas opções.

**Opção A: arquivo `.env.local`** na raiz do projeto (já está no `.gitignore`).
O `run.sh` carrega esse arquivo automaticamente:

```
PRISMA_BASE_URL=https://api.prismacloud.io
PRISMA_ACCESS_KEY=...
PRISMA_SECRET_KEY=...
```

**Opção B: variáveis exportadas no shell**, antes de rodar:

```bash
export PRISMA_BASE_URL=https://api.prismacloud.io
export PRISMA_ACCESS_KEY=...
export PRISMA_SECRET_KEY=...
```

`PRISMA_BASE_URL` é a URL da API do seu tenant (ex.: `api.prismacloud.io`,
`api2.prismacloud.io`, `api.eu.prismacloud.io`...).

### 3. Executar

```bash
./run.sh
```

Na primeira execução, o `run.sh` cria o ambiente virtual `.venv` e instala as
dependências automaticamente.

Para salvar os CSVs em outro diretório:

```bash
./run.sh --output-dir /caminho/para/saida
```

Também é possível rodar sem o `run.sh`. Nesse caso as variáveis precisam estar
exportadas no shell:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
PYTHONPATH=src ./.venv/bin/python -m prisma_indicators.cli
```

### 4. Testes

Os testes não fazem nenhuma chamada de rede:

```bash
PYTHONPATH=src ./.venv/bin/python -m unittest discover -s tests -v
```

## Limitações conhecidas

- Os campos `serviceName`, `accountName` e `accountId` na resposta agregada
  seguem a documentação, mas **ainda não foram validados com uma chamada
  real**. Se vierem com outro nome, a coluna sai como `N/A`. Nesse caso,
  ajuste as chaves em `ResourceCount.from_api` (`models.py`).
- Não foi validado se `/v3/inventory` pagina a resposta com um `groupBy` tão
  granular. Se a resposta trouxer `nextPageToken`, o código loga um aviso de
  que o resultado pode estar incompleto.
- O `groupBy` usa `cloud.type` (com ponto). A variante `cloudType`, citada na
  documentação, retornou resultado vazio no tenant testado.
