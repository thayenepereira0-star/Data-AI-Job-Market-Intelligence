"""Simulated Lever tests; no live API requests are made."""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.ingestion.lever_extractor import (
    LeverAPIError,
    extract_configured_sites,
    extract_site_jobs,
    write_raw_extraction,
)


class LeverExtractorTest(unittest.TestCase):
    @staticmethod
    def response(payload: list[dict]) -> BytesIO:
        return BytesIO(json.dumps(payload).encode("utf-8"))

    @patch("src.ingestion.lever_extractor.urlopen")
    def test_fetches_site_paginates_and_filters_brazil(self, mock_urlopen):
        first = [
            {"id": "br-1", "text": "Analista", "categories": {"location": "Brazil"}},
            {"id": "remote", "text": "Remote", "categories": {"location": "Remote"}},
        ]
        mock_urlopen.side_effect = [self.response(first), self.response([])]
        result = extract_site_jobs(site="ciandt", limit=2, pages=3)

        self.assertEqual(result["site_result_count"], 2)
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(len(result["pages"]), 2)
        self.assertEqual(result["pages"][0], first)
        self.assertEqual(result["jobs"][0]["id"], "br-1")

        first_request = mock_urlopen.call_args_list[0].args[0]
        params = parse_qs(urlparse(first_request.full_url).query)
        self.assertEqual(params["mode"], ["json"])
        self.assertEqual(params["skip"], ["0"])
        self.assertEqual(params["limit"], ["2"])
        second_request = mock_urlopen.call_args_list[1].args[0]
        self.assertIn("skip=2", second_request.full_url)

    @patch("src.ingestion.lever_extractor.urlopen")
    def test_rejects_invalid_slug_before_network(self, mock_urlopen):
        with self.assertRaises(ValueError):
            extract_site_jobs(site="../internal")
        mock_urlopen.assert_not_called()

    @patch("src.ingestion.lever_extractor.urlopen")
    def test_rejects_invalid_response_shape(self, mock_urlopen):
        mock_urlopen.return_value = BytesIO(b'{"jobs":[]}')
        with self.assertRaises(LeverAPIError):
            extract_site_jobs(site="ciandt")

    @patch("src.ingestion.lever_extractor.urlopen")
    def test_configured_sites_are_called_sequentially(self, mock_urlopen):
        mock_urlopen.side_effect = [
            self.response([]),
            self.response([]),
        ]
        results = extract_configured_sites(site_slugs=["ciandt", "example"])
        self.assertEqual(len(results), 2)
        self.assertEqual(mock_urlopen.call_count, 2)

    def test_writes_raw_envelope_with_source_parameters(self):
        extraction = {
            "source": "lever",
            "extracted_at": "2026-11-22T00:00:00+00:00",
            "parameters": {"site": "ciandt"},
            "pages": [[]],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "raw.json"
            write_raw_extraction(extraction, str(path))
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["source"], "lever")
        self.assertEqual(saved["parameters"]["site"], "ciandt")


if __name__ == "__main__":
    unittest.main()
