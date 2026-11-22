"""Read-only connector for Himalayas' Remote Jobs search API.

No network call is made at import time. Raw responses are kept inside an
envelope carrying source, timestamp, and query parameters.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://himalayas.app/jobs/api/search"
SOURCE = "himalayas"


class HimalayasAPIError(RuntimeError):
    """Safe API error that does not expose URLs or authorization values."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate(
    *, query: str | None, country: str, page: int, exclude_worldwide: bool
) -> None:
    if query is not None and not query.strip():
        raise ValueError("q deve ser omitido ou conter um termo.")
    if not country.strip():
        raise ValueError("country não pode ser vazio.")
    if page < 1:
        raise ValueError("page deve ser maior ou igual a 1.")
    if not isinstance(exclude_worldwide, bool):
        raise ValueError("exclude_worldwide deve ser booleano.")


def _request_json(
    *, params: dict[str, str], timeout: float, api_key: str | None
) -> dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "Data-AI-Job-Market-Intelligence/2.0 (educational research)",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(f"{API_URL}?{urlencode(params)}", headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        detail = f"HTTP {exc.code}"
        if retry_after:
            detail += f" (Retry-After: {retry_after})"
        raise HimalayasAPIError(f"A Himalayas respondeu com {detail}.") from None
    except (URLError, TimeoutError, OSError):
        raise HimalayasAPIError("Não foi possível conectar à API Himalayas.") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HimalayasAPIError("A resposta da Himalayas não contém JSON válido.") from None

    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise HimalayasAPIError("Resposta da Himalayas sem a lista 'jobs'.")
    if any(not isinstance(job, dict) for job in data["jobs"]):
        raise HimalayasAPIError("Resposta da Himalayas contém vaga em formato inválido.")
    return data


def extract_jobs(
    *,
    query: str | None = None,
    country: str = "BR",
    page: int = 1,
    exclude_worldwide: bool = False,
    seniority: str | None = None,
    employment_type: str | None = None,
    company: str | None = None,
    timezone_filter: str | None = None,
    sort: str | None = None,
    timeout: float = 15.0,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Fetch one page of remote jobs eligible for a country.

    The API's country filter includes jobs marked worldwide. Set
    exclude_worldwide=True when worldwide listings should be omitted.
    """
    _validate(
        query=query,
        country=country,
        page=page,
        exclude_worldwide=exclude_worldwide,
    )
    params: dict[str, str] = {"country": country.strip().upper(), "page": str(page)}
    if query and query.strip():
        params["q"] = query.strip()
    if exclude_worldwide:
        params["exclude_worldwide"] = "true"
    for name, value in (
        ("seniority", seniority),
        ("employment_type", employment_type),
        ("company", company),
        ("timezone", timezone_filter),
        ("sort", sort),
    ):
        if value and value.strip():
            params[name] = value.strip()

    key = api_key or os.getenv("HIMALAYAS_API_KEY", "").strip() or None
    payload = _request_json(params=params, timeout=timeout, api_key=key)
    return {
        "source": SOURCE,
        "extracted_at": _utc_now().isoformat(),
        "parameters": {
            "query": query.strip() if query and query.strip() else None,
            "country": country.strip().upper(),
            "page": page,
            "exclude_worldwide": exclude_worldwide,
            "seniority": seniority.strip() if seniority and seniority.strip() else None,
            "employment_type": (
                employment_type.strip()
                if employment_type and employment_type.strip()
                else None
            ),
            "company": company.strip() if company and company.strip() else None,
            "timezone": (
                timezone_filter.strip()
                if timezone_filter and timezone_filter.strip()
                else None
            ),
            "sort": sort.strip() if sort and sort.strip() else None,
        },
        "jobs": payload["jobs"],
        "raw_response": payload,
        "result_count": len(payload["jobs"]),
    }


def write_raw_extraction(extraction: dict[str, Any], output_path: str) -> None:
    """Write a local raw snapshot; never include API credentials in the file."""
    from pathlib import Path

    if extraction.get("source") != SOURCE:
        raise ValueError("O envelope não pertence à fonte Himalayas.")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def remove_expired_jobs(
    extraction: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Return a copy without jobs whose Himalayas expiryDate has passed.

    expiryDate is a Unix timestamp. Jobs without a date are retained because
    absence of expiry metadata is not evidence that a posting is closed.
    """
    cleaned = deepcopy(extraction)
    current = (now or _utc_now()).timestamp()

    def active(job: Any) -> bool:
        if not isinstance(job, dict):
            return False
        expiry = job.get("expiryDate")
        try:
            return expiry is None or float(expiry) > current
        except (TypeError, ValueError):
            return True

    cleaned["jobs"] = [job for job in cleaned.get("jobs", []) if active(job)]
    raw = cleaned.get("raw_response")
    if isinstance(raw, dict) and isinstance(raw.get("jobs"), list):
        raw["jobs"] = [job for job in raw["jobs"] if active(job)]
    cleaned["result_count"] = len(cleaned["jobs"])
    return cleaned
