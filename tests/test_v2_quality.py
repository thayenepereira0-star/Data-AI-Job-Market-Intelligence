"""Quality diagnostics do not reveal raw job records or contact a database."""
import unittest

from src.processing.api_job_transform import NormalizedJob
from src.processing.v2_quality import analyze_quality
from src.run_v2 import prepare_run


class QualityTest(unittest.TestCase):
    def test_counts_cross_provider_same_url_without_leaking_url(self):
        jobs = [
            NormalizedJob(source="adzuna", external_id="a", title="Data Analyst", company="ACME",
                          normalized_company="acme", url="https://EXAMPLE.org/jobs/1?utm_source=ads"),
            NormalizedJob(source="lever", external_id="b", title="Data Analyst", company="ACME",
                          normalized_company="acme", url="https://example.org/jobs/1"),
        ]
        report = analyze_quality(jobs, {"adzuna": [{"index": 8, "reason": "URL inválida"}]})
        self.assertEqual(report["cross_source_same_url_groups"], 1)
        self.assertEqual(report["cross_source_same_company_title_groups"], 1)
        self.assertEqual(report["rejections"]["adzuna"]["URL inválida"], 1)
        self.assertNotIn("example.org", str(report))
        self.assertNotIn("Data Analyst", str(report))

    def test_different_source_same_title_only_is_not_confirmed(self):
        jobs = [
            NormalizedJob(source="himalayas", external_id="a", title="Analyst",
                          company="One", normalized_company="one", url="https://a.test/1"),
            NormalizedJob(source="greenhouse", external_id="b", title="Analyst",
                          company="Two", normalized_company="two", url="https://b.test/2"),
        ]
        report = analyze_quality(jobs, {})
        self.assertEqual(report["cross_source_same_url_groups"], 0)
        self.assertEqual(report["cross_source_same_company_title_groups"], 0)

    def test_rejection_reason_is_in_pipeline_report(self):
        run = {"run_id": "t", "results": [
            {"source": "adzuna", "status": "success", "result_count": 1,
             "extraction": {"source": "adzuna", "pages": [
                 {"results": [{"id": "x", "title": "Data", "company": {"display_name": "ACME"}}]}
             ]}}
        ]}
        result, _ = prepare_run(run)
        self.assertEqual(result["total_rejected"], 1)
        self.assertEqual(result["quality"]["rejections"]["adzuna"]["título, empresa ou URL ausente"], 1)


if __name__ == "__main__":
    unittest.main()
