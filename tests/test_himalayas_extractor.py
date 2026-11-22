"""Simulated unit tests: no real Himalayas API request is made."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from src.ingestion.himalayas_extractor import (
    HimalayasAPIError,
    extract_jobs,
    remove_expired_jobs,
    write_raw_extraction,
)


class HimalayasExtractorTest(unittest.TestCase):
    def response(self, payload: dict) -> BytesIO:
        return BytesIO(json.dumps(payload).encode("utf-8"))

    @patch("src.ingestion.himalayas_extractor.urlopen")
    def test_builds_brazil_search_and_preserves_raw_response(self, mock_urlopen):
        payload = {"jobs": [{"guid": "job-1", "title": "Data Analyst"}], "totalCount": 1}
        mock_urlopen.return_value = self.response(payload)

        result = extract_jobs(
            query=" data analyst ",
            country="br",
            exclude_worldwide=True,
            seniority="Entry-level",
            employment_type="Full Time",
            page=2,
            api_key="test-only-key",
        )

        request = mock_urlopen.call_args.args[0]
        params = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(params["country"], ["BR"])
        self.assertEqual(params["q"], ["data analyst"])
        self.assertEqual(params["page"], ["2"])
        self.assertEqual(params["exclude_worldwide"], ["true"])
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only-key")
        self.assertEqual(result["raw_response"], payload)
        self.assertEqual(result["source"], "himalayas")
        self.assertEqual(result["result_count"], 1)
        self.assertTrue(datetime.fromisoformat(result["extracted_at"]).tzinfo)

    @patch("src.ingestion.himalayas_extractor.urlopen")
    def test_rejects_blank_query_without_network(self, mock_urlopen):
        with self.assertRaises(ValueError):
            extract_jobs(query="   ")
        mock_urlopen.assert_not_called()

    @patch("src.ingestion.himalayas_extractor.urlopen")
    def test_rejects_invalid_page_without_network(self, mock_urlopen):
        with self.assertRaises(ValueError):
            extract_jobs(page=0)
        mock_urlopen.assert_not_called()

    @patch("src.ingestion.himalayas_extractor.urlopen")
    def test_sanitizes_http_errors_and_retains_retry_after(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            "https://himalayas.app/jobs/api/search?key=secret",
            429,
            "Too Many Requests",
            {"Retry-After": "30"},
            BytesIO(b"secret response"),
        )
        with self.assertRaises(HimalayasAPIError) as error:
            extract_jobs()
        self.assertIn("HTTP 429", str(error.exception))
        self.assertIn("Retry-After: 30", str(error.exception))
        self.assertNotIn("secret", str(error.exception))

    @patch("src.ingestion.himalayas_extractor.urlopen")
    def test_rejects_unexpected_payload(self, mock_urlopen):
        mock_urlopen.return_value = self.response({"results": []})
        with self.assertRaisesRegex(HimalayasAPIError, "lista 'jobs'"):
            extract_jobs()

    def test_removes_expired_jobs_from_copy_and_raw_snapshot(self):
        now = datetime(2026, 11, 22, tzinfo=timezone.utc)
        extraction = {
            "source": "himalayas",
            "jobs": [
                {"guid": "open", "expiryDate": now.timestamp() + 600},
                {"guid": "closed", "expiryDate": now.timestamp() - 1},
                {"guid": "unknown"},
            ],
            "raw_response": {
                "jobs": [
                    {"guid": "open", "expiryDate": now.timestamp() + 600},
                    {"guid": "closed", "expiryDate": now.timestamp() - 1},
                    {"guid": "unknown"},
                ]
            },
        }
        clean = remove_expired_jobs(extraction, now=now)
        self.assertEqual([job["guid"] for job in clean["jobs"]], ["open", "unknown"])
        self.assertEqual(clean["result_count"], 2)
        self.assertEqual(len(extraction["jobs"]), 3)

    def test_writes_json_with_provenance(self):
        extraction = {
            "source": "himalayas",
            "extracted_at": "2026-11-22T00:00:00+00:00",
            "parameters": {"country": "BR", "page": 1},
            "jobs": [{"guid": "job-1"}],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "raw" / "jobs.json"
            write_raw_extraction(extraction, str(path))
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["source"], "himalayas")
        self.assertEqual(saved["parameters"]["country"], "BR")


if __name__ == "__main__":
    unittest.main()
