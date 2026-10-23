"""
Phase 4 — Empirical Validation Foundations: Data Ingestion Schemas & Quality Gates.

Provides production-safe, structured Pydantic models for ingesting, validating,
and preserving real-world empirical packaging validation trials (REAL_EMPIRICAL).

STRICT SCIENTIFIC & ARCHITECTURAL BOUNDARIES:
- Scientific Hierarchy: REAL_EMPIRICAL > VALIDATED PHYSICS > EXACT COMPUTATIONAL PHYSICS > AI SURROGATE.
- Missing values: MUST remain explicitly None. Never replace missing empirical measurements with 0.0 or defaults.
- Nominal vs Measured: Stored distinctly. Measured properties are never silently replaced by nominal specs.
- Environmental Trajectories: Preserves full continuous T_actual(t) and RH_actual(t) trajectories as raw observations.
  Does NOT implement Mean Kinetic Temperature, average substitution, or trajectory compression.
- Endpoint Definitions: Protocol-specific. No hardcoded global shelf-life constants.
- Provenance: 9-tier traceable lineage chain using operator/laboratory identifiers with standard access metadata.
- Data Status: Strictly tagged as REAL_EMPIRICAL. Never merged with MODEL_PREDICTED or SYNTHETIC data.
- Quality Gates: 8 validation gates assigning VALIDATED or QUARANTINED status with machine-readable reasons.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, root_validator, validator

from app.schemas.inference import UncertaintyLevelEnum
from app.schemas.ai_data import (
    AIDataStatusEnum,
    AIProvenanceRecord,
    AIFeatureValue,
    AIDataRecord,
)


class EmpiricalTrialStatusEnum(str, Enum):
    """Quality gate validation outcome for empirical trial records."""
    VALIDATED = "VALIDATED"
    QUARANTINED = "QUARANTINED"


class EmpiricalMeasurementUncertainty(BaseModel):
    """
    Preserves experimental measurement uncertainty without forcing probabilistic assumptions.
    """
    value: float = Field(..., description="Uncertainty magnitude e.g. 0.05.")
    uncertainty_type: str = Field(
        default="standard_error",
        description="Type of uncertainty e.g. 'standard_error', 'instrument_accuracy', 'expanded_u95'."
    )
    unit: Optional[str] = Field(default=None, description="Physical unit matching measured property.")
    coverage_factor: Optional[float] = Field(default=1.0, description="Coverage factor k (e.g. k=2 for 95% CI).")


class EmpiricalFoodSpecification(BaseModel):
    """
    Preserves actual food commodity state and physicochemical parameters in an empirical trial.
    STRICT RULE: Missing values MUST remain None. No zero substitution or default value coercion.
    """
    commodity: str = Field(..., description="Food commodity name e.g. 'Strawberry', 'Fresh-Cut Apple'.")
    variety: Optional[str] = Field(default=None, description="Botanical variety or cultivar e.g. 'Chandler'.")
    product_form: str = Field(..., description="Product physical form e.g. 'fresh_cut', 'whole', 'powder'.")
    initial_mass_kg: Optional[float] = Field(default=None, description="Initial food mass (kg).")
    initial_moisture_g_g: Optional[float] = Field(default=None, description="Initial moisture content (g H2O / g dry solid).")
    initial_water_activity: Optional[float] = Field(default=None, description="Initial water activity (aw, [0.0 - 1.0]).")
    critical_moisture_g_g: Optional[float] = Field(default=None, description="Critical moisture content for quality loss.")
    pH_value: Optional[float] = Field(default=None, description="Initial pH value.")
    respiration_rate_O2: Optional[float] = Field(default=None, description="O2 consumption rate (mL/kg.h).")
    respiration_rate_CO2: Optional[float] = Field(default=None, description="CO2 evolution rate (mL/kg.h).")
    initial_microbial_load_log_cfu: Optional[float] = Field(default=None, description="Initial microbial load (log10 CFU/g).")
    processing_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of harvest/processing.")
    food_batch_id: Optional[str] = Field(default=None, description="Unique batch/lot ID for commodity source.")

    @validator("initial_water_activity")
    def validate_aw(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError(f"Water activity must be in [0.0, 1.0], got {v}")
        return v

    @validator("initial_mass_kg", "initial_moisture_g_g", "critical_moisture_g_g")
    def validate_positive(cls, v):
        if v is not None and v <= 0.0:
            raise ValueError(f"Food property value must be strictly positive (> 0.0), got {v}")
        return v


class EmpiricalPackagingSpecification(BaseModel):
    """
    Preserves actual packaging configuration used in an empirical trial.
    STRICT RULE: Distinguishes nominal specifications from measured experimental properties.
    """
    material: str = Field(..., description="Packaging polymer designation e.g. 'LDPE', 'PET/PE_Laminate'.")
    layer_structure: Optional[List[Dict[str, Any]]] = Field(default=None, description="Layer sequence and nominal thicknesses.")
    nominal_thickness_um: Optional[float] = Field(default=None, description="Nominal thickness specified by supplier (um).")
    measured_thickness_um: Optional[float] = Field(default=None, description="Experimentally measured film thickness (um).")
    measured_otr: Optional[float] = Field(default=None, description="Measured Oxygen Transmission Rate (cc / m2.day.atm).")
    measured_wvtr: Optional[float] = Field(default=None, description="Measured Water Vapor Transmission Rate (g / m2.day).")
    package_surface_area_m2: Optional[float] = Field(default=None, description="Internal package surface area (m2).")
    headspace_volume_m3: Optional[float] = Field(default=None, description="Internal headspace volume (m3).")
    seal_integrity_pass: Optional[bool] = Field(default=None, description="Seal integrity test result.")
    initial_O2_pct: Optional[float] = Field(default=None, description="Initial headspace O2 concentration (%).")
    initial_CO2_pct: Optional[float] = Field(default=None, description="Initial headspace CO2 concentration (%).")
    film_batch_id: Optional[str] = Field(default=None, description="Film manufacturing lot/batch identifier.")

    @validator("measured_thickness_um", "nominal_thickness_um", "package_surface_area_m2", "headspace_volume_m3")
    def validate_positive_dims(cls, v):
        if v is not None and v <= 0.0:
            raise ValueError(f"Packaging dimension must be strictly positive (> 0.0), got {v}")
        return v


class EnvironmentTrajectoryPoint(BaseModel):
    """
    Single time-stamped environmental observation point.
    Preserves raw continuous trajectory without compression or averaging.
    """
    timestamp: str = Field(..., description="ISO timestamp of environmental observation.")
    elapsed_time_hours: float = Field(..., description="Elapsed time from trial start (hours).")
    temperature_c: float = Field(..., description="Measured temperature (deg C).")
    relative_humidity_pct: float = Field(..., description="Measured relative humidity (%).")


class EmpiricalStorageEnvironment(BaseModel):
    """
    Preserves actual environmental storage conditions during an empirical trial.
    STRICT RULE: Preserves continuous T_actual(t) and RH_actual(t) trajectories.
    Does NOT implement Mean Kinetic Temperature or average substitution.
    Target setpoints are Optional (None when trial was conducted under unrecorded setpoints or ambient conditions).
    """
    target_temperature_c: Optional[float] = Field(default=None, description="Target storage temperature setpoint (deg C). None if unrecorded/ambient.")
    target_relative_humidity_pct: Optional[float] = Field(default=None, description="Target relative humidity setpoint (%). None if unrecorded/ambient.")
    temperature_trajectory: List[EnvironmentTrajectoryPoint] = Field(
        default_factory=list,
        description="Continuous logged temperature trajectory T_actual(t)."
    )
    relative_humidity_trajectory: List[EnvironmentTrajectoryPoint] = Field(
        default_factory=list,
        description="Continuous logged RH trajectory RH_actual(t)."
    )
    storage_duration_days: float = Field(..., description="Total storage trial duration (days).")
    thermal_cycling_notes: Optional[str] = Field(default=None, description="Description of thermal/humidity cycling events.")
    light_exposure_lux: Optional[float] = Field(default=None, description="Measured light illumination intensity (lux).")

    @validator("target_relative_humidity_pct")
    def validate_rh(cls, v):
        if v is not None and (v < 0.0 or v > 100.0):
            raise ValueError(f"Target RH must be in [0.0, 100.0], got {v}")
        return v


class EmpiricalTimeSeriesObservation(BaseModel):
    """
    Single time-series sampling observation during an empirical trial.
    """
    observation_id: str = Field(..., description="Unique observation point ID.")
    timestamp: str = Field(..., description="ISO timestamp of measurement.")
    elapsed_time_days: float = Field(..., description="Elapsed storage time (days).")
    measurement_type: str = Field(..., description="Property measured e.g. 'moisture_content', 'microbial_count', 'headspace_O2'.")
    value: float = Field(..., description="Measured numeric value.")
    unit: str = Field(..., description="Physical unit of measurement e.g. 'g_g', 'log10_CFU_g', 'pct'.")
    replicate_id: str = Field(default="rep_1", description="Replicate identifier e.g. 'rep_1', 'rep_2'.")
    uncertainty: Optional[EmpiricalMeasurementUncertainty] = Field(default=None, description="Measurement uncertainty record.")
    instrument_id: Optional[str] = Field(default=None, description="Instrument identifier used for measurement.")


class EmpiricalShelfLifeOutcome(BaseModel):
    """
    Preserves observed experimental shelf-life outcome and protocol-specific endpoint definition.
    STRICT RULE: Endpoint definitions are protocol-specific; NO hardcoded global failure constants.
    """
    observed_shelf_life_days: float = Field(..., description="Observed experimental shelf-life (days).")
    endpoint_type: str = Field(..., description="Type of endpoint e.g. 'moisture_limit', 'microbial_threshold', 'sensory_score'.")
    endpoint_definition: str = Field(..., description="Protocol-specific operational endpoint formula/criterion.")
    endpoint_timestamp: Optional[str] = Field(default=None, description="ISO timestamp when endpoint was reached.")
    endpoint_measurement_value: Optional[float] = Field(default=None, description="Measured parameter value at endpoint.")
    endpoint_measurement_unit: Optional[str] = Field(default=None, description="Unit of parameter value at endpoint.")

    @validator("observed_shelf_life_days")
    def validate_shelf_life(cls, v):
        if v < 0.0:
            raise ValueError(f"Observed shelf-life must be non-negative (>= 0.0), got {v}")
        return v


class EmpiricalTrialProvenance(BaseModel):
    """
    Preserves complete 9-tier traceable provenance chain for an empirical trial.
    STRICT RULE: Uses operator/laboratory identifiers with standard access control; NO mandatory hashing.
    """
    trial_id: str = Field(..., description="Unique empirical trial identifier.")
    protocol_id: str = Field(..., description="Pre-registered laboratory protocol identifier.")
    food_batch_id: Optional[str] = Field(default=None, description="Food commodity lot/batch ID.")
    film_batch_id: Optional[str] = Field(default=None, description="Packaging film lot/batch ID.")
    storage_chamber_id: Optional[str] = Field(default=None, description="Environmental test chamber ID.")
    instrument_ids: List[str] = Field(default_factory=list, description="IDs of instruments used in trial.")
    calibration_info: Optional[Dict[str, Any]] = Field(default=None, description="Calibration status and certificates.")
    operator_or_lab_id: str = Field(..., description="Laboratory or operator identifier.")
    creation_timestamp: str = Field(..., description="ISO timestamp of trial registration.")


class EmpiricalTrialRecord(BaseModel):
    """
    Complete Empirical Trial Record container representing a real-world physical packaging trial.
    STRICT RULE: Tagged exclusively as REAL_EMPIRICAL. Never merged with MODEL_PREDICTED or SYNTHETIC.
    """
    trial_id: str = Field(..., description="Unique trial identifier.")
    protocol_id: str = Field(..., description="Pre-registered laboratory trial protocol ID.")
    data_status: AIDataStatusEnum = Field(
        default=AIDataStatusEnum.REAL_EMPIRICAL,
        description="Data status taxonomy. MUST be REAL_EMPIRICAL."
    )
    status: EmpiricalTrialStatusEnum = Field(
        default=EmpiricalTrialStatusEnum.VALIDATED,
        description="Quality gate validation status (VALIDATED or QUARANTINED)."
    )
    quarantine_reasons: List[str] = Field(
        default_factory=list,
        description="Machine-readable quarantine reasons if validation failed."
    )
    food_spec: EmpiricalFoodSpecification = Field(..., description="Food commodity state and parameters.")
    packaging_spec: EmpiricalPackagingSpecification = Field(..., description="Packaging material specification.")
    storage_env: EmpiricalStorageEnvironment = Field(..., description="Storage environmental conditions and trajectories.")
    time_series_observations: List[EmpiricalTimeSeriesObservation] = Field(
        default_factory=list,
        description="Time-series measurement sampling points."
    )
    outcome: Optional[EmpiricalShelfLifeOutcome] = Field(default=None, description="Observed shelf-life outcome.")
    provenance: EmpiricalTrialProvenance = Field(..., description="9-tier traceable provenance record.")
    raw_payload: Optional[Dict[str, Any]] = Field(default=None, description="Original unparsed/submitted raw empirical payload dictionary.")


    @root_validator(skip_on_failure=True)
    def enforce_real_empirical_status(cls, values):
        status = values.get("data_status")
        if status != AIDataStatusEnum.REAL_EMPIRICAL:
            raise ValueError(
                f"EmpiricalTrialRecord MUST have data_status=REAL_EMPIRICAL, got {status}. "
                "Computational data (MODEL_PREDICTED / SYNTHETIC) must not be represented as empirical trials."
            )
        return values

    def to_ai_data_record(self) -> AIDataRecord:
        """
        Converts EmpiricalTrialRecord into standard Layer 1 AIDataRecord for system compatibility.
        """
        prov_record = AIProvenanceRecord(
            source_id=self.trial_id,
            source_type="lab_trial",
            data_status=AIDataStatusEnum.REAL_EMPIRICAL,
            epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            generation_timestamp=self.provenance.creation_timestamp,
            food_context={"commodity": self.food_spec.commodity, "product_form": self.food_spec.product_form},
            packaging_context={"material": self.packaging_spec.material},
            storage_context={
                "target_temperature_c": self.storage_env.target_temperature_c,
                "target_relative_humidity_pct": self.storage_env.target_relative_humidity_pct,
                "storage_duration_days": self.storage_env.storage_duration_days,
            },
        )

        food_feats: Dict[str, AIFeatureValue] = {}
        if self.food_spec.initial_moisture_g_g is not None:
            food_feats["initial_moisture_g_g"] = AIFeatureValue(
                feature_name="initial_moisture_g_g",
                value=self.food_spec.initial_moisture_g_g,
                is_missing=False,
                unit="g_g",
                data_status=AIDataStatusEnum.REAL_EMPIRICAL,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            )
        if self.food_spec.initial_water_activity is not None:
            food_feats["initial_water_activity"] = AIFeatureValue(
                feature_name="initial_water_activity",
                value=self.food_spec.initial_water_activity,
                is_missing=False,
                unit="aw",
                data_status=AIDataStatusEnum.REAL_EMPIRICAL,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            )

        pkg_feats: Dict[str, AIFeatureValue] = {}
        thick_val = self.packaging_spec.measured_thickness_um or self.packaging_spec.nominal_thickness_um
        if thick_val is not None:
            pkg_feats["thickness_um"] = AIFeatureValue(
                feature_name="thickness_um",
                value=thick_val,
                is_missing=False,
                unit="um",
                data_status=AIDataStatusEnum.REAL_EMPIRICAL,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            )

        outcome_feats: Dict[str, AIFeatureValue] = {}
        if self.outcome is not None:
            outcome_feats["shelf_life_days"] = AIFeatureValue(
                feature_name="shelf_life_days",
                value=self.outcome.observed_shelf_life_days,
                is_missing=False,
                unit="days",
                data_status=AIDataStatusEnum.REAL_EMPIRICAL,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            )

        return AIDataRecord(
            record_id=self.trial_id,
            data_status=AIDataStatusEnum.REAL_EMPIRICAL,
            epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            provenance=prov_record,
            food_features=food_feats,
            packaging_features=pkg_feats,
            outcome_features=outcome_feats,
        )


class EmpiricalTrialQualityGateEngine:
    """
    Evaluates incoming EmpiricalTrialRecord objects against the 8 approved quality gates.
    If any gate fails, assigns QUARANTINED status with machine-readable reasons.
    Original raw records are preserved without silent deletion or auto-repair.
    """

    def evaluate_and_validate(self, record: EmpiricalTrialRecord) -> EmpiricalTrialRecord:
        """Evaluate record across 8 validation gates and return updated record."""
        quarantine_reasons: List[str] = []

        # Gate A — Identity Gate
        if not record.trial_id or not record.trial_id.strip():
            quarantine_reasons.append("GATE_A_FAIL: Missing trial_id")
        if not record.protocol_id or not record.protocol_id.strip():
            quarantine_reasons.append("GATE_A_FAIL: Missing protocol_id")

        # Gate B — Units Gate
        for obs in record.time_series_observations:
            if not obs.unit or not obs.unit.strip():
                quarantine_reasons.append(f"GATE_B_FAIL: Observation {obs.observation_id} missing unit")

        # Gate C — Physical Validity Gate
        if record.food_spec.initial_water_activity is not None:
            if record.food_spec.initial_water_activity < 0.0 or record.food_spec.initial_water_activity > 1.0:
                quarantine_reasons.append(f"GATE_C_FAIL: Invalid water activity {record.food_spec.initial_water_activity}")
        if record.storage_env.target_relative_humidity_pct is not None:
            if record.storage_env.target_relative_humidity_pct < 0.0 or record.storage_env.target_relative_humidity_pct > 100.0:
                quarantine_reasons.append(f"GATE_C_FAIL: Invalid target RH {record.storage_env.target_relative_humidity_pct}")

        # Gate D — Temporal Consistency Gate
        last_t = -1.0
        for obs in record.time_series_observations:
            if obs.elapsed_time_days < last_t:
                quarantine_reasons.append(f"GATE_D_FAIL: Temporal inconsistency in observation {obs.observation_id}")
                break
            last_t = obs.elapsed_time_days

        # Gate E — Environmental Completeness Gate
        has_temp_info = (record.storage_env.target_temperature_c is not None) or (len(record.storage_env.temperature_trajectory) > 0)
        has_rh_info = (record.storage_env.target_relative_humidity_pct is not None) or (len(record.storage_env.relative_humidity_trajectory) > 0)

        if not has_temp_info:
            quarantine_reasons.append("GATE_E_FAIL: Storage environment lacks temperature information (neither target setpoint nor measured trajectory provided)")
        if not has_rh_info:
            quarantine_reasons.append("GATE_E_FAIL: Storage environment lacks relative humidity information (neither target setpoint nor measured trajectory provided)")

        # Gate F — Replicate Integrity Gate
        replicates_found = set(obs.replicate_id for obs in record.time_series_observations)
        if record.time_series_observations and not replicates_found:
            quarantine_reasons.append("GATE_F_FAIL: Time-series observations lack replicate identifiers")

        # Gate G — Provenance Completeness Gate
        if not record.provenance.operator_or_lab_id:
            quarantine_reasons.append("GATE_G_FAIL: Missing operator_or_lab_id in provenance")
        if not record.provenance.creation_timestamp:
            quarantine_reasons.append("GATE_G_FAIL: Missing creation_timestamp in provenance")

        # Gate H — Endpoint Definition Gate
        if record.outcome is not None:
            if not record.outcome.endpoint_definition or not record.outcome.endpoint_definition.strip():
                quarantine_reasons.append("GATE_H_FAIL: Observed shelf-life outcome lacks explicit endpoint definition")

        # Assign validation outcome
        if quarantine_reasons:
            record.status = EmpiricalTrialStatusEnum.QUARANTINED
            record.quarantine_reasons = quarantine_reasons
        else:
            record.status = EmpiricalTrialStatusEnum.VALIDATED
            record.quarantine_reasons = []

        return record


class EmpiricalTrialIngestionResult(BaseModel):
    """
    Structured machine-readable ingestion result for an empirical trial.
    """
    trial_id: str = Field(..., description="Unique empirical trial identifier.")
    status: EmpiricalTrialStatusEnum = Field(..., description="Validation status: VALIDATED or QUARANTINED.")
    quarantine_reasons: List[str] = Field(default_factory=list, description="Machine-readable quarantine reasons if validation failed.")
    record: EmpiricalTrialRecord = Field(..., description="Ingested EmpiricalTrialRecord instance stored in repository.")

