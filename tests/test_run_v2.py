"""The cross-source pipeline preview must not access PostgreSQL."""
import unittest
from unittest.mock import patch

from src.run_v2 import main, prepare_run


class V2IntegrationTests(unittest.TestCase):
    def test_prepare_run_handles_multiple_envelopes(self):
        run = {
            "run_id": "test-run",
            "results": [
                {"source": "himalayas", "status": "success", "result_count": 1,
                 "extraction": {"source": "himalayas", "jobs": [
                     {"id": "h1", "title": "Data", "companyName": "Co",
                      "applicationLink": "https://example.org/h"}]}},
                {"source": "lever", "status": "failure", "error_type": "RuntimeError"},
            ],
        }
        report, grouped = prepare_run(run)
        self.assertEqual(report["total_valid"], 1)
        self.assertEqual(report["sources"][1]["status"], "failure")
        self.assertEqual(len(grouped["himalayas"]), 1)

    def test_preview_never_calls_loader(self):
        fake_run = {"run_id": "local", "results": [
            {"source": "greenhouse", "status": "success", "result_count": 1,
             "extraction": {"source": "greenhouse", "parameters": {"board_token": "kunumi"},
                            "jobs": [{"id": 1, "title": "Developer",
                                      "absolute_url": "https://example.org/job"}]}}
        ]}
        with patch("src.run_v2.build_registry", return_value={"greenhouse": object()}), \\
             patch("src.run_v2.run_sources", return_value=fake_run), \\
             patch("src.run_v2.apply_incremental") as loader, \\
             patch("builtins.print"):
            self.assertEqual(main(["--sources", "greenhouse", "--greenhouse-boards", "kunumi"]), 0)
            loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
