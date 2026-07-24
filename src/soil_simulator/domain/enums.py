"""Enumerations shared by the scientific domain contracts."""

from enum import StrEnum


class ParameterSource(StrEnum):
    """Required provenance classification for every scientific model parameter."""

    ESTABLISHED_MODEL = "established_model"
    LITERATURE_INFORMED_PRIOR = "literature_informed_prior"
    SCENARIO_ASSUMPTION = "scenario_assumption"
    CALIBRATED = "calibrated"


class ManagementEventType(StrEnum):
    """Scheduled management operations implemented by the Phase 6 boundary."""

    TILLAGE = "tillage"
    COVER_CROP_ESTABLISHMENT = "cover_crop_establishment"
    COVER_CROP_TERMINATION = "cover_crop_termination"
    PHOSPHORUS_APPLICATION = "phosphorus_application"
    FARMYARD_MANURE = "farmyard_manure"


class TillageLevel(StrEnum):
    """Configured tillage intensity levels."""

    CONVENTIONAL = "conventional"
    REDUCED = "reduced"
    NO_TILL = "no_till"


class PopulationSplit(StrEnum):
    """Leakage-resistant population partitions assigned at seed-group level."""

    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    ARCHETYPE_OOD = "archetype_ood"
    WEATHER_OOD = "weather_ood"


class CarbonPool(StrEnum):
    """Soil-carbon pools implemented by the deterministic Phase 3 core."""

    DPM = "dpm_c"
    RPM = "rpm_c"
    MICROBIAL = "microbial_c"
    PROTECTED_SOC = "protected_soc_c"
    IOM = "iom_c"


class AmfCarbonPool(StrEnum):
    """AMF and transient plant-carbon pools used by Phase 5 flux records."""

    REALISED_PLANT = "realised_plant_c"
    LIVE = "amf_live_c"
    NECROMASS = "amf_necromass_c"
    SUBSTRATE = "amf_substrate_c"


class CarbonBoundary(StrEnum):
    """Named system boundaries used in carbon-flow records."""

    EXTERNAL_INPUTS = "external_inputs"
    ATMOSPHERE = "atmosphere"
    HARVEST_EXPORT = "harvest_export"
    RESIDUE_EXPORT = "residue_export"


class ExternalInputTiming(StrEnum):
    """Supported timing for external soil-carbon additions."""

    POST_DECOMPOSITION = "post_decomposition"
    LEGACY_PRE_DECOMPOSITION = "legacy_pre_decomposition"


class PhosphorusPool(StrEnum):
    """Pools and boundaries used by available-phosphorus accounting."""

    AVAILABLE = "available_p"
    EXTERNAL_INPUTS = "external_p_inputs"
    PLANT = "plant_p"
    AMF = "amf_p"
    AMF_RETAINED = "amf_retained_p"
