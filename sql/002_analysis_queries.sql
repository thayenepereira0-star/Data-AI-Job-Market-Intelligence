-- DAI-24 | Consultas exploratórias de leitura (PostgreSQL v2)
-- Escopo: snapshot importado da Adzuna; não representa o mercado brasileiro.
-- Este arquivo não modifica dados. Execute com psql -f via stdin.

\echo '1. Resumo do dataset e fontes'
SELECT
    (SELECT count(*) FROM jobs) AS vagas,
    (SELECT count(*) FROM job_postings) AS publicacoes,
    (SELECT count(*) FROM companies) AS empresas,
    (SELECT count(*) FROM sources) AS fontes;

\echo '2. Vagas publicadas por empresa (top 10)'
SELECT c.name AS empresa, count(DISTINCT j.job_id) AS vagas
FROM jobs j
JOIN companies c ON c.company_id = j.company_id
GROUP BY c.company_id, c.name
ORDER BY vagas DESC, empresa
LIMIT 10;

\echo '3. Distribuicao de vagas por mes de publicacao'
SELECT to_char(date_trunc('month', published_at AT TIME ZONE 'UTC'), 'YYYY-MM') AS mes_utc,
       count(*) AS vagas
FROM jobs
WHERE published_at IS NOT NULL
GROUP BY date_trunc('month', published_at AT TIME ZONE 'UTC')
ORDER BY mes_utc;

\echo '4. Completude dos campos principais'
SELECT count(*) AS total,
       count(*) FILTER (WHERE description IS NOT NULL AND btrim(description) <> '') AS com_descricao,
       count(*) FILTER (WHERE published_at IS NOT NULL) AS com_data_publicacao,
       count(*) FILTER (WHERE employment_type IS NOT NULL) AS com_tipo_contrato,
       count(*) FILTER (WHERE salary_min IS NOT NULL OR salary_max IS NOT NULL) AS com_algum_salario,
       count(*) FILTER (WHERE work_mode IS NOT NULL) AS com_modalidade
FROM jobs;

\echo '5. Títulos mais frequentes (títulos literais, sem normalização)'
SELECT title AS titulo, count(*) AS vagas
FROM jobs
GROUP BY title
ORDER BY vagas DESC, titulo
LIMIT 15;

\echo '6. Participacao por fonte (conta publicacoes, nao vagas unicas)'
SELECT s.name AS fonte, count(*) AS publicacoes
FROM job_postings p
JOIN sources s ON s.source_id = p.source_id
GROUP BY s.source_id, s.name
ORDER BY publicacoes DESC, fonte;

\echo '7. Verificacao de integridade dos registros importados'
SELECT
    (SELECT count(*) FROM job_postings p LEFT JOIN jobs j ON j.job_id = p.job_id WHERE j.job_id IS NULL) AS publicacoes_sem_vaga,
    (SELECT count(*) FROM jobs j LEFT JOIN companies c ON c.company_id = j.company_id WHERE c.company_id IS NULL) AS vagas_sem_empresa,
    (SELECT count(*) FROM job_postings p LEFT JOIN sources s ON s.source_id = p.source_id WHERE s.source_id IS NULL) AS publicacoes_sem_fonte;

\echo '8. Execucoes auditadas'
SELECT pipeline_run_id, started_at, finished_at, status,
       records_fetched, records_valid, records_rejected
FROM pipeline_runs
ORDER BY started_at DESC, pipeline_run_id DESC
LIMIT 10;
