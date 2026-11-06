# DAI-24 — Consultas SQL para exploração do banco

O arquivo `sql/002_analysis_queries.sql` contém **8 consultas de leitura** para validar e explorar a amostra importada da v1.

## Executar no VS Code (PowerShell)

Na raiz do repositório, com PostgreSQL ativo (`docker compose ps` deve mostrar `healthy`):

```powershell
Get-Content -Raw .\sql\002_analysis_queries.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U jobmarket -d jobmarket
```

O arquivo usa `SELECT` e `\\echo` do psql para separar relatórios. Ele **não grava, altera ou exclui registros**.

## O que cada consulta responde

1. Quantas vagas, publicações, empresas e fontes existem?
2. Quais empresas mais aparecem nesta amostra?
3. Como as vagas se distribuem por mês de publicação (UTC)?
4. Quantos registros possuem descrição, data, contrato, salário e modalidade?
5. Quais são os títulos literais mais repetidos?
6. Quantas publicações foram registradas por plataforma?
7. Existem publicações órfãs ou vagas sem empresa? O esperado é zero.
8. Quais execuções de migração constam na auditoria?

## Interpretação e limites

- **Amostra, não mercado brasileiro:** os dados foram obtidos a partir do CSV analítico da Adzuna. Não extrapolar resultados para todas as vagas do país.
- **127 vagas não equivalem a 127 empresas:** o relacionamento entre `jobs` e `companies` evita repetição de empresas na modelagem.
- **Fonte ≠ cargo:** o arquivo `jobs_analysis.csv` tinha `cargo_base`, mas a migração DAI-23 não criou essa coluna em `jobs`. Portanto, o relatório atual de títulos mostra **títulos literais**, não categorias classificadas.
- **Localização e modalidade:** não foram preenchidas na migração porque os dados originais não estavam estruturados com confiança. Não interpretar `NULL` como vaga presencial ou remota.
- **Salário:** se preenchido, a moeda e periodicidade não foram normalizadas; os relatórios não calculam média comparativa de remuneração.
- **Data:** agregação mensal usa UTC; `collected_at` dos jobs representa inserção no banco novo, não data histórica de coleta.
- **Execuções:** `pipeline_runs` pode crescer em novas reexecuções idempotentes. Isso não significa novas vagas.

## Critérios de aceite

- [x] Consultas SQL versionadas e documentadas.
- [x] Executar consultas no PostgreSQL local com sucesso.
- [x] Conferir contagens, vínculos e campos ausentes.
- [x] Registrar resultados reais da execução local.
- [ ] Mesclar PR após revisão.

## Resultados da execução local (evidência fornecida em terminal)

O script de oito blocos foi executado com sucesso em `psql` pela desenvolvedora.

- Resumo: **127 vagas**, **127 publicações**, **82 empresas** e **1 fonte** (Adzuna).
- Empresas mais frequentes: BEES (12), AB InBev (11), Jobgether (5), Decision group (3), DoorDash (3), Pavago (3), 3M (2), Azumo (2), BP (2), Banco Bradesco (2).
- Distribuição mensal UTC 2026: janeiro 1, fevereiro 1, março 1, abril 2, maio 5, junho 4, julho 11, agosto 20, setembro 27, outubro 55 (soma 127).
- Completude: 127 com descrição, 127 com data de publicação, 18 com tipo de contrato, 11 com algum salário, 0 com modalidade.
- Títulos literais mais frequentes: Data Engineer (11), Senior Data Engineer (9), Data Scientist (8), Intermediate Data Analyst (5), Senior Data Analyst (5).
- Fontes: Adzuna 127 publicações.
- Integridade: 0 publicações sem vaga, 0 vagas sem empresa, 0 publicações sem fonte.
- Execuções auditadas: dois registros `pipeline_runs`, com status `partial` (uma linha rejeitada em cada execução); uma execução importou 127 e a reexecução importou 0.

**Cuidados:** mais vagas em outubro podem refletir a coleta, não crescimento do mercado; a classificação por título aqui é literal; os campos sem dados precisam de enriquecimento posterior. Textos acentuados apareceram com caracteres `??` no terminal Windows em um título do relatório; isso é sintoma de codificação de exibição e não comprova corrupção de dados.
