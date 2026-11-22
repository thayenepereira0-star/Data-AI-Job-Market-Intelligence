"""DAI-30: loader cannot write without source approval or valid input."""
import unittest
from unittest.mock import patch

from src.database.api_job_loader import SOURCE_DB_NAMES, apply_incremental, preview
from src.processing.api_job_transform import NormalizedJob


class LoaderSafetyTests(unittest.TestCase):
    def setUp(self):
        self.record = NormalizedJob(
            source="adzuna", external_id="test-1", title="Analista",
            company="Empresa Teste", normalized_company="empresa teste",
            url="https://example.org/jobs/1",
        )

    def test_adzuna_preserves_existing_source_name(self):
        self.assertEqual(SOURCE_DB_NAMES["adzuna"], "Adzuna")

    def test_preview_never_connects(self):
        with patch("src.database.api_job_loader.psycopg.connect") as connection:
            self.assertEqual(preview([self.record]), {"adzuna": 1})
            connection.assert_not_called()

    def test_unapproved_source_never_connects(self):
        with patch("src.database.api_job_loader.psycopg.connect") as connection:
            with self.assertRaisesRegex(ValueError, "Nenhuma fonte aprovada"):
                apply_incremental([self.record], approved_sources=set())
            connection.assert_not_called()

    def test_mixed_approved_and_unapproved_rejected_before_connection(self):
        second = NormalizedJob(
            source="lever", external_id="2", title="Data Engineer",
            company="Empresa", normalized_company="empresa",
            url="https://example.org/jobs/2",
        )
        with patch("src.database.api_job_loader.psycopg.connect") as connection:
            with self.assertRaisesRegex(ValueError, "sem permissão"):
                apply_incremental([self.record, second], approved_sources={"adzuna"})
            connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
