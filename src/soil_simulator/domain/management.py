"""Immutable Phase 6 scheduled-management contracts.

Carbon uses ``t C ha-1``, available phosphorus uses ``kg P ha-1``, cost uses
``GBP ha-1`` and the non-mechanistic emissions proxy uses ``kg CO2e ha-1``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from soil_simulator.domain.amf import AmfStepResult
from soil_simulator.domain.enums import ManagementEventType, ParameterSource
from soil_simulator.domain.models import (
    ContractModel,
    FieldState,
    FluxRecord,
    ManagementEvent,
    NonNegativeFloat,
    NonNegativeInt,
)
from soil_simulator.domain.plant import PhosphorusFluxRecord, PlantMonth

EVENT_ORDER: dict[ManagementEventType, int] = {
    ManagementEventType.PHOSPHORUS_APPLICATION: 10,
    ManagementEventType.TILLAGE: 20,
    ManagementEventType.COVER_CROP_TERMINATION: 30,
    ManagementEventType.FARMYARD_MANURE: 40,
    ManagementEventType.COVER_CROP_ESTABLISHMENT: 50,
}


def event_simulation_month(event: ManagementEvent, start_date: date) -> int:
    """Resolve an event date or explicit zero-based index to a simulation month."""
    if event.simulation_month is not None:
        return event.simulation_month
    if event.event_date is None:  # guarded by ManagementEvent, retained for typing
        raise ValueError("management event has no schedule")
    months = (event.event_date.year - start_date.year) * 12
    months += event.event_date.month - start_date.month
    if months < 0:
        raise ValueError(f"event {event.event_id!r} precedes scenario start_date")
    return months


def ordered_events(
    events: tuple[ManagementEvent, ...], start_date: date
) -> tuple[ManagementEvent, ...]:
    """Return the documented deterministic month/type/id ordering."""
    return tuple(
        sorted(
            events,
            key=lambda event: (
                event_simulation_month(event, start_date),
                EVENT_ORDER[event.event_type],
                event.event_id,
            ),
        )
    )


class ManagementPolicy(ContractModel):
    """One named deterministic intervention schedule."""

    policy_id: Annotated[str, Field(min_length=1)]
    name: Annotated[str, Field(min_length=1)]
    events: tuple[ManagementEvent, ...] = ()
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_identifiers(self) -> Self:
        """Reject repeated IDs; schedule-dependent conflicts are checked by the set."""
        ids = [event.event_id for event in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("management event_id values must be unique within a policy")
        return self


class ManagementScenarioSet(ContractModel):
    """Shared deterministic forcing and multiple predefined management policies."""

    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]
    seed: NonNegativeInt
    start_date: date
    initial_state: FieldState
    monthly_steps: Annotated[tuple[PlantMonth, ...], Field(min_length=1)]
    policies: Annotated[tuple[ManagementPolicy, ...], Field(min_length=1)]
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        """Reject out-of-range, duplicate, conflicting, or unpaired events."""
        policy_ids = [policy.policy_id for policy in self.policies]
        if len(policy_ids) != len(set(policy_ids)):
            raise ValueError("management policy_id values must be unique")
        expected_month = self.start_date.month
        for index, month in enumerate(self.monthly_steps):
            calendar_month = ((expected_month - 1 + index) % 12) + 1
            if month.calendar_month != calendar_month:
                raise ValueError("monthly_steps must follow start_date in calendar-month order")
        for policy in self.policies:
            resolved = [event_simulation_month(event, self.start_date) for event in policy.events]
            if any(month >= len(self.monthly_steps) for month in resolved):
                raise ValueError(
                    f"policy {policy.policy_id!r} contains an event outside the horizon"
                )
            signatures: set[tuple[object, ...]] = set()
            tillage_months: set[int] = set()
            cover_active = False
            for event in ordered_events(policy.events, self.start_date):
                scheduled_month = event_simulation_month(event, self.start_date)
                signature = (
                    scheduled_month,
                    event.event_type,
                    event.amount,
                    event.units,
                    tuple((p.name, p.value, p.unit) for p in event.parameters),
                )
                if signature in signatures:
                    raise ValueError(f"policy {policy.policy_id!r} contains duplicate events")
                signatures.add(signature)
                if event.event_type is ManagementEventType.TILLAGE:
                    if scheduled_month in tillage_months:
                        raise ValueError("only one tillage event is allowed in a simulation month")
                    tillage_months.add(scheduled_month)
                elif event.event_type is ManagementEventType.COVER_CROP_ESTABLISHMENT:
                    if cover_active:
                        raise ValueError("cover crop cannot be established while already active")
                    cover_active = True
                elif event.event_type is ManagementEventType.COVER_CROP_TERMINATION:
                    if not cover_active:
                        raise ValueError("cover crop cannot terminate before establishment")
                    cover_active = False
            if cover_active:
                raise ValueError("every cover-crop establishment requires a scheduled termination")
        return self

    def stable_hash(self) -> str:
        """Hash validated scenario and event values deterministically."""
        canonical = json.dumps(
            self.model_dump(mode="json"),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ManagementRuntimeState(ContractModel):
    """Explicit carried management state outside the verified Phase 5 state."""

    cover_crop_active: bool = False
    cover_shoot_c_t_ha: NonNegativeFloat = 0.0
    cover_root_c_t_ha: NonNegativeFloat = 0.0
    cover_plant_p_kg_ha: NonNegativeFloat = 0.0
    tillage_effect_months_remaining: NonNegativeInt = 0
    soil_cover_suppression_months_remaining: NonNegativeInt = 0
    decomposition_multiplier: Annotated[float, Field(ge=1.0, allow_inf_nan=False)] = 1.0
    amf_turnover_multiplier: Annotated[float, Field(ge=1.0, allow_inf_nan=False)] = 1.0


class AppliedManagementEvent(ContractModel):
    """One event in its deterministic execution order."""

    event: ManagementEvent
    simulation_month: NonNegativeInt
    order_in_month: NonNegativeInt


class ManagementCarbonBalance(ContractModel):
    """Whole managed carbon-system conservation diagnostic [t C ha-1]."""

    month_index: NonNegativeInt
    initial_carbon_t_c_ha: NonNegativeFloat
    crop_assimilation_t_c_ha: NonNegativeFloat
    cover_crop_assimilation_t_c_ha: NonNegativeFloat
    manure_input_t_c_ha: NonNegativeFloat
    respiration_t_c_ha: NonNegativeFloat
    harvest_and_biomass_exports_t_c_ha: NonNegativeFloat
    final_carbon_t_c_ha: NonNegativeFloat
    residual_t_c_ha: float = Field(allow_inf_nan=False)
    tolerance_t_c_ha: NonNegativeFloat
    within_tolerance: bool


class ManagementPhosphorusBalance(ContractModel):
    """Available plus cover-plant P conservation diagnostic [kg P ha-1]."""

    month_index: NonNegativeInt
    initial_phosphorus_kg_p_ha: NonNegativeFloat
    phosphorus_application_kg_p_ha: NonNegativeFloat
    manure_phosphorus_input_kg_p_ha: NonNegativeFloat
    crop_and_amf_withdrawal_kg_p_ha: NonNegativeFloat
    cover_amf_retention_kg_p_ha: NonNegativeFloat
    cover_phosphorus_export_kg_p_ha: NonNegativeFloat
    final_phosphorus_kg_p_ha: NonNegativeFloat
    residual_kg_p_ha: float = Field(allow_inf_nan=False)
    tolerance_kg_p_ha: NonNegativeFloat
    within_tolerance: bool


class ManagementStepResult(ContractModel):
    """One immutable managed month composed around the Phase 5 result."""

    initial_state: FieldState
    final_state: FieldState
    initial_management_state: ManagementRuntimeState
    final_management_state: ManagementRuntimeState
    applied_events: tuple[AppliedManagementEvent, ...]
    amf_step: AmfStepResult
    tillage_amf_mortality_t_c_ha: NonNegativeFloat
    tillage_incorporated_carbon_t_c_ha: NonNegativeFloat
    cover_crop_gross_carbon_t_c_ha: NonNegativeFloat
    cover_crop_net_carbon_t_c_ha: NonNegativeFloat
    cover_crop_phosphorus_uptake_kg_p_ha: NonNegativeFloat
    cover_crop_residue_return_t_c_ha: NonNegativeFloat
    cover_crop_phosphorus_return_kg_p_ha: NonNegativeFloat
    manure_carbon_input_t_c_ha: NonNegativeFloat
    manure_phosphorus_input_kg_p_ha: NonNegativeFloat
    phosphorus_application_kg_p_ha: NonNegativeFloat
    cost_gbp_ha: NonNegativeFloat
    emissions_proxy_kg_co2e_ha: NonNegativeFloat
    carbon_fluxes: tuple[FluxRecord, ...]
    phosphorus_fluxes: tuple[PhosphorusFluxRecord, ...]
    carbon_balance: ManagementCarbonBalance
    phosphorus_balance: ManagementPhosphorusBalance
    uncertainty_status: Literal["provisional_phase_6_not_quantified"] = (
        "provisional_phase_6_not_quantified"
    )


class ManagementSimulationResult(ContractModel):
    """Immutable deterministic result for one Phase 6 policy."""

    policy_id: Annotated[str, Field(min_length=1)]
    policy_name: Annotated[str, Field(min_length=1)]
    seed: NonNegativeInt
    configuration_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    schedule_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    initial_state: FieldState
    final_state: FieldState
    final_management_state: ManagementRuntimeState
    steps: tuple[ManagementStepResult, ...]
    applied_events: tuple[AppliedManagementEvent, ...]
    cumulative_grain_yield_t_dm_ha: NonNegativeFloat
    cumulative_cover_crop_carbon_input_t_c_ha: NonNegativeFloat
    cumulative_respiration_t_c_ha: NonNegativeFloat
    cumulative_cost_gbp_ha: NonNegativeFloat
    cumulative_emissions_proxy_kg_co2e_ha: NonNegativeFloat
    cumulative_carbon_residual_t_c_ha: float = Field(allow_inf_nan=False)
    cumulative_phosphorus_residual_kg_p_ha: float = Field(allow_inf_nan=False)
    amf_outcomes: tuple[Literal["beneficial", "neutral", "harmful"], ...]
    carbon_unit: Literal["t_C_ha"] = "t_C_ha"
    phosphorus_unit: Literal["kg_P_ha"] = "kg_P_ha"
    cost_unit: Literal["GBP_ha"] = "GBP_ha"
    emissions_proxy_unit: Literal["kg_CO2e_ha"] = "kg_CO2e_ha"
    uncertainty_status: Literal["provisional_phase_6_not_quantified"] = (
        "provisional_phase_6_not_quantified"
    )
    provenance: Annotated[str, Field(min_length=1)]


class ManagementComparisonResult(ContractModel):
    """Results for every predefined policy without an optimiser or ranking."""

    scenario_name: Annotated[str, Field(min_length=1)]
    scenario_version: Annotated[str, Field(min_length=1)]
    results: Annotated[tuple[ManagementSimulationResult, ...], Field(min_length=1)]
    scientific_claim_boundary: Literal[
        "scenario directions are model implications, not field validation or causal recommendations"
    ] = "scenario directions are model implications, not field validation or causal recommendations"
