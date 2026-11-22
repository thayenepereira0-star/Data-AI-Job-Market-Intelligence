# Lever Postings API — DAI-67

The connector reads published posts from selected company career sites. It is not a global job search service. Initial site slug: `ciandt`, from the existing POC and a real read-only endpoint check.

## Use

```powershell
python -m src.ingestion.extract_lever --sites ciandt --limit 100 --pages 1
```

The default filters explicit Brazil/city locations. Generic `Remote` is not treated as Brazil-eligible. Pagination uses `skip` and `limit`; one page is the default. Full text search is not available, so the connector queries configured sites then filters location fields locally.

To save a raw JSON snapshot, pass both `--output <path>` and `--confirm-local-storage`. Lever's public docs say published jobs can be viewed on Lever-hosted pages and may be scraped by third parties, while the Postings API is documented for building a custom career site. The docs do not provide a general analytics-retention license for third-party site slugs; do not redistribute content. Keep approved snapshots private and short-lived. Raw pages remain available in the in-memory envelope for downstream DAI-29.

## API behavior and limitations

- GET `/v0/postings/{site}?mode=json&skip=X&limit=Y` returns published jobs; no authentication is needed for GET.
- Lever does not document a numerical rate limit for listing GET requests. The 2 application POST requests/second limit applies to job applications and does not apply to this read-only connector. This connector runs requests sequentially.
- The API is company/site-scoped and does not provide full-text search across all employers.
- Brazil coverage depends on the selected career pages and current postings, not the whole Brazilian market.
- Location matching uses explicit Brazil/city labels; a generic `Remote` label is not assumed to include Brazil.
- Real endpoint check on 2026-11-22: one GET to `ciandt` with `limit=100` returned 100 postings in that response page, of which 76 had explicit Brazil/city location strings. This is a bounded sample of the first page, not a stable or complete count.
- No live response was saved. The storage confirmation flag requires a separate review and does not establish permission by itself.

## Tests and real-call distinction

`tests/test_lever_extractor.py` uses mocked responses and makes no real API calls. The observed count above came from a separate live GET and must not be confused with test fixtures.

## Official references

- [Lever Postings API documentation](https://github.com/Lever/postings-api)
- [Lever Postings API credentials and job feeds](https://help.lever.co/s/article/Generating-and-using-API-credentials)
