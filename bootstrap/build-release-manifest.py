"""Generate ``bootstrap/release.json`` for OpenConcierge.

The release job and local development both run this script to produce the
metadata file consumed by ``install.sh`` and ``install.ps1``. It validates
that production sources use ``https://``, accepts absolute local paths for
development, requires a semantic version, and refuses to overwrite an
existing manifest unless ``--force`` is supplied. Writes are atomic so a
crash mid-write never leaves a partial ``release.json`` behind.

Only the standard library is used.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def _looks_like_url(value: str) -> bool:
    """Return ``True`` when ``value`` starts with a known URL scheme.

    Restricting the check to ``http://`` and ``https://`` avoids
    ``urlparse`` mis-parsing Windows drive letters (``C:\\path``) as
    ``scheme='c'`` while still rejecting ``http://`` and any other
    explicit scheme.
    """
    return value.startswith(("http://", "https://"))


def _validate_url(value: str, *, field: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme == "https":
        if not parsed.netloc:
            raise ValueError(
                f"{field} https URL is missing a host: {value!r}"
            )
        return
    raise ValueError(
        f"{field} must use https for production release; got {value!r}"
    )


def _validate_distribution_source(value: str) -> None:
    if not value:
        raise ValueError("distribution_source must be a non-empty string")
    if _looks_like_url(value):
        _validate_url(value, field="distribution_source")


def _validate_skill_source(value: str) -> None:
    if not value:
        raise ValueError("skill_source must be a non-empty string")
    if _looks_like_url(value):
        _validate_url(value, field="skill_source")


def _validate_version(value: str) -> None:
    if not value:
        raise ValueError("version must be a non-empty string")
    if not SEMVER_PATTERN.match(value):
        raise ValueError(
            f"version must be a semantic version like '0.1.0'; got {value!r}"
        )


def build_manifest(
    distribution_source: str, skill_source: str, version: str
) -> dict[str, str]:
    """Validate and return release metadata for the bootstrap scripts.

    ``distribution_source`` and ``skill_source`` must be either an ``https``
    URL (required for production release) or a local development value
    (relative or absolute path for ``distribution_source``; relative or
    absolute path or plain identifier for ``skill_source``). Empty values
    and ``http://`` URLs are rejected. ``version`` must match
    ``MAJOR.MINOR.PATCH``.
    """
    _validate_distribution_source(distribution_source)
    _validate_skill_source(skill_source)
    _validate_version(version)
    return {
        "distribution_source": distribution_source,
        "skill_source": skill_source,
        "version": version,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate bootstrap/release.json with validated "
            "distribution and skill sources."
        )
    )
    parser.add_argument(
        "--distribution-source",
        required=True,
        help="HTTPS URL (production) or absolute/relative local path (dev).",
    )
    parser.add_argument(
        "--skill-source",
        required=True,
        help=(
            "HTTPS URL (production), local path, or plain skill identifier "
            "such as 'openconcierge'."
        ),
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Semantic version such as '0.1.0'.",
    )
    parser.add_argument(
        "--output",
        default="bootstrap/release.json",
        help="Destination path for the release.json file (default: bootstrap/release.json).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the destination file if it already exists.",
    )
    return parser.parse_args(argv)


def _atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via a sibling temp file then rename.

    Uses ``pathlib.Path.replace`` which delegates to ``os.replace`` so the
    swap is atomic on the same filesystem on both POSIX and Windows. If the
    rename fails, the temp file is cleaned up.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        manifest = build_manifest(
            args.distribution_source, args.skill_source, args.version
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(
            f"error: {output_path} already exists; pass --force to overwrite.",
            file=sys.stderr,
        )
        return 3

    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _atomic_write_text(output_path, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())