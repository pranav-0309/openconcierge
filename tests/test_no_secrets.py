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