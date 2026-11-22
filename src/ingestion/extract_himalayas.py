"""CLI for one bounded Himalayas search page."""
from __future__ import annotations

import argparse
import sys

from src.ingestion.himalayas_extractor import (
    HimalayasAPIError,
    extract_jobs,
    write_raw_extraction,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Busca uma página de vagas remotas na Himalayas."
    )
    parser.add_argument("--query", default="data", help="Termo de busca (padrão: data)")
    parser.add_argument("--country", default="BR", help="País ISO alpha-2 (padrão: BR)")
    parser.add_argument("--page", type=int, default=1, help="Página da busca (padrão: 1)")
    parser.add_argument(
        "--exclude-worldwide",
        action="store_true",
        help="Exclui vagas abertas mundialmente do filtro por país.",
    )
    parser.add_argument("--seniority", help="Senioridade suportada pela API")
    parser.add_argument("--employment-type", help="Tipo de contratação suportado pela API")
    parser.add_argument("--output", default="data/raw/himalayas_jobs.json")
    args = parser.parse_args()

    try:
        extraction = extract_jobs(
            query=args.query,
            country=args.country,
            page=args.page,
            exclude_worldwide=args.exclude_worldwide,
            seniority=args.seniority,
            employment_type=args.employment_type,
        )
        write_raw_extraction(extraction, args.output)
    except (HimalayasAPIError, OSError, ValueError) as exc:
        print(f"Falha na extração Himalayas: {exc}", file=sys.stderr)
        return 1

    print(f"Fonte: Himalayas")
    print(f"País solicitado: {extraction['parameters']['country']}")
    print(f"Página recebida: {extraction['parameters']['page']}")
    print(f"Anúncios efetivamente retornados: {extraction['result_count']}")
    print(f"Extraído em UTC: {extraction['extracted_at']}")
    print(f"JSON bruto salvo em: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
