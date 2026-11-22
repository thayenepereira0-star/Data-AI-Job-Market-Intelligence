"""Read-only, aggregated snapshot of historical PostgreSQL rows.

Never prints connection details, job text, URLs or passwords.
"""
from __future__ import annotations

import json
import psycopg
from src.config import connection_settings


def snapshot() -> dict:
    with psycopg.connect(**connection_settings()) as conn:
        # Prevent a read-only diagnostics command from modifying the database.
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            tables = {}
            for name in ("sources", "companies", "jobs", "job_postings", "pipeline_runs", "skills", "job_skills"):
                cur.execute(f"SELECT COUNT(*) FROM {name}")
                tables[name] = cur.fetchone()[0]
            cur.execute(
                "SELECT sources.name, COUNT(*) FROM job_postings "
                "JOIN sources ON sources.source_id = job_postings.source_id "
                "GROUP BY sources.name ORDER BY sources.name"
            )
            per_source = {name: count for name, count in cur.fetchall()}
            cur.execute(
                "SELECT COUNT(*) FROM (SELECT source_id, original_url FROM job_postings "
                "GROUP BY source_id, original_url HAVING COUNT(*) > 1) AS duplicate_urls"
            )
            duplicates = cur.fetchone()[0]
    return {
        "mode": "read_only",
        "tables": tables,
        "postings_by_source": per_source,
        "duplicate_source_url_groups": duplicates,
    }


def main() -> None:
    try:
        report = snapshot()
    except (psycopg.Error, ValueError) as exc:
        # Never expose database connection parameters or credentials.
        raise SystemExit(f"Diagnóstico não concluído: {type(exc).__name__}") from None
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
