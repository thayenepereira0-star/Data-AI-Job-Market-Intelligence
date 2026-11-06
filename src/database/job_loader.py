"""Persiste oportunidades e publicações com integridade transacional no PostgreSQL."""
from __future__ import annotations

import psycopg
from dotenv import load_dotenv

from src.database.check_connection import connection_settings
from src.processing.job_transform import Record

SOURCE_NAME = "Adzuna"

def apply(records: list[Record], total: int, rejected_count: int) -> tuple[int, int]:
    """Transação completa: nunca criar uma vaga órfã ou importar pela metade."""
    inserted = 0
    skipped = 0
    load_dotenv()
    with psycopg.connect(**connection_settings()) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pipeline_runs (status, records_fetched, records_rejected) "
                    "VALUES ('running', %s, %s) RETURNING pipeline_run_id",
                    (total, rejected_count),
                )
                run_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO sources (name, base_url) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                    "RETURNING source_id",
                    (SOURCE_NAME, "https://www.adzuna.com.br"),
                )
                source_id = cur.fetchone()[0]
                for record in records:
                    cur.execute(
                        "SELECT 1 FROM job_postings WHERE source_id = %s "
                        "AND (original_url = %s OR external_job_id = %s) LIMIT 1",
                        (source_id, record.url, record.external_id),
                    )
                    if cur.fetchone() is not None:
                        skipped += 1
                        continue
                    cur.execute(
                        "INSERT INTO companies (name, normalized_name) VALUES (%s, %s) "
                        "ON CONFLICT (normalized_name) DO UPDATE SET name = companies.name "
                        "RETURNING company_id",
                        (record.company, record.normalized_company),
                    )
                    company_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO jobs (company_id, title, description, employment_type, "
                        "salary_min, salary_max, published_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING job_id",
                        (company_id, record.title, record.description,
                         record.employment_type, record.salary_min, record.salary_max,
                         record.published_at),
                    )
                    job_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO job_postings (job_id, source_id, collected_run_id, "
                        "external_job_id, original_url, source_title) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (job_id, source_id, run_id, record.external_id, record.url, record.title),
                    )
                    inserted += 1
                cur.execute(
                    "UPDATE pipeline_runs SET status = %s, finished_at = now(), "
                    "records_valid = %s WHERE pipeline_run_id = %s",
                    ("partial" if rejected_count else "success", inserted, run_id),
                )
    return inserted, skipped


