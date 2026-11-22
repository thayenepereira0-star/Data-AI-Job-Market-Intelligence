# DAI-30 — Carga incremental controlada de dados normalizados

Este PR é **dependente** da DAI-29 e foi criado em uma branch derivada de `feat/dai-29-normalize-api-jobs`; não mesclar antes da normalização.

## Fluxo de uso

1. Obter um envelope JSON de fonte autorizada, apenas quando a retenção e o processamento forem compatíveis com os termos da fonte.
2. Prévia **sem gravar no banco**:

```powershell
python -m src.database.load_api_jobs --input data/raw/adzuna_jobs.json
```

3. Somente após revisar as permissões da fonte e conferir a prévia, executar explicitamente:

```powershell
python -m src.database.load_api_jobs --input data/raw/adzuna_jobs.json --apply --approved-source adzuna
```

A flag `--approved-source` é uma declaração do operador sobre a permissão de armazenamento; **não representa autorização concedida por este software**.

## Segurança e limitações

- Não executa DDL, `DELETE`, `TRUNCATE` ou migração destrutiva.
- Usa transação única, tabela de fontes, índices únicos existentes e consulta prévia para evitar importar anúncios repetidos na mesma fonte.
- Mantém as 127 vagas anteriores. Não afirma idempotência diante de múltiplos processos simultâneos; concorrência exige tratamento adicional.
- Fonte Greenhouse/Lever pode identificar empresa apenas por slug; requer confirmação antes de gravar.
- Himalayas: não usar com persistência histórica sem avaliar explicitamente condições sobre expiração, atribuição e redistribuição.
- Credenciais continuam no `.env` local.
- A suíte de testes NÃO acessa o PostgreSQL; execução real de inserção e segunda carga idempotente permanecem para validação local.

**Atenção:** os anúncios recebidos das APIs não foram testados em uma carga real no PostgreSQL neste PR. Mantenha em rascunho até validar integralidade e idempotência com o banco local.
