# Extração multissource — DAI-66

The orchestrator runs only configured connectors, one at a time. Each source produces an isolated status, observed result count, duration, timestamp and parameters. A failed source is recorded by exception type; the remaining sources continue. Successful envelopes keep each connector's raw response available to DAI-29.

## Run

```powershell
python -m src.ingestion.run_multisource --sources himalayas --query "data analyst" --country BR
python -m src.ingestion.run_multisource --sources greenhouse --greenhouse-boards kunumi
python -m src.ingestion.run_multisource --sources lever --lever-sites ciandt
```

The first command does not write raw data. For local persistence, use `--persist-raw --approved-storage-sources <comma-separated-sources>`. This explicit allowlist must contain only sources whose current terms and project retention policy were reviewed. Files include the source extraction envelope and are written as `{source}_{run_id}.json`. Do not commit raw snapshots.

## Storage policy

- Himalayas allows API integrations and instructs users to cache where possible and remove expired jobs. Refresh daily, call the connector's expiry cleanup before storing and do not redistribute job listings to third-party aggregators.
- The Greenhouse Job Board API docs describe its public jobs data for building the company's career pages and warn that requests may be rate limited. The docs do not clearly grant external analytics retention or redistribution. CLI defaults to no file writes; review terms or obtain authorization before enabling storage.
- Lever docs describe the Postings API for a custom career site and state published listings are public and may be scraped. They do not grant a general analytics-retention license. CLI defaults to no file writes; review terms or obtain authorization before enabling storage.
- Adzuna credentials remain local. Observe attribution and account limits; do not log keys or include them in provenance.

The orchestrator intentionally does not default Greenhouse/Lever into the persistence allowlist. Results remain available in memory to the immediate caller; use only permitted sources for durable raw snapshots. This enforces the project rule to verify terms before persistence.

## Run metrics and behavior

- Counts come from actual returned envelopes. No API estimated `totalCount` is treated as extracted count.
- Failures are isolated and sanitized; errors do not include full request URLs, response bodies, or credentials.
- Runs are sequential and have no retry loop; respect provider limits and `Retry-After`.
- Connectors are injected into `run_sources`, so orchestration tests make no external API calls.
- This is an extraction boundary for DAI-29. It does not normalize job fields, write PostgreSQL, deduplicate across sources, call AI, or build dashboards.

## Test distinction

`tests/test_orchestrator.py` uses simulated local callables and does not contact any provider. Provider-level mocked tests remain in their own test modules.
