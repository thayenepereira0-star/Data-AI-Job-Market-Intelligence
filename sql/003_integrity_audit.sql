-- DAI-25: read-only PostgreSQL integrity and duplicate audit
-- Run on the existing jobmarket database. Expected 0 for violation counts.
\set ON_ERROR_STOP on

\echo '1. Table row counts'
SELECT 'companies' AS table_name, count(*) AS rows FROM companies
UNION ALL SELECT 'sources', count(*) FROM sources
UNION ALL SELECT 'jobs', count(*) FROM jobs
UNION ALL SELECT 'job_postings', count(*) FROM job_postings
UNION ALL SELECT 'skills', count(*) FROM skills
UNION ALL SELECT 'job_skills', count(*) FROM job_skills
UNION ALL SELECT 'pipeline_runs', count(*) FROM pipeline_runs
ORDER BY table_name;

\echo '2. Foreign key constraints declared in the database'
SELECT conrelid::regclass AS from_table, conname AS constraint_name,
       confrelid::regclass AS to_table
FROM pg_constraint
WHERE contype = 'f' AND connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, conname;

\echo '3. Orphan records and unexpected missing links (expected zero)'
SELECT
 (SELECT count(*) FROM jobs j LEFT JOIN companies c ON c.company_id = j.company_id WHERE c.company_id IS NULL) AS jobs_without_company,
 (SELECT count(*) FROM job_postings p LEFT JOIN jobs j ON j.job_id = p.job_id WHERE j.job_id IS NULL) AS postings_without_job,
 (SELECT count(*) FROM job_postings p LEFT JOIN sources s ON s.source_id = p.source_id WHERE s.source_id IS NULL) AS postings_without_source,
 (SELECT count(*) FROM job_postings p LEFT JOIN pipeline_runs r ON r.pipeline_run_id = p.collected_run_id WHERE p.collected_run_id IS NOT NULL AND r.pipeline_run_id IS NULL) AS postings_with_invalid_run,
 (SELECT count(*) FROM job_skills js LEFT JOIN jobs j ON j.job_id = js.job_id WHERE j.job_id IS NULL) AS job_skills_without_job,
 (SELECT count(*) FROM job_skills js LEFT JOIN skills s ON s.skill_id = js.skill_id WHERE s.skill_id IS NULL) AS job_skills_without_skill;

\echo '4. Exact duplicate postings by source and external ID (expected zero)'
SELECT count(*) AS duplicated_external_id_groups
FROM (
 SELECT source_id, external_job_id
 FROM job_postings WHERE external_job_id IS NOT NULL
 GROUP BY source_id, external_job_id HAVING count(*) > 1
) duplicates;

\echo '5. Exact duplicate postings by source and URL (expected zero)'
SELECT count(*) AS duplicated_source_url_groups
FROM (
 SELECT source_id, original_url
 FROM job_postings
 GROUP BY source_id, original_url HAVING count(*) > 1
) duplicates;

\echo '6. Duplicate company and skill normalized keys (expected zero)'
SELECT
 (SELECT count(*) FROM (
    SELECT normalized_name FROM companies GROUP BY normalized_name HAVING count(*) > 1
 ) d) AS duplicated_company_keys,
 (SELECT count(*) FROM (
    SELECT normalized_name FROM skills GROUP BY normalized_name HAVING count(*) > 1
 ) d) AS duplicated_skill_keys;

\echo '7. Business-rule anomalies (expected zero)'
SELECT
 (SELECT count(*) FROM jobs WHERE title IS NULL OR btrim(title) = '') AS blank_job_titles,
 (SELECT count(*) FROM companies WHERE btrim(name) = '' OR btrim(normalized_name) = '') AS blank_company_names,
 (SELECT count(*) FROM job_postings WHERE original_url IS NULL OR btrim(original_url) = '') AS blank_posting_urls,
 (SELECT count(*) FROM jobs WHERE salary_min > salary_max) AS inverted_salary_ranges,
 (SELECT count(*) FROM job_postings WHERE last_seen_at < first_seen_at) AS inverted_seen_dates,
 (SELECT count(*) FROM pipeline_runs WHERE finished_at < started_at) AS inverted_run_dates;

\echo '8. Jobs without publications (informational, not always invalid)'
SELECT count(*) AS jobs_without_postings
FROM jobs j LEFT JOIN job_postings p ON p.job_id = j.job_id
WHERE p.posting_id IS NULL;

\echo '9. Expected uniqueness safeguards: installed indexes'
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'uq_job_postings_external', 'uq_job_postings_source_url',
    'uq_companies_normalized_name', 'skills_normalized_name_key'
  )
ORDER BY tablename, indexname;

\echo '10. Duplicate-looking opportunities by company and exact title (review only)'
SELECT c.name AS company, j.title AS title, count(*) AS jobs
FROM jobs j
JOIN companies c ON c.company_id = j.company_id
GROUP BY c.company_id, c.name, j.title
HAVING count(*) > 1
ORDER BY jobs DESC, company, title
LIMIT 15;
