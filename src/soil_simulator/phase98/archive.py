"""Validate the Phase 9.8 evidence archive without recomputing science."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Any, cast

REQUIRED_TABLES = tuple(f"table_{index:02d}" for index in range(1, 10))
REQUIRED_FIGURES = tuple(f"figure_{index:02d}" for index in range(1, 12))
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
AUDIT_SOURCE_MAP = {
    "AUDIT_PHASE96_CLEAN_SLATE.md": "AUDIT_PHASE96_CLEAN_SLATE.md",
    "audit_closure_matrix_independent.csv": "phase96_finding_closure.csv",
    "recomputed_metrics.json": "phase96_recomputed_metrics.json",
    "discrepancies.md": "phase96_discrepancies.md",
    "AUDIT_PHASE97_FOCUSED.md": "AUDIT_PHASE97_FOCUSED.md",
    "phase97_finding_closure.csv": "phase97_finding_closure.csv",
    "phase97_recomputed_metrics.json": "phase97_recomputed_metrics.json",
    "phase97_discrepancies.md": "phase97_discrepancies.md",
    "sobol_findings.md": "phase97_sobol_findings.md",
    "convergence_findings.md": "phase97_convergence_findings.md",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


def _validate_manifest(root: Path, manifest_path: Path) -> list[str]:
    errors: list[str] = []
    manifest = _load_object(manifest_path)
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return [f"manifest has no entries list: {manifest_path}"]
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            errors.append(f"non-object manifest entry: {manifest_path}")
            continue
        entry = cast(dict[str, Any], raw_entry)
        relative_path = entry.get("path")
        if not isinstance(relative_path, str):
            errors.append(f"manifest entry has no path: {manifest_path}")
            continue
        target = root / relative_path
        if not target.is_file():
            errors.append(f"manifest target missing: {relative_path}")
            continue
        if entry.get("sha256") != _sha256(target):
            errors.append(f"manifest hash mismatch: {relative_path}")
        if entry.get("file_size") != target.stat().st_size:
            errors.append(f"manifest size mismatch: {relative_path}")
    return errors


def validate_tables(root: Path) -> list[str]:
    """Validate required table files, stable provenance columns and previews."""
    errors: list[str] = []
    table_directory = root / "manuscript/tables"
    for stem in REQUIRED_TABLES:
        csv_path = next(iter(sorted(table_directory.glob(f"{stem}_*.csv"))), None)
        if csv_path is None:
            errors.append(f"required table missing: {stem}")
            continue
        if not csv_path.with_suffix(".md").is_file():
            errors.append(f"table preview missing: {csv_path.name}")
        with csv_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames or []
            for required in ("source_path", "units", "audit_status"):
                if required not in fields:
                    errors.append(f"{csv_path.name} lacks {required}")
            rows = list(reader)
        if not rows:
            errors.append(f"table has no rows: {csv_path.name}")
        for row_number, row in enumerate(rows, start=2):
            for required in ("source_path", "units", "audit_status"):
                if not row.get(required, "").strip():
                    errors.append(f"{csv_path.name}:{row_number} empty {required}")
            source_path = row.get("source_path", "")
            if source_path and not (root / source_path).exists():
                errors.append(f"{csv_path.name}:{row_number} missing source {source_path}")
    return errors


def validate_figures(root: Path) -> list[str]:
    """Validate required SVG files and their explicitly indexed source files."""
    errors: list[str] = []
    figure_directory = root / "manuscript/figures"
    for stem in REQUIRED_FIGURES:
        matches = sorted(figure_directory.glob(f"{stem}_*.svg"))
        if len(matches) != 1:
            errors.append(f"expected one figure for {stem}; found {len(matches)}")
            continue
        try:
            ElementTree.parse(matches[0])
        except ElementTree.ParseError as error:
            errors.append(f"invalid SVG {matches[0].name}: {error}")
    sources = (
        "docs/ARCHITECTURE.md",
        "docs/MODEL_SPEC.md",
        "data/processed/phase96_empirical_soil_locations_v1.csv",
        "outputs/phase96_v0.9.6/figures/empirical_generated_distributions.svg",
        "outputs/phase96_v0.9.6/figures/hoosfield_trajectories.svg",
        "outputs/phase96_v0.9.6/validation_trajectories.csv",
        "outputs/phase97_v0.9.7/calibration_profile.json",
        "outputs/phase97_v0.9.7/sensitivity_convergence_manifest.json",
        "outputs/phase97_v0.9.7/sensitivity_first_total.csv",
        "outputs/phase97_v0.9.7/gate_evidence.json",
        "manuscript/AUDIT_TRAIL.md",
    )
    for source in sources:
        if not (root / source).is_file():
            errors.append(f"figure source missing: {source}")
    index = figure_directory / "FIGURE_INDEX.md"
    if not index.is_file():
        errors.append("figure index missing")
    else:
        index_text = index.read_text(encoding="utf-8")
        for stem in REQUIRED_FIGURES:
            if stem not in index_text:
                errors.append(f"figure index omits {stem}")
    return errors


def validate_internal_links(root: Path) -> list[str]:
    """Validate relative Markdown link targets within the Phase 9.8 archive."""
    errors: list[str] = []
    markdown_paths = [root / "README.md", root / "docs/provenance/RESEARCH_ARCHIVE.md"]
    markdown_paths.extend((root / "docs/audits").glob("*.md"))
    markdown_paths.extend((root / "manuscript").rglob("*.md"))
    for path in sorted(markdown_paths):
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().strip("<>").split("#", maxsplit=1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (path.parent / target).resolve().exists():
                errors.append(f"broken internal link in {path.relative_to(root)}: {target}")
    return errors


def validate_audits(root: Path) -> list[str]:
    """Replay audit hashes, export attestations and every byte-preserved copy."""
    errors = _validate_manifest(root, root / "docs/audits/audit_manifest.json")
    archive_manifest = _load_object(root / "docs/audits/audit_manifest.json")
    if archive_manifest.get("missing_required_independent_deliverables") != []:
        errors.append("audit archive still reports missing independent deliverables")
    archived = root / "docs/audits/AUDIT_v0.9.0_INDEPENDENT.md"
    original = root / "docs/AUDIT_soil_simulator_v0.9.0.md"
    if archived.read_bytes() != original.read_bytes():
        errors.append("v0.9.0 audit archive copy differs from source")
    incoming_manifest_path = root / "audits/incoming/AUDIT_EXPORT_MANIFEST.json"
    archived_manifest_path = root / "docs/audits/AUDIT_EXPORT_MANIFEST.json"
    if archived_manifest_path.read_bytes() != incoming_manifest_path.read_bytes():
        errors.append("archived audit export manifest differs from source")
    export_manifest = _load_object(incoming_manifest_path)
    raw_entries = export_manifest.get("files")
    if not isinstance(raw_entries, list):
        return [*errors, "audit export manifest has no files list"]
    entries = {entry.get("filename"): entry for entry in raw_entries if isinstance(entry, dict)}
    if export_manifest.get("total_file_count") != 10 or set(entries) != set(AUDIT_SOURCE_MAP):
        errors.append("audit export manifest does not declare the exact ten-file set")
        return errors
    actual_incoming = {
        path.name
        for path in (root / "audits/incoming").iterdir()
        if path.is_file() and path.name != "AUDIT_EXPORT_MANIFEST.json"
    }
    if actual_incoming != set(AUDIT_SOURCE_MAP):
        errors.append("incoming audit directory has missing or unexpected deliverables")
    for source_name, canonical_name in AUDIT_SOURCE_MAP.items():
        source = root / "audits/incoming" / source_name
        canonical = root / "docs/audits" / canonical_name
        entry = entries[source_name]
        if source.read_bytes() != canonical.read_bytes():
            errors.append(f"canonical audit copy differs from source: {canonical_name}")
        if entry.get("sha256") != _sha256(source):
            errors.append(f"audit export hash mismatch: {source_name}")
        if entry.get("byte_size") != source.stat().st_size:
            errors.append(f"audit export size mismatch: {source_name}")
        if entry.get("retrieved_unchanged") is not True:
            errors.append(f"audit export lacks unchanged attestation: {source_name}")
    return errors


def validate_bundle(root: Path) -> list[str]:
    """Replay category/complete manifests and the complete set digest."""
    errors: list[str] = []
    manifest_directory = root / "manuscript/manifests"
    correction = _load_object(manifest_directory / "phase98_current_byte_corrections.json")
    changes = correction.get("changes_since_phase97_freeze")
    if not isinstance(changes, list):
        errors.append("Phase 9.8 correction record has no changes list")
    else:
        changed_paths = {item.get("path") for item in changes if isinstance(item, dict)}
        if changed_paths != {"README.md"}:
            errors.append(f"unexpected Phase 9.7 current-byte changes: {changed_paths}")
        for raw_change in changes:
            if not isinstance(raw_change, dict):
                continue
            change = cast(dict[str, Any], raw_change)
            relative_path = change.get("path")
            if not isinstance(relative_path, str):
                continue
            if change.get("current_sha256") != _sha256(root / relative_path):
                errors.append(f"Phase 9.8 correction hash mismatch: {relative_path}")
    for manifest_path in sorted(manifest_directory.glob("*_manifest.json")):
        errors.extend(_validate_manifest(root, manifest_path))
    complete = _load_object(manifest_directory / "manuscript_bundle_manifest.json")
    entries = complete.get("entries")
    if not isinstance(entries, list):
        return [*errors, "complete manuscript manifest has no entries list"]
    canonical_parts = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            errors.append("complete manifest has a non-object entry")
            continue
        entry = cast(dict[str, Any], raw_entry)
        canonical_parts.append(f"{entry['path']}\0{entry['sha256']}\n")
    digest = hashlib.sha256("".join(canonical_parts).encode()).hexdigest()
    if complete.get("set_sha256") != digest:
        errors.append("complete manuscript set digest mismatch")
    digest_file = (
        (manifest_directory / "MANUSCRIPT_BUNDLE_SHA256.txt").read_text(encoding="utf-8").strip()
    )
    if digest_file != digest:
        errors.append("manuscript digest file mismatch")
    return errors


def validate_archive(root: Path) -> list[str]:
    """Return every Phase 9.8 archive validation error; an empty list passes."""
    return [
        *validate_tables(root),
        *validate_figures(root),
        *validate_internal_links(root),
        *validate_audits(root),
        *validate_bundle(root),
    ]
