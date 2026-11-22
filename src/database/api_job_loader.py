"""Incremental, source-aware PostgreSQL loader for normalized API jobs.

Never stores ads unless the caller explicitly approves a source for persistence.
No schema migration and no destructive statements.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

import psycopg

from src.config import connection_settings
from src.processing.api_job_transform import NormalizedJob

# Existing DAI-23 data uses the exact case-sensitive source name "Adzuna".
# Reuse it to avoid importing the same source as a separate provider.
SOURCE_DB_NAMES = {
    "adzuna": "Adzuna",
    "himalayas": "Himalayas",
    "greenhouse": "Greenhouse",
    "lever": "Lever",
}

BASE_URLS = {
    "adzuna": "https://www.adzuna.com.br",
    "himalayas": "https://himalayas.app",
    "greenhouse": "https://boards.greenhouse.io",
    "lever": "https://jobs.lever.co",
}


def preview(records: Iterable[NormalizedJob]) -> dict[str, int]:
    """Read-only, database-free count by source."""
    return dict(sorted(Counter(record.source for record in records).items()))


def apply_incremental(
    records: list[NormalizedJob],
    *,
    approved_sources: set[str],
    rejected_count: int = 0,
) -> dict[str, int]:
    """Insert only explicitly approved sources, atomically and idempotently.

    A source approval must reflect independently reviewed terms of storage,
    redistribution, retention, and permitted processing. No source is approved
    by default. The caller must never treat HTTP access as storage permission.
    """
    if not approved_sources:
        raise ValueError("Nenhuma fonte aprovada para armazenamento.")
    if rejected_count < 0:
        raise ValueError("rejected_count inválido.")
    unknown = {row.source for row in records} - set(BASE_URLS)
    if unknown:
        raise ValueError("Fonte desconhecida no lote.")
    not_approved = {row.source for row in records} - approved_sources
    if not_approved:
        raise ValueError("Lote contém fonte sem permissão de armazenamento.")
    inserted = 0
    existing = 0
    # One transaction for the entire batch; any exception rolls it back.
    with psycopg.connect(**connection_settings()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pipeline_runs (status, records_fetched, records_rejected) "
                "VALUES ('running', %s, %s) RETURNING pipeline_run_id",
                (len(records) + rejected_count, rejected_count),
            )
            run_id = cur.fetchone()[0]
            source_ids: dict[str, int] = {}
            for record in records:
                if record.source not in source_ids:
                    cur.execute(
                        "INSERT INTO sources(name, base_url) VALUES (%s, %s) "
                        "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                        "RETURNING source_id",
                        (SOURCE_DB_NAMES[record.source], BASE_URLS[record.source]),
                    )
                    source_ids[record.source] = cur.fetchone()[0]
                source_id = source_ids[record.source]
                # Avoid OR + NULL pitfalls. Both checks are source-scoped.
                cur.execute(
                    "SELECT 1 FROM job_postings "
                    "WHERE source_id = %s AND "
                    "(original_url = %s OR (external_job_id IS NOT NULL AND external_job_id = %s)) "
                    "LIMIT 1",
                    (source_id, record.url, record.external_id),
                )
                if cur.fetchone() is not None:
                    existing += 1
                    continue
                cur.execute(
                    "INSERT INTO companies(name, normalized_name) VALUES (%s, %s) "
                    "ON CONFLICT (normalized_name) DO UPDATE SET name = companies.name "
                    "RETURNING company_id",
                    (record.company, record.normalized_company),
                )
                company_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO jobs(company_id, title, description, employment_type, published_at) "
                    "VALUES (%s, %s, %s, %s, %s) RETURNING job_id",
                    (company_id, record.title, record.description,
                     record.employment_type, record.published_at),
                )
                job_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO job_postings(job_id, source_id, collected_run_id, "
                    "external_job_id, original_url, source_title) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (job_id, source_id, run_id, record.external_id, record.url, record.title),
                )
                inserted += 1
            cur.execute(
                "UPDATE pipeline_runs SET status = %s, finished_at = now(), "
                "records_valid = %s WHERE pipeline_run_id = %s",
                ("partial" if rejected_count else "success", len(records), run_id),
            )
        # Implicit commit only when all statements succeeded.
    return {"inserted": inserted, "already_present": existing,
            "valid": len(records), "rejected": rejected_count}
