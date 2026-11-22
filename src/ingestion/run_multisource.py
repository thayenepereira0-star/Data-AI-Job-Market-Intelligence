"""Run configured extraction sources and report per-source outcomes."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

from src.ingestion.orchestrator import persist_raw_results, run_sources


def _combine_source_envelopes(source: str, envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    # Keep each career board's identity; combining lists must not erase provenance.
    identifier = "board_token" if source == "greenhouse" else "site"
    jobs = [
        {**job, "_origin_board": envelope.get("parameters", {}).get(identifier)}
        for envelope in envelopes
        for job in envelope.get("jobs", [])
    ]
    return {
        "source": source,
        "source_url": envelopes[0].get("source_url") if envelopes else None,
        "extracted_at": envelopes[0].get("extracted_at") if envelopes else None,
        "parameters": {
            "boards" if source == "greenhouse" else "sites": [
                envelope.get("parameters", {}).get(
                    "board_token" if source == "greenhouse" else "site"
                )
                for envelope in envelopes
            ]
        },
        "jobs": jobs,
        "pages": [
            envelope.get("raw_response", envelope.get("pages"))
            for envelope in envelopes
        ],
        "result_count": len(jobs),
    }


def build_registry(
    sources: list[str],
    *,
    query: str,
    country: str,
    greenhouse_boards: list[str],
    lever_sites: list[str],
) -> dict[str, Any]:
    """Load requested connectors only; let unmerged connectors stay optional."""
    registry: dict[str, Any] = {}
    if "adzuna" in sources:
        from src.ingestion.adzuna_extractor import extract_jobs as extract_adzuna

        registry["adzuna"] = lambda: extract_adzuna(
            what=query, country=country.lower(), pages=1
        )
    if "himalayas" in sources:
        from src.ingestion.himalayas_extractor import extract_jobs as extract_himalayas

        registry["himalayas"] = lambda: extract_himalayas(
            query=query, country=country.upper(), page=1
        )
    if "greenhouse" in sources:
        if not greenhouse_boards:
            raise ValueError("Informe --greenhouse-boards ao selecionar Greenhouse.")
        from src.ingestion.greenhouse_extractor import extract_configured_boards

        registry["greenhouse"] = lambda: _combine_source_envelopes(
            "greenhouse",
            extract_configured_boards(board_tokens=greenhouse_boards, brazil_only=True),
        )
    if "lever" in sources:
        if not lever_sites:
            raise ValueError("Informe --lever-sites ao selecionar Lever.")
        from src.ingestion.lever_extractor import extract_configured_sites

        registry["lever"] = lambda: _combine_source_envelopes(
            "lever",
            extract_configured_sites(site_slugs=lever_sites, brazil_only=True),
        )
    return registry


def main() -> int:
    parser = argparse.ArgumentParser(description="Orquestra extrações de vagas V2.")
    parser.add_argument(
        "--sources",
        required=True,
        help="Fontes separadas por vírgula: adzuna,himalayas,greenhouse,lever",
    )
    parser.add_argument("--query", default="data analyst")
    parser.add_argument("--country", default="BR")
    parser.add_argument("--greenhouse-boards", default="")
    parser.add_argument("--lever-sites", default="")
    parser.add_argument("--persist-raw", action="store_true")
    parser.add_argument(
        "--approved-storage-sources",
        default="",
        help="Fontes com armazenamento revisado e permitido; padrão vazio.",
    )
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sources = [value.strip().lower() for value in args.sources.split(",") if value.strip()]
    unknown = set(sources) - {"adzuna", "himalayas", "greenhouse", "lever"}
    if unknown:
        parser.error(f"Fontes desconhecidas: {', '.join(sorted(unknown))}")
    storage_approved = {
        value.strip().lower()
        for value in args.approved_storage_sources.split(",")
        if value.strip()
    }
    if args.persist_raw and not storage_approved:
        parser.error("--persist-raw exige --approved-storage-sources.")

    try:
        registry = build_registry(
            sources,
            query=args.query,
            country=args.country,
            greenhouse_boards=[
                value.strip() for value in args.greenhouse_boards.split(",") if value.strip()
            ],
            lever_sites=[
                value.strip() for value in args.lever_sites.split(",") if value.strip()
            ],
        )
        run = run_sources(registry)
        if args.persist_raw:
            saved = persist_raw_results(
                run,
                output_dir=args.output_dir,
                approved_sources=storage_approved,
            )
        else:
            saved = {}
    except (ImportError, OSError, ValueError) as exc:
        print(f"Falha ao configurar/executar o pipeline: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({
        "run_id": run["run_id"],
        "source_count": run["source_count"],
        "success_count": run["success_count"],
        "failure_count": run["failure_count"],
        "results": [
            {
                "source": item["source"],
                "status": item["status"],
                "result_count": item["result_count"],
                "duration_ms": item["duration_ms"],
                "error_type": item.get("error_type"),
            }
            for item in run["results"]
        ],
        "saved_raw": saved,
    }, ensure_ascii=False, indent=2))
    return 0 if not run["failure_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
