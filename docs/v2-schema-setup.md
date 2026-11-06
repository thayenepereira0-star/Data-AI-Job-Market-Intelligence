# DAI-21 — Criar as tabelas da v2 no PostgreSQL

Este script implementa o **primeiro esquema físico** definido conceitualmente na DAI-17. Execute somente depois de validar a DAI-20.

## Antes de executar

No terminal, na raiz do repositório, confirme que o banco está saudável:

```powershell
docker compose ps
```

Em seguida crie as tabelas:

```powershell
Get-Content -Raw .\sql\001_initial_schema.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U jobmarket -d jobmarket
```

**O que ocorre:** PowerShell lê o arquivo SQL e o envia para o cliente `psql` dentro do contêiner. `ON_ERROR_STOP=1` interrompe a execução em caso de erro; `BEGIN/COMMIT` garante atomicidade.

Confirme a lista de tabelas:

```powershell
docker compose exec db psql -U jobmarket -d jobmarket -c "\dt"
```

Conferência quantitativa:

```powershell
docker compose exec db psql -U jobmarket -d jobmarket -c "SELECT count(*) AS tabelas FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
```

**Esperado:** sete tabelas: `companies`, `sources`, `pipeline_runs`, `jobs`, `skills`, `job_skills`, `job_postings`.

## Decisões

- PKs numéricas `BIGINT IDENTITY`, chaves estrangeiras e índices para relacionamentos.
- `jobs` são oportunidades; `job_postings` representam aparições em fontes distintas.
- `job_skills` é o vínculo muitos-para-muitos entre vagas e habilidades, com evidências e revisão.
- Para campos não informados (`work_mode`, senioridade etc.), usa-se `NULL`, nunca inventamos dados.
- Os índices únicos evitam duplicação exata de postagens por fonte/ID externo ou fonte/URL. Duplicatas semânticas permanecem sujeitas à revisão.
- `pipeline_runs` registra execuções de processamento.
- `CREATE TABLE IF NOT EXISTS` facilita repetição em ambientes vazios, mas **não substitui migrações Alembic**, previstas mais adiante. Não executa `DROP TABLE` nem apaga dados.
- Nenhum dado real é importado nesta etapa (migração de dados: DAI-23).

## Critérios de aceite

- [x] SQL versionado para as sete tabelas e vínculos.
- [x] Instruções de implantação e consultas de verificação documentadas.
- [x] Script executado no PostgreSQL local com `BEGIN`, sete `CREATE TABLE`, índices e `COMMIT`, sem erros relatados.
- [x] Sete tabelas confirmadas por `\dt` e seis chaves estrangeiras confirmadas na consulta ao `information_schema` (evidências de terminal fornecidas pela desenvolvedora).

Testes executados pela desenvolvedora no PostgreSQL local; resultados enviados via capturas do terminal. O assistente não acessou ou executou comandos no computador dela.
