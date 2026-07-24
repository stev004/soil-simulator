from pathlib import Path

from soil_simulator.phase98 import validate_archive
from soil_simulator.phase98.archive import (
    validate_audits,
    validate_bundle,
    validate_figures,
    validate_internal_links,
    validate_tables,
)

ROOT = Path(__file__).resolve().parents[2]


def test_manuscript_tables_are_traceable() -> None:
    assert validate_tables(ROOT) == []


def test_figures_are_valid_and_source_backed() -> None:
    assert validate_figures(ROOT) == []


def test_archive_internal_links_resolve() -> None:
    assert validate_internal_links(ROOT) == []


def test_audit_archive_replays() -> None:
    assert validate_audits(ROOT) == []


def test_prism_handoff_is_ready_only_for_bounded_drafting() -> None:
    handoff = (ROOT / "manuscript/PRISM_HANDOFF.md").read_text(encoding="utf-8")
    assert "READY FOR BOUNDED PRISM DRAFTING" in handoff
    assert "NOT READY FOR PRISM" not in handoff
    assert "validated agricultural-prediction paper: not supported" in handoff.lower()


def test_manuscript_bundle_replays() -> None:
    assert validate_bundle(ROOT) == []


def test_complete_archive_validation_passes() -> None:
    assert validate_archive(ROOT) == []
