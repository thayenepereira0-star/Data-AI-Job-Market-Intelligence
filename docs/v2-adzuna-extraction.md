# DAI-28 — Extração bruta de vagas pela Adzuna

A extração consulta o endpoint oficial de busca de anúncios da Adzuna e preserva as páginas JSON recebidas. A API usa um código de país e paginação na rota; `br` está configurado como padrão para o Brasil.

## Executar

Com `(.venv)` ativo e as variáveis `ADZUNA_APP_ID` e `ADZUNA_APP_KEY` definidas no `.env` local:

```powershell
python -m src.ingestion.extract_adzuna --what "data analyst" --where "Rio de Janeiro" --pages 1
```

O comando salva o envelope bruto em `data/raw/adzuna_jobs.json` por padrão. Para salvar em outro lugar, use `--output`. Também é possível controlar `--country`, `--first-page`, `--pages` e `--results-per-page`. A busca padrão solicita somente uma página, para limitar a chamada inicial.

O arquivo mantém metadados da consulta e cada resposta original em `pages`. Não converte nomes de campos, valida anúncio por anúncio, remove duplicatas, grava no PostgreSQL ou contém as credenciais usadas na chamada. A DAI-29 vai transformar esses registros para o modelo interno.

## Segurança e validação

- As chaves vêm de `adzuna_credentials()` e nunca são impressas.
- `data/raw/adzuna_*.json` é ignorado pelo Git. Não versione dados baixados da API.
- Os testes substituem a resposta HTTP e as credenciais; não fazem chamadas reais.
- Erros HTTP mostram somente o código de status, sem URL, parâmetros ou corpo da resposta.

## Referências e uso

- [Documentação oficial de busca da Adzuna](https://developer.adzuna.com/docs/search)
- [Visão geral da API](https://developer.adzuna.com/overview)
- [Termos de uso da API](https://developer.adzuna.com/docs/terms_of_service)

A especificação oficial lista `br` entre os países aceitos pelo endpoint. Antes de executar coletas recorrentes ou publicar análises/dados, confira os termos atuais e limites da sua chave. Para pesquisa pessoal ou acadêmica, os termos pedem reconhecimento da Adzuna como fonte dos dados de vagas e salários publicados.