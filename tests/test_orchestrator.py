"""Simulated orchestrator tests; connectors are local functions, no API calls."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.ingestion.orchestrator import persist_raw_results, run_sources


class OrchestratorTest(unittest.TestCase):
    def test_records_success_zero_results_and_failure_without_stopping(self):
        def good():
            return {
                "source": "himalayas",
                "extracted_at": "2026-11-22T00:00:00+00:00",
                "parameters": {"country": "BR"},
                "jobs": [{"guid": "1"}],
                "result_count": 1,
            }

        def empty():
            return {"source": "greenhouse", "parameters": {}, "jobs": []}

        def broken():
            raise RuntimeError("credential URL should never be copied to result")

        run = run_sources({"himalayas": good, "greenhouse": empty, "lever": broken})
        by_source = {item["source"]: item for item in run["results"]}
        self.assertEqual(run["source_count"], 3)
        self.assertEqual(run["success_count"], 2)
        self.assertEqual(run["failure_count"], 1)
        self.assertEqual(by_source["himalayas"]["result_count"], 1)
        self.assertEqual(by_source["greenhouse"]["result_count"], 0)
        self.assertEqual(by_source["lever"]["status"], "failure")
        self.assertEqual(by_source["lever"]["error_type"], "RuntimeError")
        self.assertNotIn("credential URL", json.dumps(by_source["lever"]))

    def test_raw_persistence_requires_explicit_per_source_approval(self):
        run = run_sources({
            "himalayas": lambda: {
                "source": "himalayas",
                "extracted_at": "2026-11-22T00:00:00+00:00",
                "parameters": {"country": "BR"},
                "raw_response": {"jobs": [{"guid": "one"}]},
                "result_count": 1,
            },
            "greenhouse": lambda: {
                "source": "greenhouse",
                "parameters": {"board_token": "kunumi"},
                "raw_response": {"jobs": [{"id": 1}]},
                "result_count": 1,
            },
        })
        with TemporaryDirectory() as directory:
            saved = persist_raw_results(
                run,
                output_dir=directory,
                approved_sources={"himalayas"},
            )
            self.assertEqual(set(saved), {"himalayas"})
            content = json.loads(Path(saved["himalayas"]).read_text(encoding="utf-8"))
        self.assertEqual(content["source"], "himalayas")
        self.assertNotIn("greenhouse", saved)

    def test_rejects_empty_source_list(self):
        with self.assertRaises(ValueError):
            run_sources({})


if __name__ == "__main__":
    unittest.main()
