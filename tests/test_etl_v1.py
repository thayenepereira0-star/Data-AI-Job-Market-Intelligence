"""DAI-26: testes unitários ETL sem Docker e sem escrita no banco."""
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.ingestion.csv_reader import read_csv
from src.processing.job_transform import parse_record, unique_records


class ETLTest(unittest.TestCase):
    def test_clean_missing_company_is_rejected(self):
        row = {"title": "Analista", "empresa": "", "redirect_url": "https://example.com/details/123"}
        with self.assertRaisesRegex(ValueError, "empresa"):
            parse_record(row, 2)

    def test_transform_preserves_source_evidence(self):
        row = {
            "title": "Data Analyst", "empresa": "Exemplo SA",
            "redirect_url": "https://example.com/details/123",
            "description": "SQL exigido", "created": "2026-10-22 17:52:58+00:00",
            "salary_min": "", "salary_max": "", "contract_type": ""
        }
        rec = parse_record(row, 2)
        self.assertEqual(rec.external_id, "123")
        self.assertEqual(rec.normalized_company, "exemplo sa")
        self.assertEqual(rec.description, "SQL exigido")
        self.assertIsNone(rec.salary_min)
        self.assertIsNone(rec.employment_type)

    def test_duplicate_external_id_is_skipped(self):
        base = {"title": "Data Engineer", "empresa": "Exemplo",
                "redirect_url": "https://example.com/details/123"}
        a = parse_record(base, 2)
        b = parse_record({**base, "redirect_url": "https://example.com/details/123?origin=another"}, 3)
        unique, duplicates = unique_records([a, b])
        self.assertEqual((len(unique), duplicates), (1, 1))

    def test_reader_reports_rejected_rows(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.csv"
            columns = ["title", "empresa", "description", "redirect_url",
                       "created", "salary_min", "salary_max", "contract_type"]
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerow({"title": "Analista", "empresa": "Exemplo",
                    "redirect_url": "https://example.com/details/55"})
                writer.writerow({"title": "Sem empresa",
                    "redirect_url": "https://example.com/details/56"})
            records, rejects, total = read_csv(path)
            self.assertEqual((len(records), len(rejects), total), (1, 1, 2))
            self.assertEqual(rejects[0][0], 3)


if __name__ == "__main__":
    unittest.main()
