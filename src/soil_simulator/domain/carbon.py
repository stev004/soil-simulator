"""Typed contracts for deterministic RothC-style carbon-core inputs and outputs.

All carbon stocks and flows use ``t C ha-1``. ``protected_soc_c`` remains a
humified/protected model proxy and is not measured MAOC. Phase 3 quantifies no
parameter or process uncertainty, so results state that boundary explicitly.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from soil_simulator.domain.enums import ExternalInputTiming, ParameterSource
from soil_simulator.domain.models import (
    ContractModel,
    FieldState,
    FluxRecord,
    Fraction,
    NonNegativeFloat,
    NonNegativeInt,
)


class CarbonInput(ContractModel):
    """External carbon entering supported soil pools during one month.

    DPM and RPM represent plant/residue inputs. Direct protected-pool input is
    retained for the specified manure route. External additions to microbial
    biomass or IOM are outside the Phase 3 model boundary.
    """

    dpm_c: Annotated[NonNegativeFloat, Field(description="External DPM carbon [t C ha-1]")] = 0.0
    rpm_c: Annotated[NonNegativeFloat, Field(description="External RPM carbon [t C ha-1]")] = 0.0
    protected_soc_c: Annotated[
        NonNegativeFloat,
        Field(description="External carbon routed directly to protected SOC proxy [t C ha-1]"),
    ] = 0.0
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1, description="Input source provenance")]

    @property
    def total_t_c_ha(self) -> float:
        """Return total external carbon [t C ha-1]."""
        return self.dpm_c + self.rpm_c + self.protected_soc_c


class RothCForcing(ContractModel):
    """Monthly forcing for the official RothC environmental calculations.

    Water inputs use ``mm month-1``. Evaporation is open-pan evaporation; a
    PET estimate must first be converted to its open-pan equivalent because
    RothC applies its configured 0.75 factor internally. Soil cover records
    physical crop/vegetation cover, not AMF host status.
    """

    mean_air_temperature_c: Annotated[
        float, Field(allow_inf_nan=False, description="Mean monthly air temperature [deg C]")
    ]
    precipitation_mm: Annotated[
        NonNegativeFloat, Field(description="Monthly precipitation [mm month-1]")
    ]
    open_pan_evaporation_mm: Annotated[
        NonNegativeFloat, Field(description="Monthly open-pan evaporation [mm month-1]")
    ]
    is_covered: Annotated[bool, Field(description="Whether growing vegetation covers the soil")]
    clay_percent: Annotated[
        float, Field(ge=0.0, le=100.0, allow_inf_nan=False, description="Clay content [% mass]")
    ]
    soil_depth_cm: Annotated[
        float, Field(gt=0.0, allow_inf_nan=False, description="Modelled topsoil depth [cm]")
    ]
    provenance: Annotated[str, Field(min_length=1)]


class CarbonCoreMonth(ContractModel):
    """One deterministic month of external carbon and environmental forcing."""

    external_input: CarbonInput
    forcing: RothCForcing


class RothCModifierDiagnostic(ContractModel):
    """Traceable environmental modifiers and moisture state for one month."""

    temperature: NonNegativeFloat
    moisture: NonNegativeFloat
    cover: NonNegativeFloat
    combined: NonNegativeFloat
    previous_accumulated_tsmd_mm: Annotated[float, Field(le=0.0, allow_inf_nan=False)]
    accumulated_tsmd_mm: Annotated[float, Field(le=0.0, allow_inf_nan=False)]
    maximum_tsmd_mm: Annotated[float, Field(le=0.0, allow_inf_nan=False)]
    bare_soil_maximum_tsmd_mm: Annotated[float, Field(le=0.0, allow_inf_nan=False)]
    co2_to_retained_ratio: NonNegativeFloat
    co2_fraction: Fraction
    retained_fraction: Fraction


class MassBalanceDiagnostic(ContractModel):
    """One carbon-conservation check, with all quantities in ``t C ha-1``."""

    month_index: NonNegativeInt
    initial_carbon_t_c_ha: NonNegativeFloat
    external_inputs_t_c_ha: NonNegativeFloat
    respiration_losses_t_c_ha: NonNegativeFloat
    final_carbon_t_c_ha: NonNegativeFloat
    residual_t_c_ha: float = Field(allow_inf_nan=False)
    relative_residual: NonNegativeFloat
    tolerance_t_c_ha: NonNegativeFloat
    within_tolerance: bool
    equation: Literal[
        "initial carbon + external carbon inputs - respiration losses = final carbon"
    ] = "initial carbon + external carbon inputs - respiration losses = final carbon"


class CarbonCoreStepResult(ContractModel):
    """Immutable result of one deterministic monthly soil-carbon step."""

    initial_state: FieldState
    final_state: FieldState
    fluxes: tuple[FluxRecord, ...]
    modifiers: RothCModifierDiagnostic
    respiration_t_c_ha: NonNegativeFloat
    transfer_to_microbial_t_c_ha: NonNegativeFloat
    transfer_to_protected_t_c_ha: NonNegativeFloat
    mass_balance: MassBalanceDiagnostic
    external_input_timing: ExternalInputTiming
    carbon_unit: Literal["t_C_ha"] = "t_C_ha"
    uncertainty_status: Literal["not_quantified_in_phase_3"] = "not_quantified_in_phase_3"
    provenance: Annotated[str, Field(min_length=1)]


class CarbonCoreSimulationResult(ContractModel):
    """Immutable multi-month deterministic carbon-core trajectory."""

    seed: NonNegativeInt
    initial_state: FieldState
    final_state: FieldState
    steps: tuple[CarbonCoreStepResult, ...]
    fluxes: tuple[FluxRecord, ...]
    cumulative_respiration_t_c_ha: NonNegativeFloat
    cumulative_transfer_to_microbial_t_c_ha: NonNegativeFloat
    cumulative_transfer_to_protected_t_c_ha: NonNegativeFloat
    cumulative_mass_balance: MassBalanceDiagnostic
    external_input_timing: ExternalInputTiming
    carbon_unit: Literal["t_C_ha"] = "t_C_ha"
    uncertainty_status: Literal["not_quantified_in_phase_3"] = "not_quantified_in_phase_3"
    provenance: Annotated[str, Field(min_length=1)]


class CarbonCoreScenario(ContractModel):
    """A predefined, versioned input scenario for the Phase 3 CLI."""

    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]
    seed: NonNegativeInt
    initial_state: FieldState
    monthly_steps: Annotated[tuple[CarbonCoreMonth, ...], Field(min_length=1)]
    classification: Literal[ParameterSource.SCENARIO_ASSUMPTION]
    provenance: Annotated[str, Field(min_length=1)]
