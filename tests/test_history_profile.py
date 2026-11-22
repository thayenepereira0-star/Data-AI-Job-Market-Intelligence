"""Unit tests for safety and shape of read-only historical analytics."""
import unittest
from unittest.mock import patch, MagicMock

from src.database.history_profile import profile


class HistoricalProfileTest(unittest.TestCase):
    @patch("src.database.history_profile.connection_settings", return_value={})
    @patch("src.database.history_profile.psycopg.connect")
    def test_aggregations_run_read_only_and_never_mutate(self, connect, _settings):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (127, 5, 3, 12, 40, 95, 0),
            (1,),
            (0,),
        ]
        cursor.fetchall.side_effect = [
            [("2026-10", 127)],
            [("Company X", 4)],
            [("Adzuna", 127)],
        ]
        connection = connect.return_value.__enter__.return_value
        connection.cursor.return_value.__enter__.return_value = cursor

        result = profile()
        self.assertEqual(result["mode"], "read_only")
        self.assertEqual(result["completeness"]["total"], 127)
        self.assertEqual(result["review_candidates"]["same_company_normalized_title_groups"], 1)
        self.assertEqual(result["postings_by_source"], {"Adzuna": 127})
        sql_statements = [call.args[0].strip().upper() for call in cursor.execute.call_args_list]
        self.assertTrue(sql_statements[0].startswith("SET TRANSACTION READ ONLY"))
        self.assertTrue(all(stmt.startswith(("SET TRANSACTION READ ONLY", "SELECT")) for stmt in sql_statements))
        self.assertNotIn("INSERT", " ".join(sql_statements))
        self.assertNotIn("DELETE", " ".join(sql_statements))
        self.assertNotIn("UPDATE ", " ".join(sql_statements))


if __name__ == "__main__":
    unittest.main()
