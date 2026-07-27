# OpenConcierge Core Distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and test the Hermes-native OpenConcierge profile distribution, shopping skill, provider-neutral search instructions, and deterministic candidate ranking without creating a separate service.

**Architecture:** The repository is a Hermes profile distribution plus one standalone skill directory. Hermes supplies the active model, memory, web tools, MCP/plugin tools, sessions, and gateways. A dependency-free Python ranking helper receives source-backed candidate evidence from the skill, applies hard filters, and returns deterministic ranked, unranked, and rejected results.

**Tech Stack:** Markdown skill files, YAML distribution metadata, Python 3.11 standard library, `unittest`, Hermes Agent profile/skill commands.

---

## Scope and dependency

This plan implements the first independently usable subsystem. It must be complete before the bootstrapper plan begins. The bootstrapper will install the artifacts created here; it must not contain shopping logic.

The current workspace contains `PRD.md` and the approved design at `docs/superpowers/specs/2026-07-27-openconcierge-hermes-addon-design.md`, but no application code or test runner. Do not assume a package manager, framework, database, or remote repository URL.

This workspace is not currently a Git checkout. Do not create commits during implementation unless the user explicitly requests them.

## File ownership map

Create these files:

- `distribution.yaml`: Hermes profile-distribution manifest and ownership policy.
- `SOUL.md`: dedicated-profile identity and safety rules.
- `skills/openconcierge/SKILL.md`: skill metadata and executable conversational workflow.
- `skills/openconcierge/references/interviewing.md`: intent and question-selection rules.
- `skills/openconcierge/references/research-and-evidence.md`: provider-neutral search discovery and evidence rules.
- `skills/openconcierge/references/recommendations.md`: output contract and trade-off language.
- `skills/openconcierge/references/memory-and-privacy.md`: preference persistence and deletion rules.
- `skills/openconcierge/scripts/rank_candidates.py`: pure ranking/filtering implementation and CLI.
- `skills/__init__.py`: Python package marker for test imports.
- `skills/openconcierge/__init__.py`: Python package marker for skill-script imports.
- `skills/openconcierge/scripts/__init__.py`: Python package marker for the ranking helper.
- `tests/__init__.py`: standard-library test package marker.
- `tests/test_distribution_layout.py`: distribution file and metadata tests.
- `tests/test_rank_candidates.py`: ranking and filtering tests.
- `tests/fixtures/ranking/basic.json`: mixed candidate fixture.
- `tests/fixtures/ranking/unknown-evidence.json`: unknown evidence fixture.
- `tests/fixtures/ranking/ties.json`: deterministic tie fixture.
- `tests/test_skill_contract.py`: skill frontmatter and required-section tests.
- `tests/test_no_secrets.py`: repository secret/state exclusion tests.

Do not create a `config.yaml`, database schema, MCP server, web application, or provider adapter in this plan.

## Task 1: Establish the repository layout and a failing distribution test

**Files:**
- Create: `skills/__init__.py`
- Create: `skills/openconcierge/__init__.py`
- Create: `skills/openconcierge/scripts/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_distribution_layout.py`
- Create: `tests/test_no_secrets.py`
- Create: `tests/test_skill_contract.py`
- Create: `tests/fixtures/ranking/basic.json`
- Create: `tests/fixtures/ranking/unknown-evidence.json`
- Create: `tests/fixtures/ranking/ties.json`

- [ ] **Step 1: Write the failing layout test**

Create `tests/test_distribution_layout.py` with this contract:

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DistributionLayoutTests(unittest.TestCase):
    def test_required_distribution_files_exist(self):
        required = (
            ROOT / "distribution.yaml",
            ROOT / "SOUL.md",
            ROOT / "skills" / "openconcierge" / "SKILL.md",
            ROOT / "skills" / "openconcierge" / "references" / "interviewing.md",
            ROOT / "skills" / "openconcierge" / "references" / "research-and-evidence.md",
            ROOT / "skills" / "openconcierge" / "references" / "recommendations.md",
            ROOT / "skills" / "openconcierge" / "references" / "memory-and-privacy.md",
            ROOT / "skills" / "openconcierge" / "scripts" / "rank_candidates.py",
        )
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Write the repository secret/state test**

