"""Real PostgreSQL integration validation against a temporary CI database."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

import psycopg

from src.config import connection_settings
from src.database.api_job_loader import apply_incremental
from src.processing.api_job_transform import NormalizedJob


@unittest.skipUnless(os.getenv("RUN_POSTGRES_INTEGRATION") == "1",
                     "Real database test only runs with an isolated CI PostgreSQL service.")
class PostgreSQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with psycopg.connect(**connection_settings()) as conn:
            schema = Path("sql/001_initial_schema.sql").read_text(encoding="utf-8")
            conn.execute(schema)

    def test_insert_and_replay_do_not_duplicate(self):
        record = NormalizedJob(
            source="adzuna", external_id="ci-integration-0001",
            title="Analista de Dados CI", company="Empresa CI",
            normalized_company="empresa ci",
            url="https://example.org/ci/job/0001",
        )
        first = apply_incremental([record], approved_sources={"adzuna"})
        second = apply_incremental([record], approved_sources={"adzuna"})
        self.assertEqual(first["inserted"], 1)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["already_present"], 1)

        with psycopg.connect(**connection_settings()) as conn:
            row = conn.execute(
                "SELECT count(*) FROM job_postings WHERE external_job_id = %s",
                ("ci-integration-0001",),
            ).fetchone()
        self.assertEqual(row[0], 1)


if __name__ == "__main__":
    unittest.main()
