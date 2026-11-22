"""CLI para executar a extração bruta da Adzuna."""
from __future__ import annotations

import argparse
import sys

from src.ingestion.adzuna_extractor import (
    AdzunaAPIError,
    extract_jobs,
    write_raw_extraction,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extrai anúncios brutos da API Adzuna para JSON local."
    )
    parser.add_argument("--what", required=True, help="Termos de busca, por exemplo: data analyst")
    parser.add_argument("--where", help="Localidade opcional, por exemplo: Rio de Janeiro")
    parser.add_argument("--country", default="br", help="Código do país (padrão: br)")
    parser.add_argument("--first-page", type=int, default=1, help="Primeira página (padrão: 1)")
    parser.add_argument("--pages", type=int, default=1, help="Quantidade máxima de páginas (padrão: 1)")
    parser.add_argument(
        "--results-per-page",
        type=int,
        default=20,
        help="Anúncios solicitados por página (padrão: 20)",
    )
    parser.add_argument(
        "--output",
        default="data/raw/adzuna_jobs.json",
        help="Arquivo JSON de saída (padrão: data/raw/adzuna_jobs.json)",
    )
    args = parser.parse_args()

    try:
        extraction = extract_jobs(
            what=args.what,
            where=args.where,
            country=args.country.lower(),
            first_page=args.first_page,
            pages=args.pages,
            results_per_page=args.results_per_page,
        )
        write_raw_extraction(extraction, args.output)
    except (AdzunaAPIError, OSError, ValueError) as exc:
        print(f"Falha na extração: {exc}", file=sys.stderr)
        return 1

    fetched_pages = len(extraction["pages"])
    fetched_jobs = sum(len(page["results"]) for page in extraction["pages"])
    print(f"Fonte: Adzuna ({extraction['country']})")
    print(f"Páginas recebidas: {fetched_pages}")
    print(f"Anúncios extraídos: {fetched_jobs}")
    print(f"JSON bruto salvo em: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
