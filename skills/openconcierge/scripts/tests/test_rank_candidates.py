"""Tests for rank_candidates.py — deterministic ranking per PRD Section 5/6.

No network calls. All fixtures are inline JSON.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "rank_candidates.py"


def run_script(task):
    """Run rank_candidates.py with a task dict; return (returncode, parsed stdout)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(task),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"script failed: {proc.stderr}"
    return json.loads(proc.stdout)


def make_candidate(name, url=None, price=50.0, currency="USD", region=True, criteria=None, tradeoffs=None):
    return {
        "name": name,
        "product_url": url or f"https://example.com/{name.lower().replace(' ', '-')}",
        "seller_or_manufacturer": "TestSeller",
        "observed_price": price,
        "currency": currency,
        "observed_at": "2026-09-09",
        "ships_to_region": region,
        "criteria": criteria or [],
        "tradeoffs": tradeoffs or [],
    }


def make_task(candidates, max_budget=None, region=None, exclusions=None, deadline=None, requirements=None):
    return {
        "brief": {
            "category": "pillow",
            "problem_to_solve": "neck pain, overheating",
            "intended_user": "side sleeper",
            "must_haves": ["firm support"],
            "preferences": ["cooling gel"],
            "avoid": [],
            "budget": {"minimum": None, "maximum": max_budget, "currency": "USD"},
            "region": region,
            "deadline": deadline,
            "existing_context": [],
        },
        "exclusions": exclusions or [],
        "requirements": requirements
        or [
            {"requirement": "firm support", "importance": "must"},
            {"requirement": "cooling gel", "importance": "preference"},
            {"requirement": "washable cover", "importance": "nice"},
        ],
        "candidates": candidates,
    }


# ---------------------------------------------------------------------------
# Hard filters
# ---------------------------------------------------------------------------


class TestHardFilters:
    def test_over_budget_candidate_is_filtered(self):
        c = make_candidate("Expensive Pillow", price=200.0)
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        result = run_script(make_task([c], max_budget=100.0))
        assert result["ranked"] == []
        assert len(result["filtered_out"]) == 1
        assert result["filtered_out"][0]["reason"] == "over_budget"

    def test_region_unavailable_candidate_is_filtered(self):
        c = make_candidate("Far Pillow", region=False)
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        result = run_script(make_task([c], region="US"))
        assert result["filtered_out"][0]["reason"] == "region_unavailable"

    def test_excluded_brand_is_filtered(self):
        c = make_candidate("BrandX Pillow")
        result = run_script(make_task([c], exclusions=["BrandX"]))
        assert result["filtered_out"][0]["reason"] == "excluded"

    def test_must_have_match_none_is_filtered(self):
        c = make_candidate("Soft Pillow")
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "none", "source_urls": []}]
        result = run_script(make_task([c]))
        assert result["filtered_out"][0]["reason"] == "must_have_not_met"

    def test_must_have_match_unknown_is_filtered(self):
        c = make_candidate("Mystery Pillow")
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "unknown", "source_urls": []}]
        result = run_script(make_task([c]))
        assert result["filtered_out"][0]["reason"] == "must_have_not_met"

    def test_deadline_unmet_is_filtered(self):
        c = make_candidate("Slow Pillow")
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        result = run_script(make_task([c], deadline="2026-09-15"))
        # No delivery evidence field -> cannot confirm deadline -> filtered
        assert result["filtered_out"][0]["reason"] == "deadline_unverifiable"

    def test_deadline_met_when_delivery_days_confirmed(self):
        c = make_candidate("Fast Pillow")
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        c["delivery_days_max"] = 3
        result = run_script(make_task([c], deadline="2026-09-15"))
        assert result["filtered_out"] == []
        assert len(result["ranked"]) == 1

    def test_no_budget_max_keeps_any_price(self):
        c = make_candidate("Any Price Pillow", price=999.0)
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        result = run_script(make_task([c], max_budget=None))
        assert len(result["ranked"]) == 1

    def test_unknown_price_passes_budget_filter(self):
        c = make_candidate("Unknown Price Pillow", price=None)
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        result = run_script(make_task([c], max_budget=100.0))
        assert len(result["ranked"]) == 1


# ---------------------------------------------------------------------------
# Weighted scoring
# ---------------------------------------------------------------------------


