"""CLI for selected Greenhouse Job Board pages.

By default this command only prints counts. Use --output together with
--confirm-local-storage after confirming that local storage is permitted.
"""
from __future__ import annotations

import argparse
import json
import sys

from src.ingestion.greenhouse_extractor import (
    GreenhouseAPIError,
    extract_configured_boards,
    write_raw_extraction,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consulta páginas Greenhouse selecionadas (GET somente leitura)."
    )
    parser.add_argument(
        "--boards",
        required=True,
        help="Tokens separados por vírgula, por exemplo kunumi",
    )
    parser.add_argument("--include-content", action="store_true")
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
        results = extract_configured_boards(
            board_tokens=[value.strip() for value in args.boards.split(",") if value.strip()],
            include_content=args.include_content,
            brazil_only=not args.all_locations,
        )
        if args.output:
            if len(results) != 1:
                parser.error("Use uma consulta por arquivo de saída.")
            write_raw_extraction(results[0], args.output)
    except (GreenhouseAPIError, OSError, ValueError) as exc:
        print(f"Falha na extração Greenhouse: {exc}", file=sys.stderr)
        return 1

    for result in results:
        print(json.dumps({
            "source": result["source"],
            "board_token": result["parameters"]["board_token"],
            "board_result_count": result["board_result_count"],
            "result_count": result["result_count"],
            "extracted_at": result["extracted_at"],
            "saved": bool(args.output),
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
