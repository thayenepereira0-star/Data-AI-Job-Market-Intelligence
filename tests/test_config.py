"""DAI-27: configuração e credenciais testadas sem acessar serviços externos."""
import os
import unittest
from unittest.mock import patch

from src.config import connection_settings, adzuna_credentials


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "POSTGRES_PASSWORD": "test-secret-not-real",
            "POSTGRES_PORT": "5432",
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_DB": "jobmarket",
            "POSTGRES_USER": "jobmarket",
            "ADZUNA_APP_ID": "test-id-not-real",
            "ADZUNA_APP_KEY": "test-key-not-real",
        })
        self.env.start()
        self.dotenv = patch("src.config.load_dotenv")
        self.dotenv.start()

    def tearDown(self):
        self.dotenv.stop()
        self.env.stop()

    def test_valid_postgres_connection_configuration(self):
        config = connection_settings()
        self.assertEqual(config["port"], 5432)
        self.assertEqual(config["dbname"], "jobmarket")
        self.assertEqual(config["connect_timeout"], 5)

    def test_rejects_missing_password_without_echo(self):
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": ""}):
            with self.assertRaises(ValueError) as result:
                connection_settings()
            self.assertNotIn("test-secret-not-real", str(result.exception))

    def test_rejects_invalid_port(self):
        for invalid in ("not-a-port", "0", "65536"):
            with self.subTest(port=invalid), patch.dict(os.environ, {"POSTGRES_PORT": invalid}):
                with self.assertRaises(ValueError):
                    connection_settings()

    def test_adzuna_credentials_optional_until_requested(self):
        with patch.dict(os.environ, {"ADZUNA_APP_ID": "", "ADZUNA_APP_KEY": ""}):
            self.assertEqual(connection_settings()["dbname"], "jobmarket")
            with self.assertRaises(ValueError):
                adzuna_credentials()

    def test_adzuna_credentials_available_when_configured(self):
        self.assertEqual(adzuna_credentials(), ("test-id-not-real", "test-key-not-real"))


if __name__ == "__main__":
    unittest.main()
