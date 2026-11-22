"""Read-only connector for selected public Lever career sites."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_BASE_URL = "https://api.lever.co/v0/postings"
SOURCE = "lever"
BRAZIL_LOCATION = re.compile(
    r"\b(brazil|brasil|sao paulo|são paulo|rio de janeiro|recife|curitiba|"
    r"belo horizonte|porto alegre|florianopolis|florianópolis|bras[ií]lia|"
    r"fortaleza|salvador|manaus|remote\s*[-–—]?\s*(br|brazil|brasil))\b",
    re.IGNORECASE,
)


class LeverAPIError(RuntimeError):
    """Safe API error without request URL or response body."""


def _validate_site(site: str) -> str:
    site = site.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", site):
        raise ValueError("Site slug inválido.")
    return site


def _fetch_page(
    *, site: str, skip: int, limit: int, timeout: float
) -> list[dict[str, Any]]:
    url = f"{API_BASE_URL}/{site}?{urlencode({'mode': 'json', 'skip': skip, 'limit': limit})}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Data-AI-Job-Market-Intelligence/2.0 (educational research)",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise LeverAPIError(f"Lever respondeu com HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError):
        raise LeverAPIError("Não foi possível conectar à Lever.") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise LeverAPIError("A resposta Lever não contém JSON válido.") from None

    if not isinstance(payload, list) or any(not isinstance(job, dict) for job in payload):
        raise LeverAPIError("Resposta Lever não contém uma lista válida de anúncios.")
    return payload


def is_brazil_compatible(job: dict[str, Any]) -> bool:
    """Match explicit Brazil locations; generic remote is not sufficient."""
    categories = job.get("categories") or {}
    location = categories.get("location", "") if isinstance(categories, dict) else ""
    workplace = job.get("workplaceType", "")
    return bool(BRAZIL_LOCATION.search(f"{location} {workplace}"))


def extract_site_jobs(
    *,
    site: str,
    brazil_only: bool = True,
    first_skip: int = 0,
    limit: int = 100,
    pages: int = 1,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Read a bounded number of pages from one published Lever job site."""
    site_slug = _validate_site(site)
    if not isinstance(brazil_only, bool):
        raise ValueError("brazil_only deve ser booleano.")
    if first_skip < 0 or limit < 1 or pages < 1:
        raise ValueError("first_skip deve ser >= 0; limit e pages devem ser >= 1.")

    raw_pages: list[list[dict[str, Any]]] = []
    all_jobs: list[dict[str, Any]] = []
    for page_index in range(pages):
        skip = first_skip + page_index * limit
        batch = _fetch_page(site=site_slug, skip=skip, limit=limit, timeout=timeout)
        raw_pages.append(batch)
        all_jobs.extend(batch)
        if len(batch) < limit:
            break

    selected = (
        [job for job in all_jobs if is_brazil_compatible(job)]
        if brazil_only
        else all_jobs
    )
    return {
        "source": SOURCE,
        "source_url": f"https://jobs.lever.co/{site_slug}",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "site": site_slug,
            "brazil_only": brazil_only,
            "first_skip": first_skip,
            "limit": limit,
            "pages_requested": pages,
        },
        "jobs": selected,
        "pages": raw_pages,
        "result_count": len(selected),
        "site_result_count": len(all_jobs),
    }


def extract_configured_sites(
    *,
    site_slugs: list[str],
    brazil_only: bool = True,
    limit: int = 100,
    pages: int = 1,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """Fetch the configured career sites sequentially."""
    if not site_slugs:
        raise ValueError("Configure pelo menos um Lever site slug.")
    return [
        extract_site_jobs(
            site=site,
            brazil_only=brazil_only,
            limit=limit,
            pages=pages,
            timeout=timeout,
        )
        for site in site_slugs
    ]


def write_raw_extraction(extraction: dict[str, Any], output_path: str) -> None:
    """Write a private raw snapshot only after source terms are reviewed."""
    from pathlib import Path

    if extraction.get("source") != SOURCE:
        raise ValueError("O envelope não pertence à fonte Lever.")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
