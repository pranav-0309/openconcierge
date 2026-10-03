#!/usr/bin/env python3
"""Build dist/openconcierge.zip with the skill folder at the zip root.

Usage: python scripts/build_zip.py   (from the repo root)

Per the PRD: the ZIP contains the openconcierge/ folder itself at the
root (not its contents), with credentials, caches, and .git artifacts
excluded. Dependencies: Python 3 standard library only.
"""

import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "openconcierge"
DIST_ZIP = REPO_ROOT / "dist" / "openconcierge.zip"
EXCLUDE_DIRS = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", "node_modules", ".venv", "tests"}
EXCLUDE_FILES = {".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if path.name in EXCLUDE_FILES:
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def main() -> None:
    if not SKILL_DIR.is_dir():
        print(f"build_zip: skill folder not found: {SKILL_DIR}", file=sys.stderr)
        sys.exit(1)
    DIST_ZIP.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in SKILL_DIR.rglob("*") if p.is_file() and should_include(p))
    if not files:
        print("build_zip: no files found to package", file=sys.stderr)
        sys.exit(1)
    with zipfile.ZipFile(DIST_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            arcname = Path("openconcierge") / path.relative_to(SKILL_DIR)
            zf.write(path, arcname.as_posix())
    print(f"built {DIST_ZIP} ({len(files)} files, skill folder at zip root)")


if __name__ == "__main__":
    main()