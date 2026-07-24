"""Predeclared Phase 9.5 manuscript-readiness gates."""

from __future__ import annotations

from collections.abc import Mapping

GATE_LABELS: tuple[str, ...] = (
    "stock_target_circularity_removed_from_headlines",
    "deterministic_accounting_removed_from_ml",
    "duplicate_no_till_resolved",
    "phosphorus_dominance_bounded_calibrated_or_excluded",
    "global_sensitivity_complete",
    "multi_decade_soc_validation_reported",
    "population_empirically_grounded_or_explicitly_synthetic",
    "results_and_limitations_reproducible",
    "negative_findings_visible",
)


def publication_readiness(gates: Mapping[str, bool]) -> dict[str, object]:
    """Evaluate only the predeclared gates; absent gates fail closed."""
    evaluated = {label: bool(gates.get(label, False)) for label in GATE_LABELS}
    blockers = tuple(label for label, passed in evaluated.items() if not passed)
    return {
        "version": "0.9.5",
        "gates": evaluated,
        "passed": not blockers,
        "remaining_blockers": blockers,
        "exact_next_task": (
            "independent re-audit" if not blockers else "remaining scientific remediation"
        ),
        "manuscript_drafting_recommendation": False,
        "claim_boundary": (
            "Prism manuscript drafting is not recommended until an independent re-audit "
            "confirms that every publication-readiness gate is satisfied."
        ),
    }
