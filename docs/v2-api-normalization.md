# DAI-29 — Normalização de anúncios de APIs (proposta em PR)

Módulo: `src/processing/api_job_transform.py`.

Recebe um envelope JSON produzido por Adzuna, Himalayas, Greenhouse ou Lever e retorna `(validos, rejeitados)`. Não acessa redes, não escreve JSON e não abre conexões com o banco.

## Contrato interno

`NormalizedJob` inclui: `source`, `external_id`, `title`, `company`, `normalized_company`, `url`, `description`, `published_at`, `location` e `employment_type`. Ausências opcionais resultam em `None`; campos obrigatórios inválidos são rejeitados com motivo.

**Importante:** para Greenhouse e Lever o identificador da página de carreira é usado provisoriamente como empresa. Validar a correspondência jurídica antes de produzir indicadores por empregador. O campo `updated_at` da Greenhouse não é necessariamente a data de publicação: não interpretar estatísticas temporais como datas de anúncio sem ajustar o mapeamento.

As respostas podem incluir HTML e dados sujeitos às condições de uso das fontes. O transformador não autoriza persistência de anúncios; a DAI-30 deve impor uma lista de fontes explicitamente aprovadas para gravação.

## Verificações
`python -m unittest discover -s tests -p "test_*.py" -v`

## Dependências
DAI-28 + DAI-65/64/67 desenvolvidos em PRs independentes. Este PR traz apenas o contrato de transformação, para integração incremental após as branches dos conectores.
