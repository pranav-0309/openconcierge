#!/usr/bin/env python3
"""OpenConcierge deterministic ranking helper.

Dependencies: Python 3 standard library only (json, sys, datetime, argparse
via plain sys.argv parsing). No network access, no third-party packages.

Usage:
    python3 rank_candidates.py <task.json>     # task file argument
    ... | python3 rank_candidates.py           # or JSON on stdin

Input: a JSON task object:
    {
      "brief": { ..., "budget": {"maximum": ..., "currency": ...},
                 "region": ..., "avoid": [...], "deadline": ... },
      "exclusions": ["optional", "extra", "terms"],
      "requirements": [
        {"requirement": "...", "importance": "must|core|preference|nice"}
      ],
      "candidates": [ { candidate evidence objects per the PRD data model } ]
    }

Method (identical to the prose specification in references/recommendation.md):
    1. Hard filters: budget maximum, region availability, exclusions,
       must-have requirements, delivery deadline.
    2. Weighted soft scoring:
       importance weights: must=40, core=30, preference=20, nice=10
       match values:      strong=1.0, partial=0.5, unknown=0.25, none=0.0
       fit_score = sum(weight * match_value) / sum(weight over ALL requirements)
       A requirement with no criteria entry counts as "unknown".
    3. Sort: fit_score desc -> price asc (unknown price last) ->
       name asc (case-insensitive) -> URL asc. Top 4 returned.

Output: JSON {"ranked": [...], "filtered_out": [{"name","reason"}],
             "requirements": [...]} on stdout.
"""

import json
import sys
from datetime import date, datetime, timedelta

IMPORTANCE_WEIGHTS = {"must": 40, "core": 30, "preference": 20, "nice": 10}
MATCH_VALUES = {"strong": 1.0, "partial": 0.5, "unknown": 0.25, "none": 0.0}
TOP_N = 4
VALID_IMPORTANCE = set(IMPORTANCE_WEIGHTS)
VALID_MATCH = set(MATCH_VALUES)


def die(msg):
    print(f"rank_candidates: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_deadline(value):
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("date") or value.get("by") or value.get("deadline")
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def criteria_by_requirement(candidate):
    mapped = {}
    for entry in candidate.get("criteria", []):
        req = entry.get("requirement", "")
        match = entry.get("match")
        if match not in VALID_MATCH:
            die(f"invalid match value {match!r} for requirement {req!r} "
                f"(candidate {candidate.get('name', '?')!r}); "
                f"expected one of {sorted(VALID_MATCH)}")
        mapped[req] = entry
    return mapped


def hard_filter(candidate, task):
    """Return a rejection reason string, or None if the candidate passes."""
    brief = task.get("brief", {})
    budget = brief.get("budget", {}) or {}
    max_budget = budget.get("maximum")
    price = candidate.get("observed_price")

    if max_budget is not None and price is not None and price > max_budget:
        return "over_budget"

    region = brief.get("region")
    if region and candidate.get("ships_to_region") is False:
        return "region_unavailable"

    exclusion_terms = list(brief.get("avoid") or []) + list(task.get("exclusions") or [])
    haystack = f"{candidate.get('name', '')} {candidate.get('seller_or_manufacturer', '')}".lower()
    for term in exclusion_terms:
        if term and str(term).lower() in haystack:
            return "excluded"

    criteria = criteria_by_requirement(candidate)
    for req in task.get("requirements", []):
        if req.get("importance") != "must":
            continue
        entry = criteria.get(req["requirement"])
        match = entry.get("match") if entry else "unknown"
        if match not in ("strong", "partial"):
            return "must_have_not_met"

    deadline = parse_deadline(brief.get("deadline"))
    if deadline is not None:
        delivery_days = candidate.get("delivery_days_max")
        observed = candidate.get("observed_at")
        if delivery_days is None or observed is None:
            return "deadline_unverifiable"
        observed_date = parse_deadline(observed)
        if observed_date is None:
            return "deadline_unverifiable"
        arrival = observed_date + timedelta(days=int(delivery_days))
        if arrival > deadline:
            return "deadline_unmet"

    return None


def fit_score(candidate, requirements):
    criteria = criteria_by_requirement(candidate)
    total_weight = 0
    earned = 0.0
    for req in requirements:
        importance = req.get("importance")
        if importance not in VALID_IMPORTANCE:
            die(f"invalid importance {importance!r} for requirement "
                f"{req.get('requirement')!r}; expected one of {sorted(VALID_IMPORTANCE)}")
        weight = IMPORTANCE_WEIGHTS[importance]
        total_weight += weight
        entry = criteria.get(req["requirement"])
        match = entry.get("match") if entry else "unknown"
        earned += weight * MATCH_VALUES[match]
    if total_weight == 0:
        return 0.0
    return round(earned / total_weight, 4)


def sort_key(candidate):
    price = candidate.get("observed_price")
    price_sort = price if price is not None else float("inf")
    return (
        -candidate["fit_score"],
        price_sort,
        candidate.get("name", "").casefold(),
        candidate.get("product_url", ""),
    )


def rank(task):
    requirements = task.get("requirements", [])
    candidates = task.get("candidates", [])
    ranked = []
    filtered_out = []
    for candidate in candidates:
        reason = hard_filter(candidate, task)
        if reason is not None:
            filtered_out.append({"name": candidate.get("name", "?"), "reason": reason})
            continue
        scored = dict(candidate)
        scored["fit_score"] = fit_score(candidate, requirements)
        ranked.append(scored)
    ranked.sort(key=sort_key)
    return {
        "ranked": ranked[:TOP_N],
        "filtered_out": filtered_out,
        "requirements": requirements,
    }


def main():
    if len(sys.argv) > 2:
        die("usage: rank_candidates.py [task.json] (or JSON on stdin)")
    if len(sys.argv) == 2:
        try:
            with open(sys.argv[1], encoding="utf-8") as fh:
                task = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            die(f"cannot read task file: {exc}")
    else:
        try:
            task = json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            die(f"cannot parse JSON from stdin: {exc}")
    if not isinstance(task, dict):
        die("task must be a JSON object")
    result = rank(task)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()