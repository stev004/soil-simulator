"""Empirical-grounding status and group-isolation checks for Phase 9.5."""

from __future__ import annotations

from collections import defaultdict

from soil_simulator.domain.population import SyntheticPopulation


def location_group_leakage(population: SyntheticPopulation) -> dict[str, object]:
    """Report any seed/location group assigned to multiple data partitions."""
    groups: dict[str, set[str]] = defaultdict(set)
    for field in population.fields:
        groups[field.empirical_seed_id].add(field.population_split.value)
    overlaps = {
        group_id: tuple(sorted(splits))
        for group_id, splits in sorted(groups.items())
        if len(splits) > 1
    }
    return {
        "group_key": "empirical_seed_id",
        "group_count": len(groups),
        "overlaps": overlaps,
        "passed": not overlaps,
        "interpretation": (
            "The archived synthetic groups are isolated. This does not convert them into "
            "empirical locations or resolve the Phase 9.5 grounding blocker."
        ),
    }
