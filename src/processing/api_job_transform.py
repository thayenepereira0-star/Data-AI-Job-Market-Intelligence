"""Normalize supported API job envelopes without accessing PostgreSQL."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from src.processing.job_transform import key


@dataclass(frozen=True)
class NormalizedJob:
    source: str
    external_id: str | None
    title: str
    company: str
    normalized_company: str
    url: str
    description: str | None = None
    published_at: datetime | None = None
    location: str | None = None
    employment_type: str | None = None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (float, int)):
        # API publication timestamps might be Unix milliseconds.
        seconds = value / 1000 if value > 100000000000 else value
        return datetime.fromtimestamp(seconds, tz=__import__("datetime").timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def _format(source: str, item: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    if source == "adzuna":
        company = item.get("company") or {}
        location = item.get("location") or {}
        return dict(title=item.get("title"), company=company.get("display_name") if isinstance(company, dict) else company,
                    url=item.get("redirect_url"), external_id=item.get("id"),
                    description=item.get("description"), published_at=item.get("created"),
                    location=location.get("display_name") if isinstance(location, dict) else location,
                    employment_type=item.get("contract_type"))
    if source == "himalayas":
        company = item.get("companyName") or item.get("company")
        return dict(title=item.get("title"), company=company,
                    url=item.get("applicationLink") or item.get("url"),
                    external_id=item.get("id"), description=item.get("description"),
                    published_at=item.get("pubDate") or item.get("publicationDate"),
                    location=", ".join(map(str, item.get("locationRestrictions") or [])) if isinstance(item.get("locationRestrictions"), list) else None,
                    employment_type=item.get("employmentType"))
    if source == "greenhouse":
        company = envelope.get("parameters", {}).get("board_token")
        location = item.get("location") or {}
        return dict(title=item.get("title"), company=company,
                    url=item.get("absolute_url"), external_id=item.get("id"),
                    description=item.get("content"), published_at=item.get("updated_at"),
                    location=location.get("name") if isinstance(location, dict) else location,
                    employment_type=None)
    if source == "lever":
        cats = item.get("categories") or {}
        return dict(title=item.get("text"), company=envelope.get("parameters", {}).get("site"),
                    url=item.get("hostedUrl") or item.get("applyUrl"), external_id=item.get("id"),
                    description=item.get("descriptionPlain") or item.get("description"),
                    published_at=item.get("createdAt"),
                    location=cats.get("location") if isinstance(cats, dict) else None,
                    employment_type=cats.get("commitment") if isinstance(cats, dict) else None)
    raise ValueError("Fonte não suportada para transformação.")


def _items(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    source = envelope.get("source")
    if source == "adzuna":
        pages = envelope.get("pages")
        if not isinstance(pages, list):
            raise ValueError("Envelope Adzuna sem pages.")
        items = []
        for page in pages:
            if not isinstance(page, dict) or not isinstance(page.get("results"), list):
                raise ValueError("Página Adzuna inválida.")
            items.extend(page["results"])
    elif source in {"himalayas", "greenhouse", "lever"}:
        items = envelope.get("jobs")
        if not isinstance(items, list):
            raise ValueError("Envelope sem jobs.")
    else:
        raise ValueError("Fonte não suportada para transformação.")
    if any(not isinstance(x, dict) for x in items):
        raise ValueError("Anúncio deve ser um objeto JSON.")
    return items


def transform_envelope(envelope: dict[str, Any]) -> tuple[list[NormalizedJob], list[dict[str, Any]]]:
    """Return valid jobs and rejection diagnostics, without saving raw ads."""
    source = envelope.get("source")
    valid: list[NormalizedJob] = []
    rejected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(_items(envelope), 1):
        data = _format(source, item, envelope)
        title, company, url = (_text(data.get(k)) for k in ("title", "company", "url"))
        if not title or not company or not url:
            rejected.append({"index": index, "reason": "título, empresa ou URL ausente"})
            continue
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            rejected.append({"index": index, "reason": "URL inválida"})
            continue
        external_id = _text(data.get("external_id"))
        signature = (source, external_id or url)
        if signature in seen:
            rejected.append({"index": index, "reason": "duplicado na coleta"})
            continue
        seen.add(signature)
        valid.append(NormalizedJob(
            source=source, external_id=external_id, title=title,
            company=company, normalized_company=key(company), url=url,
            description=_text(data.get("description")),
            published_at=_date(data.get("published_at")),
            location=_text(data.get("location")),
            employment_type=_text(data.get("employment_type")),
        ))
    return valid, rejected
