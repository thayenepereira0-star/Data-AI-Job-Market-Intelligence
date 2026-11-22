"""CLI for selected public Lever career sites.

By default it only prints observed counts. Persisting requires an explicit
storage-review confirmation flag because public docs do not grant a broad
analytics-retention license.
"""
from __future__ import annotations

import argparse
import json
import sys

from src.ingestion.lever_extractor import (
    LeverAPIError,
    extract_configured_sites,
    write_raw_extraction,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta páginas Lever selecionadas (GET somente leitura)."
    )
    parser.add_argument(
        "--sites",
        required=True,
        help="Slugs separados por vírgula, por exemplo ciandt",
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--all-locations", action="store_true")
    parser.add_argument("--output", help="Arquivo JSON; exige --confirm-local-storage")
    parser.add_argument(
        "--confirm-local-storage",
        action="store_true",
        help="Confirma revisão dos termos/limites de armazenamento para esta fonte.",
    )
    args = parser.parse_args()

    if bool(args.output) != args.confirm_local_storage:
        parser.error("--output e --confirm-local-storage devem ser usados juntos.")

    try:
        results = extract_configured_sites(
            site_slugs=[value.strip() for value in args.sites.split(",") if value.strip()],
            brazil_only=not args.all_locations,
            limit=args.limit,
            pages=args.pages,
        )
        if args.output:
            if len(results) != 1:
                parser.error("Use uma consulta por arquivo de saída.")
            write_raw_extraction(results[0], args.output)
    except (LeverAPIError, OSError, ValueError) as exc:
        print(f"Falha na extração Lever: {exc}", file=sys.stderr)
        return 1

    for result in results:
        print(json.dumps({
            "source": result["source"],
            "site": result["parameters"]["site"],
            "site_result_count": result["site_result_count"],
            "result_count": result["result_count"],
            "pages_returned": len(result["pages"]),
            "extracted_at": result["extracted_at"],
            "saved": bool(args.output),
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
