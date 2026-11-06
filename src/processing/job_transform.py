"""Transforma e valida linhas do dataset de vagas da v1, sem acesso ao banco."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import unicodedata
from urllib.parse import urlsplit

ID_PATTERN = re.compile(r"/details/(\d+)(?:/|$)")

@dataclass(frozen=True)
class Record:
    row_number: int
    title: str
    company: str
    normalized_company: str
    description: str | None
    url: str
    external_id: str | None
    published_at: datetime | None
    location: str | None
    employment_type: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None


def clean(value: str | None) -> str | None:
    text = (value or "").strip()
    return text if text and text.casefold() not in {"unknown", "não informado", "nao informado", "nan", "none", "null"} else None


def key(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(c for c in folded if not unicodedata.combining(c))
    return " ".join(ascii_text.casefold().split())


def parse_number(value: str | None) -> Decimal | None:
    text = clean(value)
    if text is None:
        return None
    try:
        number = Decimal(text)
        if not number.is_finite() or number < 0:
            raise ValueError("salário negativo ou inválido")
        return number
    except InvalidOperation as exc:
        raise ValueError("salário não numérico") from exc


def parse_date(value: str | None) -> datetime | None:
    text = clean(value)
    if text is None:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("data de publicação inválida") from exc


def parse_record(row: dict[str, str], row_number: int) -> Record:
    title = clean(row.get("title"))
    company = clean(row.get("empresa"))
    url = clean(row.get("redirect_url"))
    if not title or not company or not url:
        raise ValueError("título, empresa ou URL ausente")
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL inválida")
    # Não transformar um link genérico em identificador externo fictício.
    match = ID_PATTERN.search(parsed.path)
    lower = parse_number(row.get("salary_min"))
    upper = parse_number(row.get("salary_max"))
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("faixa salarial invertida")
    return Record(
        row_number=row_number,
        title=title,
        company=company,
        normalized_company=key(company),
        description=clean(row.get("description")),
        url=url,  # Preserva link da origem, sem inventar redirecionamentos.
        external_id=match.group(1) if match else None,
        published_at=parse_date(row.get("created")),
        location=clean(row.get("localizacao")),
        employment_type=clean(row.get("contract_type")),
        salary_min=lower,
        salary_max=upper,
    )


def unique_records(records: list[Record]) -> tuple[list[Record], int]:
    seen: set[tuple[str, str]] = set()
    unique: list[Record] = []
    duplicates = 0
    for item in records:
        identity = ("id", item.external_id) if item.external_id else ("url", item.url)
        if identity in seen or ("url", item.url) in seen:
            duplicates += 1
            continue
        seen.add(identity)
        seen.add(("url", item.url))
        unique.append(item)
    return unique, duplicates


