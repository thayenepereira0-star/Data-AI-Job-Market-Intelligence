"""DAI-26: orquestrador ETL da migração v1 → PostgreSQL.

O comando padrão só faz prévia. --apply grava os registros.
Mantém a interface da DAI-23, agora separada em módulos testáveis.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys

import psycopg

from src.ingestion.csv_reader import read_csv
from src.processing.job_transform import unique_records
from src.database.job_loader import apply

DEFAULT_CSV = Path("data/processed/jobs_analysis.csv")

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
