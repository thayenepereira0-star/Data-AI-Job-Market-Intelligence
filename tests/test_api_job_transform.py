"""DAI-29: contract tests for normalization without external services."""
import unittest

from src.processing.api_job_transform import transform_envelope


class TransformationTests(unittest.TestCase):
    def test_adzuna(self):
        e = {"source": "adzuna", "pages": [{"results": [{"id": "1", "title": "Analista", "company": {"display_name": "Empresa"}, "redirect_url": "https://example.org/a"}]}]}
        valid, rejected = transform_envelope(e)
        self.assertEqual((len(valid), len(rejected)), (1, 0))
        self.assertEqual(valid[0].source, "adzuna")

    def test_himalayas(self):
        e = {"source": "himalayas", "jobs": [{"id": "h1", "title": "Data", "companyName": "Co", "applicationLink": "https://example.org/h"}]}
        valid, rejected = transform_envelope(e)
        self.assertEqual((len(valid), len(rejected)), (1, 0))

    def test_greenhouse(self):
        e = {"source": "greenhouse", "parameters": {"board_token": "kunumi"}, "jobs": [{"id": 5, "title": "Engenheira", "absolute_url": "https://example.org/g"}]}
        valid, rejected = transform_envelope(e)
        self.assertEqual((len(valid), len(rejected)), (1, 0))
        self.assertEqual(valid[0].company, "kunumi")

    def test_lever(self):
        e = {"source": "lever", "parameters": {"site": "ciandt"}, "jobs": [{"id": "p", "text": "Developer", "hostedUrl": "https://example.org/l", "categories": {"location": "Brazil"}}]}
        valid, rejected = transform_envelope(e)
        self.assertEqual((len(valid), len(rejected)), (1, 0))
        self.assertEqual(valid[0].location, "Brazil")

    def test_rejections_and_dedup(self):
        e = {"source": "adzuna", "pages": [{"results": [{"id": "a", "title": "X", "company": {"display_name": "Co"}, "redirect_url": "https://example.org/a"}, {"id": "a", "title": "X", "company": {"display_name": "Co"}, "redirect_url": "https://example.org/a"}, {"title": "X"}]}]}
        good, bad = transform_envelope(e)
        self.assertEqual((len(good), len(bad)), (1, 2))

    def test_unsupported_source(self):
        with self.assertRaises(ValueError):
            transform_envelope({"source": "other", "jobs": []})


if __name__ == "__main__":
    unittest.main()
