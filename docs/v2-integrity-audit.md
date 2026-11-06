# DAI-25 — Audit the PostgreSQL database integrity

This step extends the earlier SQL checks. The queries are **read-only**: no inserts, updates, deletes or schema changes. It audits the actual loaded data and the declared key constraints.

## Run from VS Code PowerShell

First switch to the branch containing this audit and ensure Docker Desktop is running.

```powershell
git fetch origin
git switch feat/dai-25-integrity-audit
docker compose ps
```

Run the SQL script:

```powershell
Get-Content -Raw .\sql\003_integrity_audit.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U jobmarket -d jobmarket
```

## How to read the results

1. Counts of all seven tables. After the DAI-23 migration, `jobs=127`, `job_postings=127`, `companies=82`; `pipeline_runs` is expected to contain at least the two demonstrated migration executions. The other tables may be empty.
2. The schema should list **six foreign keys** (`jobs → companies`, three from `job_postings`, two from `job_skills`).
3. All orphan counts should be zero. A posting with `collected_run_id=NULL` is allowed; invalid non-null references are not.
4–6. Exact duplicated source+external IDs, source+URLs and normalized company/skill keys should be zero.
7. Blank required fields and inverted ranges should be zero.
8. Jobs without a publication are shown for investigation: this is informational and could be legitimate in future data workflows.
9. Unique indexes should be present (names can vary for auto-generated constraints). Do not assume the listed results exhaust every possible unique constraint.
10. Same company + exact title occurring multiple times indicates possible duplicate **candidates**, not proven duplicate opportunities. Do not merge automatically; different locations or dates may reflect different jobs.

## Notes and limitations

- The 127 imported records all originate from the v1 Adzuna analytic sample. These results cannot be generalized to the Brazilian job market.
- A zero anomaly count is **not proof of overall data quality**; truncated descriptions, missing work mode, salary conventions, synonym companies and semantic duplicate postings still require further work.
- The last SQL query is deliberately a **review list**, not a failure condition.
- The original CSV remains unchanged. No credentials appear in SQL or documentation.

## Done criteria

- [x] Read-only audit SQL and interpretation guide versioned.
- [x] Run the SQL against local PostgreSQL and inspect the output.
- [x] Document observed anomalies and confirm expected constraints.
- [ ] Review and merge the PR after validation.

## Local audit results — 2026-11-06

Evidence: successful PowerShell/psql output supplied by the developer (the assistant did not execute commands on the local PostgreSQL instance).

- Row counts: companies 82; job_postings 127; job_skills 0; jobs 127; pipeline_runs 2; skills 0; sources 1.
- Six declared foreign keys verified in `pg_constraint`.
- Orphan/invalid references: all six checks returned **0**.
- Exact duplicate groups by (source, external ID): **0**; by (source, original URL): **0**.
- Duplicate normalized company and skill keys: **0** each.
- Blank titles/company names/URLs, inverted salary ranges and inverted timestamps: all **0**.
- Jobs with no publication: **0**.
- Four expected unique indexes identified, including partial unique index for non-null external IDs.
- Eight **groups of duplicate-looking jobs** (same company and exact title) were flagged for potential human review: BEES Intermediate Data Analyst (3); AB InBev Intermediate Data Analyst (2); AB InBev Intermediate Data Engineer (2); AB InBev Senior Data Analyst (2); AB InBev Senior Data Engineer (2); BEES Intermediate Data Engineer (2); BEES Senior Data Analyst (2); BEES Senior Data Engineer (2).

**Interpretation:** these are not confirmed duplicates; identical company/title can represent distinct opportunities. Keep all until independent identifiers, description, time and location are reviewed. The empty `skills`/`job_skills` tables have not yet been tested with real records. The checks cover the specified structural rules, not comprehensive semantic data quality.
