"""Testes do extrator Adzuna sem chamadas de rede nem credenciais reais."""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from src.ingestion.adzuna_extractor import (
    AdzunaAPIError,
    extract_jobs,
    write_raw_extraction,
)


class AdzunaExtractorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.credentials = patch(
            "src.ingestion.adzuna_extractor.adzuna_credentials",
            return_value=("fake-id", "fake-key"),
        )
        self.credentials.start()
        self.addCleanup(self.credentials.stop)

    @staticmethod
    def response(payload: dict) -> BytesIO:
        return BytesIO(json.dumps(payload).encode("utf-8"))

    @patch("src.ingestion.adzuna_extractor.urlopen")
    def test_extracts_pages_and_preserves_raw_response(self, mock_urlopen) -> None:
        first = {
            "count": 1,
            "results": [{
                "id": "job-1",
                "title": "Data Analyst",
                "company": {"display_name": "Empresa Exemplo"},
            }],
        }
        mock_urlopen.side_effect = [
            self.response(first),
            self.response({"count": 0, "results": []}),
        ]

        extraction = extract_jobs(
            what=" data analyst ",
            where="Rio de Janeiro",
            pages=4,
            results_per_page=10,
        )

        self.assertEqual(len(extraction["pages"]), 2)
        self.assertEqual(extraction["pages"][0], first)
        self.assertEqual(extraction["pages"][1]["results"], [])
        self.assertEqual(extraction["query"]["what"], "data analyst")
        self.assertEqual(extraction["query"]["where"], "Rio de Janeiro")
        self.assertEqual(extraction["source"], "adzuna")
        self.assertEqual(mock_urlopen.call_count, 2)

        request = mock_urlopen.call_args_list[0].args[0]
        parsed = urlparse(request.full_url)
        self.assertEqual(parsed.path, "/v1/api/jobs/br/search/1")
        params = parse_qs(parsed.query)
        self.assertEqual(params["what"], ["data analyst"])
        self.assertEqual(params["where"], ["Rio de Janeiro"])
        self.assertEqual(params["app_id"], ["fake-id"])
        self.assertEqual(params["app_key"], ["fake-key"])

    @patch("src.ingestion.adzuna_extractor.urlopen")
    def test_uses_configurable_country_and_page_start(self, mock_urlopen) -> None:
        mock_urlopen.return_value = self.response({"results": []})

        extract_jobs(what="data engineer", country="us", first_page=3, pages=1)

        request = mock_urlopen.call_args.args[0]
        self.assertIn("/jobs/us/search/3?", request.full_url)

    @patch("src.ingestion.adzuna_extractor.urlopen")
    def test_rejects_invalid_search_before_network_call(self, mock_urlopen) -> None:
        with self.assertRaises(ValueError):
            extract_jobs(what="  ")
        mock_urlopen.assert_not_called()

    @patch("src.ingestion.adzuna_extractor.urlopen")
    def test_http_error_does_not_expose_request_url_or_key(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = HTTPError(
            "https://api.example/search?app_key=fake-key",
            401,
            "Unauthorized",
            None,
            BytesIO(b"private response"),
        )

        with self.assertRaises(AdzunaAPIError) as caught:
            extract_jobs(what="data analyst")

        self.assertIn("HTTP 401", str(caught.exception))
        self.assertNotIn("fake-key", str(caught.exception))
        self.assertNotIn("api.example", str(caught.exception))

    @patch("src.ingestion.adzuna_extractor.urlopen")
    def test_rejects_unexpected_api_response_shape(self, mock_urlopen) -> None:
        mock_urlopen.return_value = self.response({"unexpected": []})

        with self.assertRaisesRegex(AdzunaAPIError, "lista de resultados"):
            extract_jobs(what="data analyst")

    def test_writes_raw_json_without_credentials(self) -> None:
        extraction = {
            "source": "adzuna",
            "pages": [{"results": [{"id": "job-1"}]}],
        }
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "raw" / "jobs.json"
            write_raw_extraction(extraction, str(output))
            saved_text = output.read_text(encoding="utf-8")
            saved = json.loads(saved_text)

        self.assertEqual(saved, extraction)
        self.assertNotIn("app_key", saved_text)


if __name__ == "__main__":
    unittest.main()
