"""DAI-23 — Migração auditável de vagas da v1 para PostgreSQL.

Por padrão apenas valida e apresenta uma prévia. Use --apply para gravar.
O CSV original não é modificado.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlsplit

import psycopg
from dotenv import load_dotenv

from src.database.check_connection import connection_settings

DEFAULT_CSV = Path("data/processed/jobs_analysis.csv")
SOURCE_NAME = "Adzuna"
ID_PATTERN = re.compile(r"/details/(\d+)(?:/|$)")
REQUIRED_FIELDS = {"title", "empresa", "description", "redirect_url"}
REQUIRED_COLUMNS = REQUIRED_FIELDS | {"created", "salary_min", "salary_max", "contract_type"}


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


def read_csv(path: Path) -> tuple[list[Record], list[tuple[int, str]], int]:
    records: list[Record] = []
    rejected: list[tuple[int, str]] = []
    total = 0
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
            raise ValueError(f"CSV fora do esquema da v1; colunas ausentes: {', '.join(missing)}")
        for number, row in enumerate(reader, start=2):
            total += 1
            try:
                records.append(parse_record(row, number))
            except ValueError as exc:
                rejected.append((number, str(exc)))
    return records, rejected, total


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


def apply(records: list[Record], total: int, rejected_count: int) -> tuple[int, int]:
    """Transação completa: nunca criar uma vaga órfã ou importar pela metade."""
    inserted = 0
    skipped = 0
    load_dotenv()
    with psycopg.connect(**connection_settings()) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pipeline_runs (status, records_fetched, records_rejected) "
                    "VALUES ('running', %s, %s) RETURNING pipeline_run_id",
                    (total, rejected_count),
                )
                run_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO sources (name, base_url) VALUES (%s, %s) "
                    "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                    "RETURNING source_id",
                    (SOURCE_NAME, "https://www.adzuna.com.br"),
                )
                source_id = cur.fetchone()[0]
                for record in records:
                    cur.execute(
                        "SELECT 1 FROM job_postings WHERE source_id = %s "
                        "AND (original_url = %s OR external_job_id = %s) LIMIT 1",
                        (source_id, record.url, record.external_id),
                    )
                    if cur.fetchone() is not None:
                        skipped += 1
                        continue
                    cur.execute(
                        "INSERT INTO companies (name, normalized_name) VALUES (%s, %s) "
                        "ON CONFLICT (normalized_name) DO UPDATE SET name = companies.name "
                        "RETURNING company_id",
                        (record.company, record.normalized_company),
                    )
                    company_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO jobs (company_id, title, description, employment_type, "
                        "salary_min, salary_max, published_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING job_id",
                        (company_id, record.title, record.description,
                         record.employment_type, record.salary_min, record.salary_max,
                         record.published_at),
                    )
                    job_id = cur.fetchone()[0]
                    cur.execute(
                        "INSERT INTO job_postings (job_id, source_id, collected_run_id, "
                        "external_job_id, original_url, source_title) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (job_id, source_id, run_id, record.external_id, record.url, record.title),
                    )
                    inserted += 1
                cur.execute(
                    "UPDATE pipeline_runs SET status = %s, finished_at = now(), "
                    "records_valid = %s WHERE pipeline_run_id = %s",
                    ("partial" if rejected_count else "success", inserted, run_id),
                )
    return inserted, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Migração v1 → PostgreSQL: prévia ou gravação")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--apply", action="store_true", help="Grava no PostgreSQL")
    args = parser.parse_args()
    try:
        records, rejected, total = read_csv(args.csv)
        unique, repeated = unique_records(records)
        print(f"Linhas lidas: {total}")
        print(f"Válidas antes de deduplicar: {len(records)}")
        print(f"Duplicadas no CSV: {repeated}")
        print(f"Rejeitadas por validação: {len(rejected)}")
        for line, reason in rejected[:10]:
            print(f"  Linha {line}: {reason}")
        if not args.apply:
            print(f"PRÉVIA: {len(unique)} candidatas à importação; nenhum dado foi gravado.")
            print("Use --apply apenas após revisar esta saída.")
            return 0
        inserted, skipped = apply(unique, total, len(rejected) + repeated)
        print(f"Gravação concluída: {inserted} vagas importadas; {skipped} já existentes.")
        return 0
    except (OSError, ValueError, csv.Error, psycopg.Error) as exc:
        print(f"Não foi possível concluir a migração ({type(exc).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
