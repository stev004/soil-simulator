"""Phase 9.7 transparent manifest correction and exact artifact hashing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import cast


def sha256_file(path: str | Path) -> str:
    """Hash exact file bytes using SHA-256."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_set_digest(files: dict[str, str]) -> str:
    """Hash the canonical path-to-hash mapping."""
    payload = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def corrected_phase96_manifest(root: str | Path) -> dict[str, object]:
    """Rehash the historical manifest paths without modifying historical artifacts."""
    repository = Path(root)
    historical_path = repository / "outputs/phase96_v0.9.6/artifact_hashes.json"
    historical = cast(dict[str, object], json.loads(historical_path.read_text(encoding="utf-8")))
    old_files = cast(dict[str, str], historical["files"])
    current_files: dict[str, str] = {}
    changes: list[dict[str, object]] = []
    for relative, old_hash in sorted(old_files.items()):
        path = repository / relative
        current_hash = sha256_file(path)
        current_files[relative] = current_hash
        if current_hash != old_hash:
            reason = "Phase 9.7 source/dependency/documentation update"
            if relative == "docs/AUDIT_soil_simulator_v0.9.0.md":
                reason = (
                    "the independent v0.9.0 audit document was restored or updated after the "
                    "Phase 9.6 manifest freeze; current bytes are preserved"
                )
            changes.append(
                {
                    "path": relative,
                    "historical_sha256": old_hash,
                    "current_sha256": current_hash,
                    "reason": reason,
                }
            )
    return {
        "version": "0.9.7",
        "manifest_role": "transparent correction of Phase 9.6 current-byte replay",
        "historical_manifest_path": historical_path.relative_to(repository).as_posix(),
        "historical_manifest_sha256": sha256_file(historical_path),
        "historical_artifact_set_sha256": historical["artifact_set_sha256"],
        "historical_manifest_modified": False,
        "historical_v0_9_0_artifacts_modified": False,
        "changes_since_phase96_freeze": changes,
        "files": current_files,
        "artifact_set_sha256": canonical_set_digest(current_files),
    }


def artifact_manifest(
    root: str | Path,
    paths: Iterable[str | Path],
    *,
    version: str = "0.9.7",
) -> dict[str, object]:
    """Return exact hashes for a stable explicit artifact set."""
    repository = Path(root)
    files = {
        Path(path).relative_to(repository).as_posix(): sha256_file(path)
        for path in sorted((Path(path) for path in paths), key=lambda item: item.as_posix())
    }
    return {
        "version": version,
        "files": files,
        "artifact_set_sha256": canonical_set_digest(files),
    }


def verify_manifest(root: str | Path, manifest: dict[str, object]) -> list[str]:
    """Return mismatching entries; an empty list is an exact replay pass."""
    repository = Path(root)
    files = cast(dict[str, str], manifest.get("files", {}))
    return [
        relative
        for relative, expected in files.items()
        if not (repository / relative).is_file() or sha256_file(repository / relative) != expected
    ]
