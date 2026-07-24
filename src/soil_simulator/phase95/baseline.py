"""Byte-level preservation checks for the audited v0.9.0 baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def verify_frozen_baseline(
    repository_root: str | Path, manifest_path: str | Path
) -> dict[str, object]:
    """Verify every declared historical artifact without modifying it."""
    root = Path(repository_root)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    directory = root / str(manifest["directory"])
    expected = dict(manifest["files"])
    observed_files = {
        path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file()
    }
    checks: dict[str, dict[str, object]] = {}
    for relative, digest in sorted(expected.items()):
        path = directory / relative
        observed = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        checks[relative] = {
            "expected_sha256": digest,
            "observed_sha256": observed,
            "matches": observed == digest,
        }
    undeclared = sorted(observed_files - set(expected))
    missing = sorted(set(expected) - observed_files)
    return {
        "baseline": manifest["baseline"],
        "directory": str(directory),
        "checks": checks,
        "missing": missing,
        "undeclared": undeclared,
        "passed": (
            all(bool(check["matches"]) for check in checks.values())
            and not missing
            and not undeclared
        ),
    }
