from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from urllib.parse import urlparse

MATCH_VALUES = {"strong": 1.0, "partial": 0.5, "none": 0.0, "unknown": 0.0}
IMPORTANCE_WEIGHTS = {"core": 3, "preference": 2, "nice": 1}


def rank_payload(payload: Mapping[str, object]) -> dict[str, list[dict[str, object]]]:
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    task = payload.get("task")
    candidates = payload.get("candidates")
    if not isinstance(task, Mapping):
        raise ValueError("task must be an object")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise ValueError("candidates must be an array")

    budget = task.get("budget")
    maximum = budget.get("maximum") if isinstance(budget, Mapping) else None
    region_required = bool(task.get("region"))
    ranked = []
    unranked = []
    rejected = []

    def is_url(value):
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    for raw in candidates:
        if not isinstance(raw, Mapping):
            raise ValueError("each candidate must be an object")
        name = raw.get("name")
        product_url = raw.get("product_url")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("candidate name is required")
        if not isinstance(product_url, str) or not is_url(product_url):
            raise ValueError(f"candidate {name!r} has an invalid product_url")
        criteria = raw.get("criteria", [])
        if not isinstance(criteria, Sequence) or isinstance(criteria, (str, bytes)):
            raise ValueError(f"candidate {name!r} criteria must be an array")

        normalized = []
        for criterion in criteria:
            if not isinstance(criterion, Mapping):
                raise ValueError(f"candidate {name!r} has an invalid criterion")
            importance = criterion.get("importance")
            match = criterion.get("match")
            requirement = criterion.get("requirement")
            sources = criterion.get("source_urls", [])
            if importance not in {"must", "core", "preference", "nice"}:
                raise ValueError(f"candidate {name!r} has an invalid criterion importance")
            if match not in MATCH_VALUES:
                raise ValueError(f"candidate {name!r} has an invalid criterion match")
            if not isinstance(requirement, str) or not requirement.strip():
                raise ValueError(f"candidate {name!r} has an invalid requirement")
            if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
                raise ValueError(f"candidate {name!r} source_urls must be an array")
            usable_sources = [source for source in sources if isinstance(source, str) and is_url(source)]
            if match in {"strong", "partial"} and not usable_sources:
                match = "unknown"
            normalized.append({
                "requirement": requirement,
                "importance": importance,
                "match": match,
                "source_urls": usable_sources,
            })

        price = raw.get("observed_price")
        if isinstance(maximum, (int, float)) and isinstance(price, (int, float)) and price > maximum:
            rejected.append({"name": name, "product_url": product_url, "reason": "over_budget"})
            continue
        if raw.get("ships_to_region") is False:
            rejected.append({"name": name, "product_url": product_url, "reason": "region_unavailable"})
            continue

        must_failure = next((item for item in normalized if item["importance"] == "must" and item["match"] != "strong"), None)
        if must_failure is not None:
            reason = "unverified_must_have" if must_failure["match"] == "unknown" else "missing_must_have"
            unranked.append({"name": name, "product_url": product_url, "reason": reason})
            continue
        if region_required and raw.get("ships_to_region") == "unknown":
            unranked.append({"name": name, "product_url": product_url, "reason": "region_unverified"})
            continue
        if isinstance(maximum, (int, float)) and price is None:
            unranked.append({"name": name, "product_url": product_url, "reason": "price_unverified"})
            continue
        if any(item["match"] == "unknown" and item["importance"] != "must" for item in normalized):
            unranked.append({"name": name, "product_url": product_url, "reason": "insufficient_evidence"})
            continue

        possible = 0.0
        earned = 0.0
        breakdown = {}
        for item in normalized:
            weight = IMPORTANCE_WEIGHTS.get(item["importance"], 0)
            if weight == 0:
                continue
            possible += weight
            contribution = MATCH_VALUES[item["match"]] * weight
            earned += contribution
            breakdown[item["requirement"]] = contribution
        record = dict(raw)
        record["fit_score"] = round(earned / possible, 4) if possible else 0.0
        record["score_breakdown"] = breakdown
        ranked.append(record)

    def name_key(record):
        return str(record["name"]).casefold()

    def rank_key(record):
        price = record.get("observed_price")
        price_key = price if isinstance(price, (int, float)) else float("inf")
        return (-record["fit_score"], price_key, name_key(record), record["product_url"])

    ranked.sort(key=rank_key)
    rejected.sort(key=name_key)
    unranked.sort(key=name_key)
    return {"ranked": ranked, "unranked": unranked, "rejected": rejected}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="-")
    args = parser.parse_args(argv)
    source = sys.stdin if args.input == "-" else open(args.input, encoding="utf-8")
    try:
        payload = json.load(source)
        json.dump(rank_payload(payload), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    finally:
        if source is not sys.stdin:
            source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())