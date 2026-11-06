"""Extrai linhas de um CSV versionado, aplicando validação por registro."""
from __future__ import annotations

import csv
from pathlib import Path

from src.processing.job_transform import Record, parse_record

REQUIRED_FIELDS = {"title", "empresa", "description", "redirect_url"}
REQUIRED_COLUMNS = REQUIRED_FIELDS | {"created", "salary_min", "salary_max", "contract_type"}

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