Create `tests/test_no_secrets.py`:

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    ROOT / "distribution.yaml",
    ROOT / "SOUL.md",
    ROOT / "skills",
)
FORBIDDEN_NAMES = {
    ".env",
    "auth.json",
    "state.db",
    "state.db-shm",
    "state.db-wal",
    "sessions",
    "memories",
    "logs",
}


class RepositorySafetyTests(unittest.TestCase):
    def test_distribution_source_contains_no_runtime_state_names(self):
        found = []
        for source in SOURCE_PATHS:
            paths = source.rglob("*") if source.is_dir() else (source,)
            for path in paths:
                if any(part in FORBIDDEN_NAMES for part in path.parts):
                    found.append(str(path.relative_to(ROOT)))
        self.assertEqual(found, [])

    def test_distribution_source_contains_no_common_secret_assignments(self):
        needles = tuple(name + "=" for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SERPAPI_KEY", "TAVILY_API_KEY"))
        matches = []
        for source in SOURCE_PATHS:
            paths = source.rglob("*") if source.is_dir() else (source,)
            for path in paths:
                if not path.is_file() or path.suffix in {".pyc", ".db"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for needle in needles:
                    if needle in text:
                        matches.append(f"{path.relative_to(ROOT)}:{needle}")
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Write the skill contract test**

Create `tests/test_skill_contract.py`:

```python
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "openconcierge" / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_frontmatter_has_provider_neutral_metadata(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertRegex(text, r"(?m)^name:\s*openconcierge\s*$")
        self.assertRegex(text, r"(?m)^description:\s*.+$")
        self.assertNotRegex(text, r"(?m)^\s*requires_tools:")
        self.assertNotRegex(text, r"(?m)^\s*requires_toolsets:")
        self.assertNotRegex(text, r"(?i)(requires|depends on).*(exa|tavily|serpapi|serper|brave|duckduckgo)")

    def test_skill_contains_required_workflow_sections(self):
        text = SKILL.read_text(encoding="utf-8")
        for heading in (
            "## When to Use",
            "## Clarifying Questions",
            "## Search Capability Resolution",
            "## Evidence and Ranking",
            "## Recommendation Format",
            "## Memory and Privacy",
            "## Failure Handling",
        ):
            self.assertIn(heading, text)

    def test_skill_does_not_cap_questions(self):
        text = SKILL.read_text(encoding="utf-8").lower()
        self.assertNotRegex(text, r"at most\s+[0-9]+\s+questions")
        self.assertNotIn("1–3", text)
        self.assertNotIn("1-3", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Add minimal JSON fixtures**

Create `tests/fixtures/ranking/basic.json` with one over-budget product, one valid product, and one region-excluded product. Use only `https://example.test/valid`, `https://example.test/expensive`, and `https://example.test/unavailable` URLs and this shape:

```json
{
  "task": {
    "budget": {"maximum": 100, "currency": "USD"},
    "region": "US"
  },
  "candidates": [
    {
      "name": "Valid Cooling Pillow",
      "product_url": "https://example.test/valid",
      "seller_or_manufacturer": "Example Sleep",
      "observed_price": 79,
      "currency": "USD",
      "observed_at": "2026-07-27",
      "ships_to_region": true,
      "criteria": [
        {"requirement": "cooling", "importance": "core", "match": "strong", "source_urls": ["https://example.test/valid"]},
        {"requirement": "side-sleeper support", "importance": "preference", "match": "partial", "source_urls": ["https://example.test/valid"]},
        {"requirement": "latex-free", "importance": "must", "match": "strong", "source_urls": ["https://example.test/valid"]}
      ],
      "tradeoffs": ["Needs periodic refluffing"]
    },
    {
      "name": "Over Budget Pillow",
      "product_url": "https://example.test/expensive",
      "seller_or_manufacturer": "Example Sleep",
      "observed_price": 140,
      "currency": "USD",
      "observed_at": "2026-07-27",
      "ships_to_region": true,
      "criteria": [],
      "tradeoffs": []
    },
    {
      "name": "Unavailable Pillow",
      "product_url": "https://example.test/unavailable",
      "seller_or_manufacturer": "Example Sleep",
      "observed_price": 80,
      "currency": "USD",
      "observed_at": "2026-07-27",
      "ships_to_region": false,
      "criteria": [],
      "tradeoffs": []
    }
  ]
}
```

Create `tests/fixtures/ranking/unknown-evidence.json`:

```json
{
  "task": {
    "budget": {"maximum": 100, "currency": "USD"},
    "region": "US"
  },
  "candidates": [
    {
      "name": "Unverified Pillow",
      "product_url": "https://example.test/unverified",
      "seller_or_manufacturer": "Example Sleep",
      "observed_price": 79,
      "currency": "USD",
      "observed_at": "2026-07-27",
      "ships_to_region": "unknown",
      "criteria": [
        {"requirement": "latex-free", "importance": "must", "match": "unknown", "source_urls": []}
      ],
      "tradeoffs": []
    }
  ]
}
```

Create `tests/fixtures/ranking/ties.json`:

```json
{
  "task": {"budget": {}, "region": null},
  "candidates": [
    {
      "name": "Beta Product",
      "product_url": "https://example.test/beta",
      "seller_or_manufacturer": "Example",
      "observed_price": 50,
      "currency": "USD",
      "observed_at": "2026-07-27",
      "ships_to_region": true,
      "criteria": [
        {"requirement": "core fit", "importance": "core", "match": "strong", "source_urls": ["https://example.test/beta"]}
      ],
      "tradeoffs": []
    },
    {
      "name": "Alpha Product",
      "product_url": "https://example.test/alpha",
      "seller_or_manufacturer": "Example",
      "observed_price": 50,
      "currency": "USD",
      "observed_at": "2026-07-27",
      "ships_to_region": true,
      "criteria": [
        {"requirement": "core fit", "importance": "core", "match": "strong", "source_urls": ["https://example.test/alpha"]}
      ],
      "tradeoffs": []
    }
  ]
}
```

Keep all fixture URLs non-networking; the ranking helper must never open them.

- [ ] **Step 5: Create empty Python package markers**

Create empty files at `skills/__init__.py`, `skills/openconcierge/__init__.py`, `skills/openconcierge/scripts/__init__.py`, and `tests/__init__.py`. They contain no imports or runtime behavior.

- [ ] **Step 6: Run the tests and verify the intended red state**

Run:

```text
python -m unittest discover -s tests -v
```

Expected: FAIL because the distribution files and skill have not been created. No test may make a network request.

## Task 2: Define and implement the deterministic ranking contract

**Files:**
- Test: `tests/test_rank_candidates.py`
- Modify: `tests/fixtures/ranking/basic.json`
- Modify: `tests/fixtures/ranking/unknown-evidence.json`
- Modify: `tests/fixtures/ranking/ties.json`
- Create: `skills/openconcierge/scripts/rank_candidates.py`

- [ ] **Step 1: Write the failing ranking tests**

Create `tests/test_rank_candidates.py` against this public API:

```python
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
```

- [ ] **Step 2: Run only the ranking tests and confirm they fail**

Run:

```text
python -m unittest tests.test_rank_candidates -v
```

Expected: FAIL with an import error for `skills.openconcierge.scripts.rank_candidates`.

- [ ] **Step 3: Implement the exact ranking API**

Create `skills/openconcierge/scripts/rank_candidates.py` with these stable symbols and behaviors:

```python
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
```

Replace the ellipsis with the minimal implementation using these rules:

1. Validate `payload["task"]` is a mapping and `payload["candidates"]` is a sequence of mappings.
2. Require every candidate to have a nonempty `name` and an `http` or `https` `product_url`; raise `ValueError` for malformed input rather than silently dropping it.
3. Reject a candidate with `observed_price > task.budget.maximum` as `over_budget`.
4. Reject `ships_to_region is False` as `region_unavailable`.
5. Normalize every criterion with an `importance` in `must`, `core`, `preference`, or `nice` and a `match` in `strong`, `partial`, `none`, or `unknown`.
6. Convert `strong` and `partial` to `unknown` when `source_urls` is empty or contains no `http`/`https` URL.
7. Reject a `must` criterion unless its normalized match is `strong`; use `missing_must_have` for `none`/`partial` and `unverified_must_have` for `unknown`.
8. Put candidates with an unknown regional shipping result, unknown budget price when a maximum exists, or unverified non-must evidence into `unranked` with one stable reason. Do not include them in `ranked`.
9. Score only `core`, `preference`, and `nice` criteria. For each criterion, add `MATCH_VALUES[match] * IMPORTANCE_WEIGHTS[importance]` to earned points and the weight to possible points. Use `0.0` when no scored criteria exist.
10. Return each ranked record with the original candidate fields plus `fit_score` rounded to four decimal places and a `score_breakdown` mapping requirement names to their weighted contribution.
11. Sort ranked records by descending `fit_score`, then known price ascending, then case-insensitive name, then URL. Sort rejected and unranked records by case-insensitive name.
12. Return exactly `{"ranked": [], "unranked": [], "rejected": []}` with each array populated according to the rules above.

Do not import a third-party URL, YAML, validation, or data-science package.

- [ ] **Step 4: Run the ranking tests and verify green**

Run:

```text
python -m unittest tests.test_rank_candidates -v
```

Expected: PASS for hard filters, evidence handling, tie ordering, and malformed input.

- [ ] **Step 5: Run the CLI against a fixture**

Run:

```text
python skills/openconcierge/scripts/rank_candidates.py --input tests/fixtures/ranking/basic.json
```

Expected: JSON on stdout with one `ranked` record named `Valid Cooling Pillow`, two `rejected` records, and no network activity.

## Task 3: Author the provider-neutral skill workflow

**Files:**
- Create: `skills/openconcierge/SKILL.md`
- Create: `skills/openconcierge/references/interviewing.md`
- Create: `skills/openconcierge/references/research-and-evidence.md`
- Create: `skills/openconcierge/references/recommendations.md`
- Create: `skills/openconcierge/references/memory-and-privacy.md`
- Test: `tests/test_skill_contract.py`

- [ ] **Step 1: Write the frontmatter and section contract**

Start `SKILL.md` with this frontmatter. Do not add `requires_tools`, `requires_toolsets`, provider-specific API keys, or a provider allowlist:

```markdown
---
name: openconcierge
description: Research and compare products through a focused, source-backed shopping conversation.
version: 0.1.0
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [shopping, research, recommendations, products, comparison]
---
```

Create the required headings in this order:

```markdown
# OpenConcierge

## When to Use
## Clarifying Questions
## Search Capability Resolution
## Candidate Evidence
## Evidence and Ranking
## Recommendation Format
## Memory and Privacy
## Failure Handling
## Verification
```

- [ ] **Step 2: Write the question-selection rules**

In `SKILL.md` and `references/interviewing.md`, encode that there is no numeric question cap. The agent asks only when an answer can change qualification, ranking, budget/region, contradiction resolution, safety, or product type. It must not repeat known information, ask generic intake questions, or continue after a useful search is possible. It must accept “use your judgment,” state assumptions, and allow requirement changes mid-task.

Use this decision block verbatim as the operational gate:

```text
Before asking a question, identify the decision it changes. If the answer would not change eligibility, ranking, safety, regional availability, budget, or product type, do not ask it. Stop asking when the brief is sufficient to search. Never ask for a known value again.
```

- [ ] **Step 3: Write provider-neutral search resolution**

In `references/research-and-evidence.md`, instruct the agent to:

1. Use Hermes `web_search` first when it is available; Hermes selects the configured backend through its own `web.search_backend`/`web.backend` settings.
2. Use `web_extract` for direct-page verification when available.
3. If canonical search is absent or insufficient, call `tool_search` with a capability query such as `web search product search marketplace search`, then call `tool_describe` and `tool_call` for a compatible MCP/plugin tool.
4. Accept any discoverable tool that takes a query and returns inspectable result URLs; do not match only on brand names.
5. Use an installed fallback search skill when Hermes makes one available.
6. Prefer the canonical backend and use one configured fallback after failure; do not fan out across all providers.
7. Never ask for Exa, Tavily, SerpAPI, Serper, Brave, DuckDuckGo, or another key when Hermes already exposes the integration.

Include this explicit non-contract:

```text
The skill does not require `web_search`, a named provider, a particular MCP server, or a provider API key in its metadata. Search capability is selected at runtime from the active Hermes profile.
```

- [ ] **Step 4: Write evidence normalization instructions**

Require the model to produce the candidate structure consumed by `rank_candidates.py`:

```yaml
candidate:
  name: string
  product_url: string
  seller_or_manufacturer: string
  observed_price: number | null
  currency: string | null
  observed_at: date
  ships_to_region: true | false | unknown
  criteria:
    - requirement: string
      importance: must | core | preference | nice
      match: strong | partial | none | unknown
      source_urls: string[]
  tradeoffs: string[]
```

Require source URLs for every positive match. Require direct product or manufacturer verification when possible. Mark inaccessible, stale, conflicting, or absent facts as unknown. Do not present an unknown must-have as satisfied.

- [ ] **Step 5: Write recommendation and memory instructions**

The recommendation format must contain the understood need, assumptions, 2–4 qualified options when available, observed price/currency/date, seller, rationale, trade-offs, unverified details, direct links, and a comparison explaining the top choice. If fewer than two candidates qualify, explain why instead of manufacturing a shortlist.

The memory reference must require explicit confirmation before storing stable preferences. It must not persist transient tasks, browsing history, or sensitive health/allergy/disability constraints unless explicitly requested. It must support these `/openconcierge` arguments:

```text
show preferences
correct preference
forget preference
forget all preferences
```

- [ ] **Step 6: Write failure and verification instructions**

The skill must explain that no compatible search capability means live research is unavailable and direct the user to Hermes Desktop tools, skills, or MCP settings without naming a mandatory provider. It may try one already-configured fallback after a search failure; it must never fabricate results.

Verification must be passive: confirm the candidate evidence has source URLs, hard constraints were applied, unknowns are labeled, and output has trade-offs. Do not instruct the skill to run an installation smoke test.

- [ ] **Step 7: Run the skill contract tests**

Run:

```text
python -m unittest tests.test_skill_contract -v
```

Expected: PASS, including the checks that no provider-specific tool requirement exists and no numeric question cap appears.

## Task 4: Add the dedicated-profile identity and distribution manifest

**Files:**
- Create: `SOUL.md`
- Create: `distribution.yaml`
- Modify: `tests/test_distribution_layout.py`

- [ ] **Step 1: Write the manifest**

Create `distribution.yaml` with exactly this initial ownership policy:

```yaml
name: openconcierge
version: 0.1.0
description: A source-backed personal shopping concierge for Hermes Agent
hermes_requires: ">=0.12.0"
distribution_owned:
  - distribution.yaml
  - SOUL.md
  - skills/openconcierge/
```

Do not add `env_requires`, `config.yaml`, `mcp.json`, cron entries, or provider-specific settings.

- [ ] **Step 2: Write the dedicated profile identity**

Create `SOUL.md` with these operational commitments:

```markdown
# OpenConcierge

You are a patient, evidence-oriented personal shopping concierge.

Learn the user's actual intent before researching. Ask only questions whose answers can change eligibility, ranking, budget, region, safety, or product type. Never invent products, prices, availability, ratings, specifications, or source claims. Separate verified facts from inferences. Show trade-offs and uncertainty plainly. Do not pressure the user, transact, reserve inventory, or claim that a volatile price or stock status is permanent.

Use the active Hermes search capabilities rather than requesting a particular provider. Respect the user's configured model, tools, channels, memory, and privacy settings. Store stable shopping preferences only after the user confirms them, and do not persist sensitive constraints unless explicitly requested.
```

- [ ] **Step 3: Extend the layout tests**

Assert that `distribution.yaml` contains `name: openconcierge`, `version: 0.1.0`, `hermes_requires: ">=0.12.0"`, and all three owned paths. Assert that `config.yaml`, `.env`, `auth.json`, `mcp.json`, and cron files are not part of the distribution tree.

- [ ] **Step 4: Run the complete unit suite**

Run:

```text
python -m unittest discover -s tests -v
```

Expected: PASS with no network access.

## Task 5: Validate native Hermes installation and standalone skill packaging

**Files:**
- No repository files. These are manual native-Hermes integration checks performed in a temporary Hermes home.

- [ ] **Step 1: Run a local profile-distribution install in a temporary Hermes home**

Only run this when the `hermes` command is installed. Set an isolated home and install from the current directory:

```text
TEMP_HERMES_HOME="$(mktemp -d)"
export HERMES_HOME="$TEMP_HERMES_HOME"
hermes profile install . --name openconcierge-test --alias --yes
```

On PowerShell, use:

```powershell
$env:HERMES_HOME = (New-Item -ItemType Directory (Join-Path $env:TEMP "openconcierge-hermes-test")).FullName
hermes profile install (Get-Location).Path --name openconcierge-test --alias --yes
```

Expected: Hermes creates `openconcierge-test`, copies `SOUL.md` and `skills/openconcierge/`, and does not create OpenConcierge credentials or runtime state in the source repository.

- [ ] **Step 2: Verify profile ownership and discovery without a model call**

Run:

```text
hermes profile show openconcierge-test
hermes -p openconcierge-test skills list --source all --enabled-only
hermes -p openconcierge-test tools list --platform cli
```

Expected: the profile exists, `openconcierge` is listed, and tool output is inspected without sending a prompt. A missing web tool is a warning, not a reason to add a provider dependency.

- [ ] **Step 3: Verify update preservation**

Create a sentinel file under the temporary profile's `local/` directory and a sentinel memory/session fixture, then run:

```text
hermes profile update openconcierge-test --yes
```

Expected: distribution-owned files update, while `.env`, auth, memories, sessions, `local/`, and unrelated user skills remain untouched. Do not use a real credential or live gateway token.

- [ ] **Step 4: Verify standalone skill installation from a local HTTP fixture**

Serve the repository with Python's standard library in a temporary terminal:

```text
python -m http.server 8765 --directory .
```

In a separate temporary Hermes home, create a clean profile and install the skill from the served `SKILL.md` URL:

```text
TEMP_SKILL_HERMES_HOME="$(mktemp -d)"
export HERMES_HOME="$TEMP_SKILL_HERMES_HOME"
hermes profile create existing-test --no-skills
hermes -p existing-test skills install http://127.0.0.1:8765/skills/openconcierge/SKILL.md --name openconcierge --yes
rm -rf "$TEMP_SKILL_HERMES_HOME"
```

Expected: the existing profile's `SOUL.md`, provider settings, memory, and gateway configuration remain unchanged while the skill becomes visible. Stop the local server after the check and remove the first `TEMP_HERMES_HOME` directory.

- [ ] **Step 5: Verify publication command syntax without publishing secrets**

After the repository is ready for release, inspect the skill first and publish only the skill directory through Hermes's supported command:

```text
hermes skills inspect skills/openconcierge
hermes skills publish skills/openconcierge
```

The release operator must review the generated manifest and confirm that no `.env`, `auth.json`, sessions, memories, or credentials are included before making the skill public.

## Task 6: Final core acceptance checks

- [ ] **Step 1: Run the full local suite**

Run:

```text
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run static syntax checks**

Run:

```text
python -m py_compile skills/openconcierge/scripts/rank_candidates.py
```

Expected: exit code `0` and no generated `.pyc` files committed to the source tree.

- [ ] **Step 3: Inspect the changed file list**

Run:

```text
python -c "from pathlib import Path; print('\\n'.join(sorted(str(p) for p in Path('.').rglob('*') if p.is_file() and '__pycache__' not in p.parts)))"
```

Expected: only the distribution, skill, ranking code, fixtures, and tests listed in this plan are present. Remove generated caches before handing the subsystem to the bootstrapper plan.

## Core subsystem definition of done

- The distribution installs as a Hermes profile from a local source.
- The same skill installs into an existing profile without changing its identity or gateway.
- Ranking is deterministic, source-aware, hard-constraint-first, and unit-tested.
- Search instructions reuse canonical Hermes search, fallback skills, and discoverable MCP/plugin tools without provider-specific metadata.
- Memory instructions require explicit confirmation and support namespaced deletion.
- No OpenConcierge service, provider adapter, database, or secret is introduced.
