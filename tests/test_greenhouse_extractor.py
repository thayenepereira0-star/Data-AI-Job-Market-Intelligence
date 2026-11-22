"""Simulated Greenhouse tests; no live API requests are made."""
from __future__ import annotations

import json
from io import BytesIO
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.ingestion.greenhouse_extractor import (
    GreenhouseAPIError,
    extract_board_jobs,
    extract_configured_boards,
    write_raw_extraction,
)


class GreenhouseExtractorTest(unittest.TestCase):
    @staticmethod
    def response(payload: dict) -> BytesIO:
        return BytesIO(json.dumps(payload).encode("utf-8"))

    @patch("src.ingestion.greenhouse_extractor.urlopen")
    def test_fetches_board_and_filters_explicit_brazil_locations(self, mock_urlopen):
        payload = {
            "jobs": [
                {"id": 1, "title": "Analista", "location": {"name": "Brazil"}},
                {"id": 2, "title": "Remote role", "location": {"name": "Remote"}},
            ],
            "meta": {"total": 2},
        }
        mock_urlopen.return_value = self.response(payload)
        result = extract_board_jobs(board_token="kunumi", brazil_only=True)

        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["board_result_count"], 2)
        self.assertEqual(result["jobs"][0]["id"], 1)
        self.assertEqual(result["raw_response"], payload)
        self.assertEqual(result["source"], "greenhouse")
        self.assertIn("T", result["extracted_at"])
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://boards-api.greenhouse.io/v1/boards/kunumi/jobs",
        )

    @patch("src.ingestion.greenhouse_extractor.urlopen")
    def test_requests_full_content_only_when_configured(self, mock_urlopen):
        mock_urlopen.return_value = self.response({"jobs": []})
        extract_board_jobs(board_token="kunumi", include_content=True, brazil_only=False)
        params = parse_qs(urlparse(mock_urlopen.call_args.args[0].full_url).query)
        self.assertEqual(params["content"], ["true"])

    @patch("src.ingestion.greenhouse_extractor.urlopen")
    def test_rejects_bad_board_token_before_network(self, mock_urlopen):
        with self.assertRaises(ValueError):
            extract_board_jobs(board_token="../internal")
        mock_urlopen.assert_not_called()

    @patch("src.ingestion.greenhouse_extractor.urlopen")
    def test_rejects_unexpected_api_response(self, mock_urlopen):
        mock_urlopen.return_value = self.response({"results": []})
        with self.assertRaises(GreenhouseAPIError):
            extract_board_jobs(board_token="kunumi")

    @patch("src.ingestion.greenhouse_extractor.urlopen")
    def test_configured_boards_are_called_sequentially(self, mock_urlopen):
        mock_urlopen.side_effect = [
            self.response({"jobs": []}),
            self.response({"jobs": []}),
        ]
        result = extract_configured_boards(board_tokens=["kunumi", "other"])
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_writes_envelope_with_provenance(self):
        extraction = {
            "source": "greenhouse",
            "extracted_at": "2026-11-22T00:00:00+00:00",
            "parameters": {"board_token": "kunumi"},
            "raw_response": {"jobs": []},
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "raw.json"
            write_raw_extraction(extraction, str(path))
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["parameters"]["board_token"], "kunumi")
        self.assertEqual(saved["source"], "greenhouse")


if __name__ == "__main__":
    unittest.main()
