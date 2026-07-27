from pathlib import Path
import json
import unittest

from skills.openconcierge.scripts.rank_candidates import rank_payload

ROOT = Path(__file__).resolve().parents[1]


def load_fixture(name):
    return json.loads((ROOT / "tests" / "fixtures" / "ranking" / name).read_text(encoding="utf-8"))


class RankingTests(unittest.TestCase):
    def test_hard_filters_and_ranked_result(self):
        result = rank_payload(load_fixture("basic.json"))
        self.assertEqual([item["name"] for item in result["ranked"]], ["Valid Cooling Pillow"])
        self.assertEqual(result["rejected"][0]["reason"], "over_budget")
        self.assertEqual(result["rejected"][1]["reason"], "region_unavailable")
        self.assertEqual(result["ranked"][0]["score_breakdown"]["cooling"], 3.0)

    def test_unknown_required_evidence_is_unranked(self):
        result = rank_payload(load_fixture("unknown-evidence.json"))
        self.assertEqual(result["ranked"], [])
        self.assertEqual(result["unranked"][0]["reason"], "unverified_must_have")

    def test_positive_match_without_source_is_not_positive(self):
        payload = load_fixture("basic.json")
        payload["candidates"][0]["criteria"][0]["source_urls"] = []
        result = rank_payload(payload)
        self.assertEqual(result["ranked"], [])
        self.assertEqual(result["unranked"][0]["reason"], "insufficient_evidence")

    def test_tie_order_is_deterministic(self):
        result = rank_payload(load_fixture("ties.json"))
        self.assertEqual([item["name"] for item in result["ranked"]], ["Alpha Product", "Beta Product"])

    def test_invalid_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            rank_payload({"task": {}, "candidates": [{"name": "missing url"}]})


if __name__ == "__main__":
    unittest.main()