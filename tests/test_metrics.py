import unittest

import pandas as pd

from src.metrics import enrich_metrics, severity_bucket, theme_summary, weighted_rate


class MetricsTests(unittest.TestCase):
    def test_positive_consensus_does_not_create_pain(self):
        data = pd.DataFrame(
            {
                "post_sentiment": [0.8],
                "comment_neg_rate": [0.0],
                "comment_neu_rate": [0.0],
                "comment_pos_rate": [1.0],
                "n_comments_scraped": [10],
                "comment_confidence": ["medium"],
            }
        )
        result = enrich_metrics(data).iloc[0]
        self.assertEqual(result["pain_intensity"], 0.0)
        self.assertEqual(result["negative_consensus"], 0.0)

    def test_comment_rate_is_weighted_by_actual_comments(self):
        data = pd.DataFrame(
            {"comment_neg_rate": [1.0, 0.0, 1.0], "n_comments_scraped": [1, 9, 0]}
        )
        self.assertAlmostEqual(weighted_rate(data, "comment_neg_rate"), 0.1)

    def test_theme_priority_is_additive_confidence_adjusted_pain(self):
        data = pd.DataFrame(
            {
                "theme": ["routing", "routing"],
                "post_sentiment": [-1.0, 0.0],
                "comment_neg_rate": [1.0, 0.0],
                "comment_neu_rate": [0.0, 1.0],
                "comment_pos_rate": [0.0, 0.0],
                "n_comments_scraped": [20, 5],
                "comment_confidence": ["high", "medium"],
            }
        )
        summary = theme_summary(enrich_metrics(data)).iloc[0]
        self.assertAlmostEqual(summary["priority_score"], 1.0)
        self.assertAlmostEqual(summary["comment_neg_rate"], 0.8)

    def test_thresholds_are_stable(self):
        self.assertEqual(severity_bucket(0.35), "critical")
        self.assertEqual(severity_bucket(0.20), "high")
        self.assertEqual(severity_bucket(0.10), "medium")


if __name__ == "__main__":
    unittest.main()
