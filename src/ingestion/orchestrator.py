"""Small multissource runner with isolated failures and raw provenance."""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

Connector = Callable[[], dict[str, Any]]
logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result_count(extraction: dict[str, Any]) -> int:
    count = extraction.get("result_count")
    if isinstance(count, int) and count >= 0:
        return count
    jobs = extraction.get("jobs")
    if isinstance(jobs, list):
        return len(jobs)
    pages = extraction.get("pages")
    if isinstance(pages, list):
        total = 0
        for page in pages:
            if isinstance(page, list):
                total += len(page)
            elif isinstance(page, dict):
                results = page.get("results")
                if isinstance(results, list):
                    total += len(results)
        return total
    return 0


def run_sources(
    configured_sources: Mapping[str, Connector],
    *,
    log: logging.Logger | None = None,
) -> dict[str, Any]:
    """Run each configured connector independently and return raw envelopes.

    Failures are recorded by exception type only, avoiding accidental leakage
    of credentials or full request URLs from third-party exceptions.
    """
    if not configured_sources:
        raise ValueError("Configure ao menos uma fonte de extração.")
    run_logger = log or logger
    run_id = str(uuid.uuid4())
    started_at = _utc_now()
    results: list[dict[str, Any]] = []

    for source, connector in configured_sources.items():
        source_started = time.monotonic()
        try:
            extraction = connector()
            if not isinstance(extraction, dict):
                raise TypeError("connector returned a non-dictionary envelope")
            count = _result_count(extraction)
            duration_ms = round((time.monotonic() - source_started) * 1000, 2)
            item = {
                "source": source,
                "status": "success",
                "extracted_at": extraction.get("extracted_at", _utc_now()),
                "parameters": extraction.get("parameters", extraction.get("query", {})),
                "result_count": count,
                "duration_ms": duration_ms,
                "extraction": extraction,
            }
            run_logger.info(
                "extraction_source_result",
                extra={
                    "run_id": run_id,
                    "source": source,
                    "status": "success",
                    "result_count": count,
                    "duration_ms": duration_ms,
                },
            )
        except Exception as exc:  # isolate an unavailable source from others
            duration_ms = round((time.monotonic() - source_started) * 1000, 2)
            item = {
                "source": source,
                "status": "failure",
                "extracted_at": _utc_now(),
                "parameters": {},
                "result_count": 0,
                "duration_ms": duration_ms,
                "error_type": type(exc).__name__,
            }
            run_logger.warning(
                "extraction_source_result",
                extra={
                    "run_id": run_id,
                    "source": source,
                    "status": "failure",
                    "result_count": 0,
                    "duration_ms": duration_ms,
                    "error_type": type(exc).__name__,
                },
            )
        results.append(item)

    return {
        "run_id": run_id,
        "started_at": started_at,
        "completed_at": _utc_now(),
        "source_count": len(configured_sources),
        "success_count": sum(item["status"] == "success" for item in results),
        "failure_count": sum(item["status"] == "failure" for item in results),
        "results": results,
    }


def persist_raw_results(
    run: dict[str, Any],
    *,
    output_dir: str | Path,
    approved_sources: set[str] | frozenset[str],
) -> dict[str, str]:
    """Persist successful source envelopes only for explicitly approved sources.

    Greenhouse/Lever are intentionally omitted from approved_sources until a
    project owner has reviewed and documented storage permission for each.
    """
    directory = Path(output_dir)
    saved: dict[str, str] = {}
    for item in run.get("results", []):
        source = item.get("source", "")
        if item.get("status") != "success" or source not in approved_sources:
            continue
        extraction = item.get("extraction")
        if not isinstance(extraction, dict) or extraction.get("source") != source:
            continue
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{source}_{run['run_id']}.json"
        path.write_text(
            json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        saved[source] = str(path)
    return saved
