"""CLI: preview normalized API data; write only with explicit approval."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.database.api_job_loader import apply_incremental, preview
from src.processing.api_job_transform import transform_envelope


def main() -> None:
    parser = argparse.ArgumentParser(description="DAI-30: carga incremental de anúncios de API")
    parser.add_argument("--input", required=True, help="Caminho para um envelope JSON autorizado")
    parser.add_argument("--apply", action="store_true", help="Efetuar inserção transacional")
    parser.add_argument(
        "--approved-source", action="append", default=[],
        help="Fonte cuja persistência foi autorizada após revisão dos termos; repetir por fonte",
    )
    args = parser.parse_args()
    envelope = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records, rejected = transform_envelope(envelope)
    report = {"source": envelope.get("source"), "valid": len(records),
              "rejected": len(rejected), "by_source": preview(records)}
    if args.apply:
        report["load"] = apply_incremental(
            records, approved_sources=set(args.approved_source),
            rejected_count=len(rejected),
        )
    else:
        report["mode"] = "preview_only"
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
