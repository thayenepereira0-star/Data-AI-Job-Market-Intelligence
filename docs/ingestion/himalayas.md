# Himalayas Remote Jobs API — DAI-65

This connector performs one bounded page of the public remote-job search API. It does not call the API at import time and has no database integration. The output envelope preserves the provider response and records the source, UTC extraction time, query parameters, and observed result count.

## Use

```powershell
python -m src.ingestion.extract_himalayas --query "data analyst" --country BR --page 1
```

Add `--exclude-worldwide` when the search should omit jobs open worldwide. The country filter `BR` includes jobs with Brazil among their eligible countries and jobs available worldwide; the worldwide exclusion is configurable. Optional API keys are read from `HIMALAYAS_API_KEY` and are sent only in the Authorization header. The API works without a key, but the unauthenticated rate limit is lower and not numerically specified in the published docs. A key currently receives 60 requests/minute and 10,000/day; limits may change and 429 responses can include Retry-After. One page per command is the default; do not poll more often than daily because the feed refreshes daily.

## Data use and retention

Himalayas permits personal and commercial API integrations without prior approval. Its terms require source attribution when showing listings, prohibit passing listings to third-party job boards/aggregators and require removing expired jobs. The project must keep any use inside an app it operates, retain the original applicationLink if it ever exposes an apply action, cache conservatively, and avoid public redistribution. The connector provides `remove_expired_jobs`; call it before retaining/reusing snapshots and refresh the data daily. Avoid long-term retention of expired listings.

## Coverage and limits

- This is a remote-jobs search index, not a census of Brazilian vacancies.
- `country=BR` is an eligibility filter; it does not guarantee a Brazil-based employer or Portuguese-language role.
- The API's totalCount may be stale by up to a day; use returned `jobs` and page through until an empty page if exhaustive search is ever required. This CLI intentionally requests one page.
- Results can shift between pages; deduplicate by `guid` in later pipeline stages.
- Job posts can close before expiryDate. The source offers a per-job status endpoint (HTTP 410 means remove); validate before displaying cached jobs.
- Greenhouse/Lever coverage is not implied by this connector.

## Tests and real-call distinction

`tests/test_himalayas_extractor.py` uses mocked HTTP responses and makes no real API requests. A separate real GET was observed on 2026-11-22 at 17:56:27 UTC for `country=BR&q=data&page=1`: HTTP 200, 20 jobs returned on page 1. The API also returned `totalCount=1502`; the API documentation says that field is an estimate that can be up to a day old, so it is not a validated market total. The probe did not persist any job data.

## Official references

- [API docs and rate limits](https://himalayas.app/api)
- [API user terms](https://himalayas.app/terms)
