"""Read-only historical data-quality and descriptive indicators for V2.

This command reads the existing PostgreSQL history; it never captures
new advertisements, persists results, or prints job descriptions/URLs.
"""
from __future__ import annotations

import json
import psycopg

from src.config import connection_settings


def profile() -> dict:
    with psycopg.connect(**connection_settings()) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")

            cur.execute("""
                SELECT count(*) AS total,
                    count(*) FILTER (WHERE description IS NULL OR btrim(description) = '') AS no_description,
                    count(*) FILTER (WHERE published_at IS NULL) AS no_publication_date,
                    count(*) FILTER (WHERE employment_type IS NULL OR btrim(employment_type) = '') AS no_employment_type,
                    count(*) FILTER (WHERE work_mode IS NULL) AS no_work_mode,
                    count(*) FILTER (WHERE salary_min IS NULL AND salary_max IS NULL AND
                                          (salary_text IS NULL OR btrim(salary_text) = '')) AS no_salary,
                    count(*) FILTER (WHERE published_at > now()) AS future_publication_dates
                FROM jobs
            """)
            row = cur.fetchone()
            completeness = dict(zip(
                ("total", "missing_description", "missing_published_at",
                 "missing_employment_type", "missing_work_mode",
                 "missing_salary", "future_publication_dates"), row
            ))

            cur.execute("""
                SELECT to_char(date_trunc('month', published_at AT TIME ZONE 'UTC'), 'YYYY-MM'),
                       count(*)
                FROM jobs WHERE published_at IS NOT NULL
                GROUP BY 1 ORDER BY 1
            """)
            by_month = [{"month_utc": month, "jobs": count} for month, count in cur.fetchall()]

            cur.execute("""
                SELECT c.name, count(DISTINCT j.job_id) AS total
                FROM jobs j JOIN companies c ON c.company_id = j.company_id
                GROUP BY c.company_id, c.name
                ORDER BY total DESC, c.name LIMIT 10
            """)
            top_companies = [{"company": company, "jobs": count} for company, count in cur.fetchall()]

            cur.execute("""
                SELECT s.name, count(*)
                FROM job_postings p JOIN sources s ON s.source_id = p.source_id
                GROUP BY s.source_id, s.name ORDER BY s.name
            """)
            postings_by_source = {source: count for source, count in cur.fetchall()}

            cur.execute("""
                SELECT count(*) FROM (
                    SELECT j.company_id, lower(btrim(j.title))
                    FROM jobs j GROUP BY j.company_id, lower(btrim(j.title))
                    HAVING count(*) > 1
                ) candidates
            """)
            same_company_title_groups = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*) FROM jobs j
                LEFT JOIN job_postings p ON p.job_id = j.job_id
                WHERE p.posting_id IS NULL
            """)
            jobs_without_postings = cur.fetchone()[0]

    return {
        "mode": "read_only",
        "scope": "historical_database_only",
        "completeness": completeness,
        "jobs_by_publication_month_utc": by_month,
        "top_companies": top_companies,
        "postings_by_source": postings_by_source,
        "review_candidates": {
            "same_company_normalized_title_groups": same_company_title_groups,
            "jobs_without_postings": jobs_without_postings,
        },
        "caution": "Descriptive sample only; does not represent all Brazilian vacancies. "
                   "Company+title is not a confirmed duplicate. No live API collection included.",
    }


def main() -> None:
    try:
        result = profile()
    except (psycopg.Error, ValueError):
        raise SystemExit("Análise não concluída; confira a conexão local com o PostgreSQL.") from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