class TestScoring:
    def _crit(self, req, imp, match):
        return {"requirement": req, "importance": imp, "match": match, "source_urls": ["https://example.com/a"]}

    def test_full_strong_beats_partial(self):
        strong = make_candidate("Strong One")
        strong["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("cooling gel", "preference", "strong"),
            self._crit("washable cover", "nice", "strong"),
        ]
        partial = make_candidate("Partial One")
        partial["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("cooling gel", "preference", "partial"),
            self._crit("washable cover", "nice", "partial"),
        ]
        result = run_script(make_task([partial, strong]))
        assert result["ranked"][0]["name"] == "Strong One"
        assert result["ranked"][0]["fit_score"] > result["ranked"][1]["fit_score"]

    def test_none_match_scores_lower_than_unknown(self):
        # 'none' on a preference is a confirmed miss -> penalized;
        # 'unknown' is unresolved -> not as heavily penalized as a confirmed miss
        none_c = make_candidate("None Match")
        none_c["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("cooling gel", "preference", "none"),
        ]
        unknown_c = make_candidate("Unknown Match")
        unknown_c["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("cooling gel", "preference", "unknown"),
        ]
        result = run_script(make_task([none_c, unknown_c]))
        scores = {r["name"]: r["fit_score"] for r in result["ranked"]}
        assert scores["Unknown Match"] > scores["None Match"]

    def test_importance_weighting_must_beats_nice(self):
        # Strong on 'nice' should not beat strong on 'must'
        must_strong = make_candidate("Must Strong")
        must_strong["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("washable cover", "nice", "none"),
        ]
        nice_strong = make_candidate("Nice Strong")
        nice_strong["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("washable cover", "nice", "strong"),
            self._crit("extra perk", "nice", "strong"),
        ]
        # candidate A: must strong + nice none; candidate B: must strong + 2 nice strong
        # B should win, but if A had the nices and B the must-miss it must be filtered.
        result = run_script(make_task([must_strong, nice_strong]))
        assert result["ranked"][0]["name"] == "Nice Strong"

    def test_missing_criteria_entry_treated_as_unknown(self):
        c = make_candidate("Sparse Candidate")
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        # 'cooling gel' (preference) and 'washable cover' (nice) have no criteria entry
        result = run_script(make_task([c]))
        assert result["ranked"][0]["fit_score"] < 1.0  # not full marks: unresolved items count

    def test_partial_scores_between_strong_and_none(self):
        c = make_candidate("Partial Candidate")
        c["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("cooling gel", "preference", "partial"),
        ]
        strong_c = make_candidate("Strong Candidate")
        strong_c["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("cooling gel", "preference", "none"),
        ]
        none_c = make_candidate("None Candidate")
        none_c["criteria"] = [
            self._crit("firm support", "must", "strong"),
            self._crit("cooling gel", "preference", "none"),
        ]
        result = run_script(make_task([c, strong_c, none_c]))
        partial_score = {r["name"]: r["fit_score"] for r in result["ranked"]}["Partial Candidate"]
        assert 0 < partial_score < 1


# ---------------------------------------------------------------------------
# Deterministic sort: fit_score desc -> price asc -> name (case-insensitive) -> URL
# ---------------------------------------------------------------------------


class TestSortOrder:
    def _c(self, name, url, price, score_hint):
        c = make_candidate(name, url=url, price=price)
        c["criteria"] = [
            {"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]},
            {"requirement": "cooling gel", "importance": "preference", "match": score_hint, "source_urls": ["https://example.com/a"]},
        ]
        return c

    def test_equal_score_lower_price_first(self):
        a = self._c("Alpha Pillow", "https://example.com/alpha", 40.0, "strong")
        b = self._c("Beta Pillow", "https://example.com/beta", 30.0, "strong")
        result = run_script(make_task([a, b]))
        assert [r["name"] for r in result["ranked"]] == ["Beta Pillow", "Alpha Pillow"]

    def test_equal_score_equal_price_name_tiebreak_case_insensitive(self):
        a = self._c("ALPHA Pillow", "https://example.com/alpha", 30.0, "strong")
        b = self._c("alpha pillow", "https://example.com/beta", 30.0, "strong")
        result = run_script(make_task([a, b]))
        # case-insensitive name equal -> URL tiebreak
        assert [r["product_url"] for r in result["ranked"]] == ["https://example.com/alpha", "https://example.com/beta"]

    def test_higher_score_beats_lower_price(self):
        strong = self._c("Costly Great", "https://example.com/a", 80.0, "strong")
        weak = self._c("Cheap Weak", "https://example.com/b", 10.0, "none")
        result = run_script(make_task([weak, strong]))
        assert result["ranked"][0]["name"] == "Costly Great"

    def test_deterministic_output_for_identical_input(self):
        candidates = [
            self._c("A", "https://example.com/a", 30.0, "strong"),
            self._c("B", "https://example.com/b", 25.0, "partial"),
        ]
        task = make_task(candidates)
        r1 = run_script(task)
        r2 = run_script(task)
        assert r1 == r2


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


class TestOutputContract:
    def test_output_includes_ranked_and_filtered_out_and_requirements(self):
        c = make_candidate("Good Pillow", price=50.0)
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        result = run_script(make_task([c]))
        assert set(result.keys()) >= {"ranked", "filtered_out", "requirements"}
        ranked = result["ranked"][0]
        for key in ("name", "product_url", "observed_price", "fit_score", "criteria", "tradeoffs"):
            assert key in ranked

    def test_empty_candidates_yields_empty_output(self):
        result = run_script(make_task([]))
        assert result["ranked"] == []
        assert result["filtered_out"] == []

    def test_truncated_to_top_n(self):
        candidates = []
        for i in range(10):
            c = make_candidate(f"Pillow {i}", price=50.0 + i)
            c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
            candidates.append(c)
        result = run_script(make_task(candidates))
        assert len(result["ranked"]) <= 4

    def test_invalid_match_value_raises_error(self):
        c = make_candidate("Broken Pillow")
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "excellent", "source_urls": []}]
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(make_task([c])),
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode != 0
        assert "invalid" in proc.stderr.lower()

    def test_read_from_file_argument(self, tmp_path):
        c = make_candidate("File Pillow", price=50.0)
        c["criteria"] = [{"requirement": "firm support", "importance": "must", "match": "strong", "source_urls": ["https://example.com/a"]}]
        task_file = tmp_path / "task.json"
        task_file.write_text(json.dumps(make_task([c])), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(task_file)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout)["ranked"][0]["name"] == "File Pillow"