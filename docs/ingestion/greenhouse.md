# Greenhouse Job Board API — DAI-64

The connector reads published jobs from selected company board tokens. It is not a global job-search API. The selected initial token is `kunumi`, based on the project POC and a real read-only endpoint check.

## Use

```powershell
python -m src.ingestion.extract_greenhouse --boards kunumi
```

The default filters to postings with explicit Brazil locations. `Remote` alone does not qualify because the API does not establish that an unrestricted remote job accepts candidates in Brazil. Use `--all-locations` to inspect the board without the filter. Full descriptions are excluded by default; `--include-content` requests `content=true`.

To save a raw JSON snapshot, pass both `--output <path>` and `--confirm-local-storage`. The explicit flag is required because public Greenhouse docs describe the Job Board API as raw data for building the company's career pages, and do not provide a blanket grant for third-party analytics retention or redistribution. Keep any approved snapshot private, minimize retention, identify Greenhouse and the board, and do not publish job content. The connector output retains the complete provider JSON in memory for the downstream DAI-29 adapter.

## API behavior and limitations

- GET `/v1/boards/{board_token}/jobs` returns published jobs; `content=true` adds the full description, departments and offices.
- No authentication is required for reading published board jobs. Greenhouse says requests may be rate limited for security and traffic reasons; no fixed public GET quota is specified. This connector queries boards serially and should run at low frequency.
- Board tokens are company-specific and may be renamed or disabled. Maintain an explicit reviewed catalog.
- Brasil coverage depends on selected employers and current openings; this is not a national market census.
- The current location matcher catches explicit Brazil/city labels and intentionally does not infer Brazil eligibility from a generic `Remote` label.
- The real endpoint check on 2026-11-22 used one GET to token `kunumi`: HTTP 200, 6 postings returned, and 6 explicit Brazil-location matches. This is one observed board response, not a stable or complete market count.
- No real response was saved. The storage flag is a guard, not a determination that Greenhouse terms authorize retention.

## Tests and real-call distinction

`tests/test_greenhouse_extractor.py` uses mocked responses and makes no real API calls. The observed count above is from a separate, real GET and must not be confused with the simulated test fixtures.

## Official references

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Greenhouse API overview](https://www.greenhouse.com/api)
