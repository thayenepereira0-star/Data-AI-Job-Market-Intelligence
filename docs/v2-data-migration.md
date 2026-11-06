# DAI-23 — Migrar e validar dados da v1

A v1 contém **dois CSVs de origens e formatos distintos**: `data/raw/jobs_pilot.csv` (3 vagas manuais do LinkedIn) e `data/processed/jobs_analysis.csv` (dataset analítico Adzuna, descrições truncadas). Nesta entrega migramos **somente o CSV analítico da Adzuna**; o piloto manual permanece preservado e fica fora da importação para não misturar esquemas nem origens sem estratégia explícita.

## Execução — PowerShell na raiz do projeto

Pré-requisitos: Docker/PostgreSQL ativo, `.env` configurado e `(.venv)` ativado, com as dependências da DAI-22 instaladas.

1. **Prévia segura, sem escrita:**

```powershell
python -m src.database.migrate_v1
```

Confira total de linhas, rejeições e duplicatas. O comando padrão **nunca abre transação de escrita**.

2. **Gravação apenas depois de aprovar a prévia:**

```powershell
python -m src.database.migrate_v1 --apply
```

3. **Validar dados gravados:**

```powershell
docker compose exec db psql -U jobmarket -d jobmarket -c "SELECT (SELECT count(*) FROM jobs) AS jobs, (SELECT count(*) FROM job_postings) AS postings, (SELECT count(*) FROM companies) AS companies, (SELECT count(*) FROM pipeline_runs) AS runs;"
```

4. **Executar novamente `--apply` (opcional, após o primeiro teste):** deve informar zero novas vagas e contagem de registros já existentes. A identidade é conferida por **fonte + ID externo quando disponível** e **fonte + URL**. A duplicação semântica entre plataformas é assunto posterior.

## Regras e limitações

- `companies`, `jobs`, `sources`, `job_postings` e `pipeline_runs` recebem os registros. Nenhuma habilidade é inventada ou extraída nesta fase.
- Nome da empresa é normalizado para comparação, mantendo o valor original.
- `title`, `empresa` e URL válidos são obrigatórios; dados ausentes não são preenchidos artificialmente.
- `created` é interpretado como publicação; `collected_at` permanece data da inserção no novo banco, **não** uma falsa data histórica de coleta.
- Salaries são preservados como valores numéricos originais; **periodicidade e moeda não são inferidas**.
- O CSV analítico não contém modalidade, senioridade, estado e município estruturados de maneira confiável; estes campos ficam `NULL`. Localização textual original não é transportada para os campos de cidade/estado para evitar interpretações erradas.
- As descrições provenientes da Adzuna podem estar truncadas; isso limitará análises de skills.
- Dados não são alterados no CSV, não há `DELETE`, `DROP`, nem treinamento de IA.
- Importação usa transação; se um erro de escrita acontecer, a importação inteira é revertida.
- Novas execuções são auditadas em `pipeline_runs`. Na execução repetida, as vagas existentes são ignoradas.
- **A migração não foi executada localmente pelo assistente:** primeiro é necessário validar a prévia e depois a gravação com a desenvolvedora.

## Critérios de aceite

- [x] Arquivo de migração versionado.
- [x] Prévia sem escrita e tratamento de dados ausentes previstos.
- [x] Deduplicação por fonte e identificador/URL prevista.
- [x] Prévia executada e conferida no computador local.
- [x] Gravação real executada e contagens auditadas no PostgreSQL.
- [x] Reexecução sem inclusão de duplicatas comprovada.

## Correção após primeiro teste de gravação

A primeira execução local de `--apply` apresentou `IndeterminateDatatype` no PostgreSQL. A consulta de detecção de duplicados continha um parâmetro usado apenas em `IS NOT NULL`, sem contexto de tipo; o trecho foi substituído por uma comparação direta `external_job_id = %s`. A alteração é no código, sem mudança no esquema e sem exclusão de registros. É necessário atualizar a branch e repetir a prévia/gravação para validar a correção.

## Resultado da validação local — DAI-23

- Prévia: 128 linhas lidas; 127 válidas; 0 duplicatas internas; 1 rejeitada (empresa ausente na linha 124).
- Primeira gravação bem-sucedida: 127 importadas; 0 já existentes.
- Consulta SQL de auditoria: 127 `jobs`, 127 `job_postings`, 82 `companies`, 1 `pipeline_runs` após a primeira gravação.
- Reexecução idempotente: **0 importadas, 127 já existentes** (saída fornecida pela desenvolvedora).
- A reexecução cria um novo registro de auditoria em `pipeline_runs`; portanto o número de execuções pode aumentar, sem duplicar vagas.
- O registro incompleto continua no CSV, sem criação de uma empresa fictícia. O piloto manual de 3 vagas não integrou esta migração.
- Evidências fornecidas pelo terminal da desenvolvedora, não por execução remota do assistente.
