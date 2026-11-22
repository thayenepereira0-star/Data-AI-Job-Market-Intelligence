"""Execute the V2 pipeline in memory, optionally loading approved sources.

Default operation is strictly read-only: third-party API calls plus local
transformation and counts. No raw job ads are printed or saved.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from src.ingestion.orchestrator import run_sources
from src.ingestion.run_multisource import build_registry
from src.processing.api_job_transform import transform_envelope
from src.database.api_job_loader import apply_incremental
from src.processing.v2_quality import analyze_quality

SUPPORTED = frozenset({"adzuna", "himalayas", "greenhouse", "lever"})


def prepare_run(run: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[Any]]]:
    """Summarize output and produce validated records grouped by source."""
    sources: list[dict[str, Any]] = []
    grouped: dict[str, list[Any]] = {}
    rejected_total = 0
    rejected_by_source: dict[str, list[dict[str, Any]]] = {}
    for item in run["results"]:
        name = item["source"]
        if item["status"] != "success":
            sources.append({"source": name, "status": "failure",
                            "error_type": item.get("error_type")})
            continue
        try:
            valid, rejected = transform_envelope(item["extraction"])
        except (ValueError, TypeError, KeyError, AttributeError):
            sources.append({"source": name, "status": "transform_failure"})
            continue
        grouped.setdefault(name, []).extend(valid)
        rejected_total += len(rejected)
        rejected_by_source[name] = rejected
        sources.append({"source": name, "status": "success",
                        "fetched": item["result_count"],
                        "valid": len(valid), "rejected": len(rejected)})
    return {"run_id": run["run_id"], "sources": sources,
            "total_valid": sum(map(len, grouped.values())),
            "total_rejected": rejected_total,
            "quality": analyze_quality((job for records in grouped.values() for job in records), rejected_by_source)}, grouped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Data AI Job Market Intelligence V2 pipeline")
    parser.add_argument("--sources", required=True, help="Lista separada por vírgulas")
    parser.add_argument("--query", default="data analyst")
    parser.add_argument("--country", default="BR")
    parser.add_argument("--greenhouse-boards", default="")
    parser.add_argument("--lever-sites", default="")
    parser.add_argument("--apply", action="store_true", help="Permitir gravação no PostgreSQL")
    parser.add_argument("--approved-storage-sources", default="",
                        help="Fontes cuja retenção foi revisada e aprovada")
    args = parser.parse_args(argv)

    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    if not sources or len(set(sources)) != len(sources) or set(sources) - SUPPORTED:
        parser.error("Informe fontes suportadas, sem repetição.")
    approved = {s.strip().lower() for s in args.approved_storage_sources.split(",") if s.strip()}
    if args.apply and (not approved or approved - set(sources)):
        parser.error("--apply exige fontes aprovadas e selecionadas.")
    try:
        registry = build_registry(
            sources, query=args.query, country=args.country,
            greenhouse_boards=[s.strip() for s in args.greenhouse_boards.split(",") if s.strip()],
            lever_sites=[s.strip() for s in args.lever_sites.split(",") if s.strip()],
        )
    except (ImportError, ValueError) as exc:
        print(f"Configuração inválida: {type(exc).__name__}", file=sys.stderr)
        return 1

    run = run_sources(registry)
    report, grouped = prepare_run(run)
    report["mode"] = "apply" if args.apply else "preview_only"
    if args.apply:
        eligible = [job for name, records in grouped.items()
                    if name in approved for job in records]
        report["sources_approved_for_load"] = sorted(approved)
        report["sources_skipped_for_load"] = sorted(set(grouped) - approved)
        if eligible:
            # Only approved records are passed to the guarded loader.
            try:
                report["load"] = apply_incremental(
                    eligible, approved_sources=approved,
                    rejected_count=sum(x.get("rejected", 0) for x in report["sources"]
                                       if x["source"] in approved),
                )
            except Exception as exc:
                report["load_error_type"] = type(exc).__name__
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 1
        else:
            report["load"] = {"inserted": 0, "reason": "no_approved_valid_records"}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(s["status"] == "success" for s in report["sources"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
