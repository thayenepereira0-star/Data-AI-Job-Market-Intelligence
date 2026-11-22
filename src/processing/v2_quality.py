"""Read-only V2 data quality statistics.

The output intentionally contains no job titles, URLs, raw descriptions or keys.
Potential duplicates across providers are candidates, not confirmed matches.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

from src.processing.api_job_transform import NormalizedJob
from src.processing.job_transform import key


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host + port, path, "", ""))


def analyze_quality(records: Iterable[NormalizedJob], rejected_by_source: dict[str, list[dict]]) -> dict:
    jobs = list(records)
    urls: dict[str, list[NormalizedJob]] = defaultdict(list)
    roles: dict[tuple[str, str], list[NormalizedJob]] = defaultdict(list)
    for job in jobs:
        urls[_canonical_url(job.url)].append(job)
        roles[(key(job.company), key(job.title))].append(job)

    # Ignore same-provider duplicates in this report; they are handled upstream.
    repeated_urls = [group for group in urls.values() if len({j.source for j in group}) > 1]
    repeated_roles = [group for group in roles.values() if len({j.source for j in group}) > 1]

    return {
        "scope": "current_run_only",
        "valid_input_count": len(jobs),
        "rejections": {
            source: dict(sorted(Counter(row.get("reason", "motivo não informado") for row in rows).items()))
            for source, rows in sorted(rejected_by_source.items())
        },
        "cross_source_same_url_groups": len(repeated_urls),
        "cross_source_same_url_records": sum(len(group) for group in repeated_urls),
        "cross_source_same_company_title_groups": len(repeated_roles),
        "cross_source_same_company_title_records": sum(len(group) for group in repeated_roles),
        "caution": "Company+title suggests review only, not proven duplicate. No database history compared.",
    }
