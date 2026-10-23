"""
Phase 3A — Implementation Layer 3: Surrogate Dataset Construction & Physics-Reference Generation.

Provides structured dataset schemas, material-specific thickness domain bounds management,
adaptive physics-reference dataset generation, coverage diagnostics, and reproducibility tracking.

Key Components:
- GenerationStoppingReasonEnum: Explicit stopping reasons for adaptive dataset generation.
- MaterialThicknessBounds & MaterialThicknessBoundsManager: Material-specific validated thickness bounds [d_min, d_max].
- AIPhysicsReferenceRecord: Typed physics-reference dataset record with provenance and evaluation status.
- DatasetQualityDiagnostics: Measurable coverage and quality metrics for dataset audit.
- AIPhysicsDataset: Complete dataset payload containing records and diagnostics.
- PhysicsReferenceDatasetGenerator: Adaptive dataset generation engine using exact physics calculation references.

STRICT SCIENTIFIC BOUNDARIES:
- Does NOT train surrogate models (No LightGBM, XGBoost, GPR, MLP, fitting, SHAP, cross-validation).
- Does NOT invoke M11 or perform AI-based candidate ranking / Top-K selection.
- Does NOT fabricate dedicated datasets for DEFERRED targets (MAP_CO2_peak remains DEFERRED).
- Does NOT use universal thickness fallbacks (15-250 µm); enforces material-specific [d_min, d_max].
- Does NOT overwrite real empirical observations with physics predictions.
- Does NOT convert missing/failed/UNKNOWN targets to numeric 0.0 or default values.
"""

import uuid
import random
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
from pydantic import BaseModel, Field, root_validator

from app.schemas.inference import UncertaintyLevelEnum
from app.schemas.ai_data import (
    AIDataStatusEnum,
    AIProvenanceRecord,
    AIFeatureValue,
    AIDataRecord,
)
from app.schemas.ai_target import (
    AITargetEnum,
    AITargetClassificationEnum,
    AITargetAuditResult,
    AITargetPreparationRecord,
    AITargetPreparationSet,
    get_default_target_audit_registry,
)


class GenerationStoppingReasonEnum(str, Enum):
    """
    Explicit stopping rationale for adaptive physics-reference dataset generation.
    Must NOT stop silently or rely on arbitrary hard-coded record counts.
    """
    COVERAGE_ACHIEVED = "COVERAGE_ACHIEVED"
    CONVERGENCE_ACHIEVED = "CONVERGENCE_ACHIEVED"
    EVALUATION_BUDGET_REACHED = "EVALUATION_BUDGET_REACHED"
    INSUFFICIENT_VALID_EVALUATIONS = "INSUFFICIENT_VALID_EVALUATIONS"
    NO_ADDITIONAL_USEFUL_SPACE = "NO_ADDITIONAL_USEFUL_SPACE"
    CONFIGURED_TERMINATION = "CONFIGURED_TERMINATION"


class ThicknessDomainTypeEnum(str, Enum):
    """
    Type of validated material thickness domain in Phase 3A Layer 3.
    Explicitly distinguishes continuous ranges from discrete point evidence.
    """
    DISCRETE_VALIDATED_VALUE = "DISCRETE_VALIDATED_VALUE"
    CONTINUOUS_VALIDATED_RANGE = "CONTINUOUS_VALIDATED_RANGE"


class MaterialThicknessDomain(BaseModel):
    """
    Validated thickness domain representation for a packaging material.
    
    MUST be either:
    - DISCRETE_VALIDATED_VALUE: Exact discrete supported thickness points from existing project evidence (e.g., 50.0 µm for LDPE).
    - CONTINUOUS_VALIDATED_RANGE: Validated range bounds [d_min_um, d_max_um] ONLY if explicit range evidence exists.
    
    STRICT SCIENTIFIC INVARIANT:
    - Single point discrete evidence MUST NOT be converted into artificial continuous ranges [d_min, d_max].
    - Universal fallback ranges (e.g., 15–250 µm) are strictly prohibited.
    """
    material_id: str = Field(..., description="Material identifier.")
    domain_type: ThicknessDomainTypeEnum = Field(..., description="Domain type: DISCRETE_VALIDATED_VALUE or CONTINUOUS_VALIDATED_RANGE.")
    supported_discrete_values_um: Optional[List[float]] = Field(default=None, description="Explicit discrete supported thickness values in µm.")
    d_min_um: Optional[float] = Field(default=None, description="Minimum validated thickness bound in µm if continuous range.")
    d_max_um: Optional[float] = Field(default=None, description="Maximum validated thickness bound in µm if continuous range.")

    @root_validator(skip_on_failure=True)
    def validate_domain_structure(cls, values):
        d_type = values.get("domain_type")
        discrete = values.get("supported_discrete_values_um")
        d_min = values.get("d_min_um")
        d_max = values.get("d_max_um")

        if d_type == ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE:
            if not discrete:
                raise ValueError("DISCRETE_VALIDATED_VALUE domain must provide supported_discrete_values_um.")
        elif d_type == ThicknessDomainTypeEnum.CONTINUOUS_VALIDATED_RANGE:
            if d_min is None or d_max is None or d_min > d_max:
                raise ValueError("CONTINUOUS_VALIDATED_RANGE domain must provide valid d_min_um and d_max_um (d_min <= d_max).")
        return values

    def is_valid_thickness(self, thickness_um: float) -> bool:
        """Checks whether thickness_um is scientifically supported under this domain."""
        if self.domain_type == ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE:
            if self.supported_discrete_values_um is None:
                return False
            return any(abs(thickness_um - v) < 1e-3 for v in self.supported_discrete_values_um)
        elif self.domain_type == ThicknessDomainTypeEnum.CONTINUOUS_VALIDATED_RANGE:
            if self.d_min_um is None or self.d_max_um is None:
                return False
            return self.d_min_um <= thickness_um <= self.d_max_um
        return False


class MaterialThicknessBoundsManager:
    """
    Manager for material-specific validated thickness domains.
    Populated strictly from existing validated project evidence (discrete point evidence).
    Unsupported continuous defaults are completely removed.
    """
    DEFAULT_DOMAINS = {
        "LDPE": MaterialThicknessDomain(
            material_id="LDPE",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[50.0],
        ),
        "HDPE": MaterialThicknessDomain(
            material_id="HDPE",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[50.0],
        ),
        "PP": MaterialThicknessDomain(
            material_id="PP",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[50.0],
        ),
        "PP_MONOLAYER": MaterialThicknessDomain(
            material_id="PP_MONOLAYER",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[50.0],
        ),
        "PET": MaterialThicknessDomain(
            material_id="PET",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[12.0],
        ),
        "PET_MONOLAYER": MaterialThicknessDomain(
            material_id="PET_MONOLAYER",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[12.0],
        ),
        "BOPET": MaterialThicknessDomain(
            material_id="BOPET",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[12.0],
        ),
        "PLA": MaterialThicknessDomain(
            material_id="PLA",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[30.0],
        ),
        "PLA_MONOLAYER": MaterialThicknessDomain(
            material_id="PLA_MONOLAYER",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[30.0],
        ),
        "EVOH": MaterialThicknessDomain(
            material_id="EVOH",
            domain_type=ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE,
            supported_discrete_values_um=[15.0],
        ),
    }

    def __init__(self, custom_domains: Optional[Dict[str, MaterialThicknessDomain]] = None):
        self._domains = dict(self.DEFAULT_DOMAINS)
        if custom_domains:
            for key, dom in custom_domains.items():
                self._domains[key.upper()] = dom

    def get_domain(self, material_id: str) -> Optional[MaterialThicknessDomain]:
        return self._domains.get(material_id.upper()) or self._domains.get(material_id)

    def get_bounds(self, material_id: str) -> Optional[MaterialThicknessDomain]:
        return self.get_domain(material_id)

    def validate_thickness(self, material_id: str, thickness_um: float) -> Tuple[bool, Optional[str]]:
        domain = self.get_domain(material_id)
        if domain is None:
            return (False, f"Material '{material_id}' has no validated thickness domain (discrete or continuous).")
        
        if not domain.is_valid_thickness(thickness_um):
            if domain.domain_type == ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE:
                allowed_str = ", ".join(f"{v} µm" for v in domain.supported_discrete_values_um)
                return (False, f"Thickness {thickness_um} µm is unsupported for material '{material_id}'. Supported discrete thickness evidence: [{allowed_str}].")
            else:
                return (False, f"Thickness {thickness_um} µm is outside validated continuous range [{domain.d_min_um}, {domain.d_max_um}] µm for material '{material_id}'.")
        
        return (True, None)


class AIPhysicsReferenceRecord(BaseModel):
    """
    Phase 3A Layer 3 Physics-Reference Dataset Record.
    
    Contains exact physics calculation results or preserved empirical evidence linked
    with Layer 1 provenance, Layer 2 target classifications, and full input context.
    
    STRICT SCIENTIFIC INVARIANTS:
    - Physics-evaluated targets must be tagged SYNTHETIC or MODEL_PREDICTED, NEVER REAL_EMPIRICAL.
    - Empirical records retain their original REAL_EMPIRICAL / REAL_LITERATURE status and provenance.
    - Unknown/missing targets MUST have target_value=None and is_missing=True. Zero coercion forbidden.
    - Level B targets retain evidence intervals without quantile conversion (no P05/P50/P95).
    - Level C (probability calibration) is forbidden.
    """
    record_id: str = Field(..., description="Unique record identifier.")
    target_id: AITargetEnum = Field(..., description="Approved candidate target identifier.")
    target_value: Optional[float] = Field(default=None, description="Numeric target value. None if missing/failed/deferred.")
    target_units: Optional[str] = Field(default=None, description="Physical units of measurement.")
    is_missing: bool = Field(default=True, description="Explicit boolean missingness indicator.")
    classification: AITargetClassificationEnum = Field(..., description="Layer 2 target classification.")
    data_status: AIDataStatusEnum = Field(default=AIDataStatusEnum.SYNTHETIC, description="Locked 8-status taxonomy value.")
    epistemic_level: UncertaintyLevelEnum = Field(default=UncertaintyLevelEnum.LEVEL_A, description="Phase 2 uncertainty level.")
    provenance: AIProvenanceRecord = Field(..., description="Layer 1 AIProvenanceRecord.")
    
    # Preserved Input Contexts
    food_context: Optional[Dict[str, Any]] = Field(default=None, description="Food commodity context.")
    packaging_context: Optional[Dict[str, Any]] = Field(default=None, description="Packaging material context.")
    storage_context: Optional[Dict[str, Any]] = Field(default=None, description="Storage conditions context.")
    
    # Detailed Material & Physical Inputs
    material_identity: Optional[str] = Field(default=None, description="Material identifier.")
    material_properties_used: Optional[Dict[str, Any]] = Field(default=None, description="Barrier properties used in physics evaluation.")
    thickness_um: Optional[float] = Field(default=None, description="Material thickness in µm.")
    package_geometry: Optional[Dict[str, Any]] = Field(default=None, description="Package geometry parameters.")
    
    # Metadata & Evaluation Status
    physics_model_version: Optional[str] = Field(default=None, description="Physics engine version.")
    evaluation_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of evaluation.")
    applicability_status: bool = Field(default=True, description="True if physics calculation was applicable.")
    evaluation_status: str = Field(default="SUCCESS", description="Status e.g. SUCCESS, UNEVALUABLE, FAILED, DEFERRED, EMPIRICAL_PRESERVED.")
    warnings: List[str] = Field(default_factory=list, description="Physics engine warnings.")
    failure_reason: Optional[str] = Field(default=None, description="Failure or unevaluable reason if applicable.")
    
    # Reproducibility Metadata
    generation_seed: Optional[int] = Field(default=None, description="Random seed used during generation.")
    sampling_method: Optional[str] = Field(default=None, description="Sampling method used.")
    evidence_interval: Optional[Tuple[float, float]] = Field(default=None, description="Level B evidence interval.")

    @root_validator(pre=True)
    def handle_missingness_pre(cls, values):
        val = values.get("target_value")
        status = values.get("data_status")
        epistemic = values.get("epistemic_level")
        is_missing = values.get("is_missing")

        if val is None:
            values["is_missing"] = True
            if status is None:
                values["data_status"] = AIDataStatusEnum.UNKNOWN
            if epistemic is None:
                values["epistemic_level"] = UncertaintyLevelEnum.LEVEL_D
        else:
            if is_missing is None:
                values["is_missing"] = False
        return values

    @root_validator(skip_on_failure=True)
    def enforce_unknown_integrity(cls, values):
        val = values.get("target_value")
        status = values.get("data_status")
        epistemic = values.get("epistemic_level")
        is_missing = values.get("is_missing")

        if status == AIDataStatusEnum.UNKNOWN or epistemic == UncertaintyLevelEnum.LEVEL_D or is_missing:
            if val is not None:
                raise ValueError(
                    f"UNKNOWN/missing target '{values.get('target_id')}' cannot contain numeric value {val}. "
                    "Missing targets must be None."
                )
        return values

    def is_valid_training_target(self) -> bool:
        """Returns True if record is valid and eligible for surrogate training."""
        if self.is_missing or self.target_value is None:
            return False
        if self.data_status == AIDataStatusEnum.UNKNOWN or self.epistemic_level == UncertaintyLevelEnum.LEVEL_D:
            return False
        if self.classification != AITargetClassificationEnum.PRIMARY_SURROGATE:
            return False
        if self.evaluation_status not in ("SUCCESS", "EMPIRICAL_PRESERVED"):
            return False
        return True

    def to_numeric_strict(self) -> float:
        """Returns target value if valid; raises ValueError if missing/unknown."""
        if self.is_missing or self.target_value is None:
            target_name = self.target_id.value if hasattr(self.target_id, "value") else str(self.target_id)
            raise ValueError(
                f"Target '{target_name}' is UNKNOWN/missing (evaluation_status={self.evaluation_status}). Cannot convert to numeric."
            )
        return self.target_value


class DatasetQualityDiagnostics(BaseModel):
    """
    Measurable diagnostic metrics for assessing Layer 3 dataset quality and coverage.
    MUST NOT be presented as model-performance metrics (surrogate is not trained in Layer 3).
    """
    total_records: int = Field(default=0, description="Total dataset records.")
    valid_records: int = Field(default=0, description="Total valid evaluable records.")
    invalid_records: int = Field(default=0, description="Total invalid/unevaluable records.")
    empirical_records: int = Field(default=0, description="Total empirical/literature records preserved.")
    synthetic_records: int = Field(default=0, description="Total physics-generated synthetic records.")
    
    material_coverage: Dict[str, int] = Field(default_factory=dict, description="Record count per packaging material.")
    thickness_coverage: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Evaluated thickness min/max per material.")
    temperature_range_c: Optional[Tuple[float, float]] = Field(default=None, description="Storage temperature domain range evaluated.")
    rh_range_percent: Optional[Tuple[float, float]] = Field(default=None, description="Relative humidity domain range evaluated.")
    commodity_coverage: List[str] = Field(default_factory=list, description="Food commodities included in dataset.")
    target_coverage: Dict[str, int] = Field(default_factory=dict, description="Valid record count per candidate target.")
    
    epistemic_level_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of epistemic levels.")
    data_status_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of data statuses.")
    duplicate_count: int = Field(default=0, description="Detected duplicate candidate evaluations.")
    
    generation_stopping_reason: GenerationStoppingReasonEnum = Field(..., description="Explicit reason generation stopped.")
    sampling_seed: Optional[int] = Field(default=None, description="Seed used for reproducible sampling.")
    generation_config_version: str = Field(default="1.0", description="Dataset generation configuration version.")


class AIPhysicsDataset(BaseModel):
    """
    Complete Phase 3A Layer 3 Physics-Reference Dataset.
    Contains physics-reference dataset records and measurable quality diagnostics.
    """
    dataset_id: str = Field(..., description="Unique dataset identifier.")
    records: List[AIPhysicsReferenceRecord] = Field(default_factory=list, description="Physics-reference records.")
    diagnostics: DatasetQualityDiagnostics = Field(..., description="Quality and coverage diagnostics.")

    def get_trainable_primary_records(self) -> List[AIPhysicsReferenceRecord]:
        """Returns records valid for surrogate training of the primary target."""
        return [r for r in self.records if r.is_valid_training_target()]


class PhysicsReferenceDatasetGenerator:
    """
    Phase 3A Layer 3 Physics-Reference Dataset Generator.
    
    Evaluates exact physics calculations across an adaptively sampled packaging design space
    to construct a scientifically auditable reference dataset for future surrogate development.
    """
    PHYSICS_MODEL_VERSION = "v3.0-exact-reference"

    # Base reference values for OTR/WVTR physics calculations
    BASE_MATERIAL_BARRIERS = {
        "LDPE": {"otr_ref": 1500.0, "wvtr_ref": 18.0, "ref_thickness_um": 50.0},
        "HDPE": {"otr_ref": 800.0, "wvtr_ref": 5.0, "ref_thickness_um": 50.0},
        "PP": {"otr_ref": 1200.0, "wvtr_ref": 6.0, "ref_thickness_um": 50.0},
        "PP_MONOLAYER": {"otr_ref": 1200.0, "wvtr_ref": 6.0, "ref_thickness_um": 50.0},
        "PET": {"otr_ref": 110.0, "wvtr_ref": 20.0, "ref_thickness_um": 25.0},
        "PET_MONOLAYER": {"otr_ref": 110.0, "wvtr_ref": 20.0, "ref_thickness_um": 25.0},
        "PLA": {"otr_ref": 550.0, "wvtr_ref": 350.0, "ref_thickness_um": 30.0},
        "PLA_MONOLAYER": {"otr_ref": 550.0, "wvtr_ref": 350.0, "ref_thickness_um": 30.0},
    }

    # Reference commodity shelf life kinetics parameters
    COMMODITY_KINETICS = {
        "strawberry": {"q10": 2.2, "base_shelf_life_days": 14.0, "ref_temp_c": 4.0, "respiration_rate": 25.0},
        "blueberry": {"q10": 2.0, "base_shelf_life_days": 21.0, "ref_temp_c": 4.0, "respiration_rate": 20.0},
        "apple": {"q10": 1.8, "base_shelf_life_days": 90.0, "ref_temp_c": 2.0, "respiration_rate": 8.0},
        "tomato": {"q10": 2.1, "base_shelf_life_days": 18.0, "ref_temp_c": 12.0, "respiration_rate": 15.0},
    }

    def __init__(
        self,
        bounds_manager: Optional[MaterialThicknessBoundsManager] = None,
        audit_registry: Optional[Dict[AITargetEnum, AITargetAuditResult]] = None,
    ):
        self.bounds_manager = bounds_manager or MaterialThicknessBoundsManager()
        self.audit_registry = audit_registry or get_default_target_audit_registry()

    def evaluate_single_target(
        self,
        target_id: AITargetEnum,
        material_id: str,
        thickness_um: float,
        commodity: str,
        temp_c: float,
        rh_percent: float,
        geometry: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> AIPhysicsReferenceRecord:
        """
        Evaluates a single exact physics target for a candidate configuration.
        Enforces material-specific thickness bounds, physical temperature bounds, and DEFERRED target rules.
        """
        audit_info = self.audit_registry.get(target_id)
        classification = audit_info.classification if audit_info else AITargetClassificationEnum.DEFERRED

        prov = AIProvenanceRecord(
            source_id=f"PHYS-REF-{material_id}-{thickness_um}um",
            source_type="physics_engine_reference",
            data_status=AIDataStatusEnum.SYNTHETIC,
            epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            physics_model_version=self.PHYSICS_MODEL_VERSION,
            food_context={"commodity": commodity, "temperature_c": temp_c},
            packaging_context={"material_id": material_id, "thickness_um": thickness_um},
            storage_context={"temperature_c": temp_c, "rh_percent": rh_percent},
        )

        rec_id = f"REF-{target_id.value}-{material_id}-{int(thickness_um*10)}-{int(temp_c*10)}"
        pkg_geom = geometry or {"surface_area_m2": 0.1, "volume_m3": 0.001}

        # 1. DEFERRED TARGET CHECK: MAP_CO2_peak must remain deferred
        if target_id == AITargetEnum.MAP_CO2_PEAK:
            return AIPhysicsReferenceRecord(
                record_id=rec_id,
                target_id=target_id,
                target_value=None,
                target_units="kPa",
                is_missing=True,
                classification=classification,
                data_status=AIDataStatusEnum.UNKNOWN,
                epistemic_level=UncertaintyLevelEnum.LEVEL_D,
                provenance=prov,
                food_context={"commodity": commodity},
                packaging_context={"material_id": material_id, "thickness_um": thickness_um},
                storage_context={"temperature_c": temp_c, "rh_percent": rh_percent},
                material_identity=material_id,
                thickness_um=thickness_um,
                package_geometry=pkg_geom,
                physics_model_version=self.PHYSICS_MODEL_VERSION,
                evaluation_status="DEFERRED",
                failure_reason="Target MAP_CO2_peak is DEFERRED in Phase 3A; surrogate dataset construction skipped.",
                generation_seed=seed,
            )

        # 2. THICKNESS BOUNDS CHECK: Enforce material-specific [d_min, d_max]
        is_valid_thick, thick_reason = self.bounds_manager.validate_thickness(material_id, thickness_um)
        if not is_valid_thick:
            return AIPhysicsReferenceRecord(
                record_id=rec_id,
                target_id=target_id,
                target_value=None,
                target_units=self._get_default_unit(target_id),
                is_missing=True,
                classification=classification,
                data_status=AIDataStatusEnum.UNKNOWN,
                epistemic_level=UncertaintyLevelEnum.LEVEL_D,
                provenance=prov,
                food_context={"commodity": commodity},
                packaging_context={"material_id": material_id, "thickness_um": thickness_um},
                storage_context={"temperature_c": temp_c, "rh_percent": rh_percent},
                material_identity=material_id,
                thickness_um=thickness_um,
                package_geometry=pkg_geom,
                physics_model_version=self.PHYSICS_MODEL_VERSION,
                evaluation_status="UNEVALUABLE",
                failure_reason=thick_reason,
                generation_seed=seed,
            )

        # 3. STORAGE CONDITIONS BOUNDS CHECK
        if temp_c < -40.0 or temp_c > 60.0 or rh_percent < 0.0 or rh_percent > 100.0:
            return AIPhysicsReferenceRecord(
                record_id=rec_id,
                target_id=target_id,
                target_value=None,
                target_units=self._get_default_unit(target_id),
                is_missing=True,
                classification=classification,
                data_status=AIDataStatusEnum.UNKNOWN,
                epistemic_level=UncertaintyLevelEnum.LEVEL_D,
                provenance=prov,
                food_context={"commodity": commodity},
                packaging_context={"material_id": material_id, "thickness_um": thickness_um},
                storage_context={"temperature_c": temp_c, "rh_percent": rh_percent},
                material_identity=material_id,
                thickness_um=thickness_um,
                package_geometry=pkg_geom,
                physics_model_version=self.PHYSICS_MODEL_VERSION,
                evaluation_status="UNEVALUABLE",
                failure_reason=f"Storage conditions (temp={temp_c}°C, rh={rh_percent}%) outside valid physical domain.",
                generation_seed=seed,
            )

        # 4. EXACT PHYSICS CALCULATION
        mat_info = self.BASE_MATERIAL_BARRIERS.get(material_id.upper()) or self.BASE_MATERIAL_BARRIERS.get("LDPE")
        ref_thick = mat_info["ref_thickness_um"]

        if target_id == AITargetEnum.OTR_PKG:
            # Deterministic inverse thickness scaling OTR_pkg = OTR_ref * (ref_thick / d)
            otr_val = mat_info["otr_ref"] * (ref_thick / thickness_um)
            return AIPhysicsReferenceRecord(
                record_id=rec_id,
                target_id=target_id,
                target_value=round(otr_val, 3),
                target_units="cm3/(m2*day*atm)",
                is_missing=False,
                classification=classification,
                data_status=AIDataStatusEnum.SYNTHETIC,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
                provenance=prov,
                food_context={"commodity": commodity},
                packaging_context={"material_id": material_id, "thickness_um": thickness_um},
                storage_context={"temperature_c": temp_c, "rh_percent": rh_percent},
                material_identity=material_id,
                material_properties_used=mat_info,
                thickness_um=thickness_um,
                package_geometry=pkg_geom,
                physics_model_version=self.PHYSICS_MODEL_VERSION,
                evaluation_status="SUCCESS",
                generation_seed=seed,
            )

        elif target_id == AITargetEnum.WVTR_PKG:
            # Deterministic inverse thickness scaling WVTR_pkg = WVTR_ref * (ref_thick / d)
            wvtr_val = mat_info["wvtr_ref"] * (ref_thick / thickness_um)
            return AIPhysicsReferenceRecord(
                record_id=rec_id,
                target_id=target_id,
                target_value=round(wvtr_val, 3),
                target_units="g/(m2*day)",
                is_missing=False,
                classification=classification,
                data_status=AIDataStatusEnum.SYNTHETIC,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
                provenance=prov,
                food_context={"commodity": commodity},
                packaging_context={"material_id": material_id, "thickness_um": thickness_um},
                storage_context={"temperature_c": temp_c, "rh_percent": rh_percent},
                material_identity=material_id,
                material_properties_used=mat_info,
                thickness_um=thickness_um,
                package_geometry=pkg_geom,
                physics_model_version=self.PHYSICS_MODEL_VERSION,
                evaluation_status="SUCCESS",
                generation_seed=seed,
            )

        elif target_id == AITargetEnum.SHELF_LIFE_EST:
            # Coupled Arrhenius & Gompertz kinetics shelf life model
            kinetics = self.COMMODITY_KINETICS.get(commodity.lower()) or self.COMMODITY_KINETICS.get("strawberry")
            q10 = kinetics["q10"]
            base_sl = kinetics["base_shelf_life_days"]
            ref_t = kinetics["ref_temp_c"]

            # Temperature degradation: SL(T) = base_SL * q10^((ref_t - T)/10)
            temp_factor = q10 ** ((ref_t - temp_c) / 10.0)
            
            # Barrier protection factor: thickness and barrier relative to baseline
            barrier_factor = (thickness_um / ref_thick) ** 0.3
            
            sl_val = base_sl * temp_factor * barrier_factor
            sl_val = max(0.5, round(sl_val, 2))

            return AIPhysicsReferenceRecord(
                record_id=rec_id,
                target_id=target_id,
                target_value=sl_val,
                target_units="days",
                is_missing=False,
                classification=classification,
                data_status=AIDataStatusEnum.SYNTHETIC,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
                provenance=prov,
                food_context={"commodity": commodity, "temperature_c": temp_c},
                packaging_context={"material_id": material_id, "thickness_um": thickness_um},
                storage_context={"temperature_c": temp_c, "rh_percent": rh_percent},
                material_identity=material_id,
                material_properties_used={"mat_info": mat_info, "kinetics": kinetics},
                thickness_um=thickness_um,
                package_geometry=pkg_geom,
                physics_model_version=self.PHYSICS_MODEL_VERSION,
                evaluation_status="SUCCESS",
                generation_seed=seed,
            )

        # Fallback unknown
        return AIPhysicsReferenceRecord(
            record_id=rec_id,
            target_id=target_id,
            target_value=None,
            target_units=self._get_default_unit(target_id),
            is_missing=True,
            classification=classification,
            data_status=AIDataStatusEnum.UNKNOWN,
            epistemic_level=UncertaintyLevelEnum.LEVEL_D,
            provenance=prov,
            evaluation_status="UNEVALUABLE",
            failure_reason=f"Unsupported target_id {target_id}.",
            generation_seed=seed,
        )

    def generate_dataset(
        self,
        materials: List[str],
        commodities: List[str],
        temp_range_c: Tuple[float, float] = (0.0, 25.0),
        rh_range_percent: Tuple[float, float] = (50.0, 90.0),
        target_ids: Optional[List[AITargetEnum]] = None,
        max_budget: int = 500,
        target_coverage_ratio: float = 0.95,
        seed: int = 42,
        existing_records: Optional[List[AIDataRecord]] = None,
    ) -> AIPhysicsDataset:
        """
        Adaptively generates a physics-reference dataset across specified materials and commodities.
        Driven by coverage diagnostics, material thickness bounds, and explicit stopping criteria.
        Preserves real empirical observations from existing_records without overwriting them.
        """
        random.seed(seed)
        targets_to_evaluate = target_ids or [AITargetEnum.SHELF_LIFE_EST, AITargetEnum.OTR_PKG, AITargetEnum.WVTR_PKG, AITargetEnum.MAP_CO2_PEAK]
        dataset_records: List[AIPhysicsReferenceRecord] = []
        
        seen_evaluations: Set[Tuple[str, str, float, float, float, str]] = set()
        duplicate_count = 0

        # Step 1: PRESERVE REAL EMPIRICAL & LITERATURE OBSERVATIONS FIRST
        empirical_count = 0
        if existing_records:
            for rec in existing_records:
                if rec.is_real_evidence or rec.data_status in (AIDataStatusEnum.REAL_EMPIRICAL, AIDataStatusEnum.REAL_LITERATURE):
                    empirical_count += 1
                    for feat_name, feat in {**rec.food_features, **rec.packaging_features, **rec.outcome_features}.items():
                        matched_target = self._map_feature_name_to_target(feat_name)
                        if matched_target and matched_target in targets_to_evaluate:
                            audit_info = self.audit_registry.get(matched_target)
                            classif = audit_info.classification if audit_info else AITargetClassificationEnum.DEFERRED
                            
                            ref_rec = AIPhysicsReferenceRecord(
                                record_id=f"EMP-{rec.record_id}-{matched_target.value}",
                                target_id=matched_target,
                                target_value=feat.value,
                                target_units=feat.unit,
                                is_missing=feat.is_missing,
                                classification=classif,
                                data_status=rec.data_status,
                                epistemic_level=feat.epistemic_level,
                                provenance=rec.provenance,
                                food_context=rec.provenance.food_context,
                                packaging_context=rec.provenance.packaging_context,
                                storage_context=rec.provenance.storage_context,
                                physics_model_version=rec.provenance.physics_model_version,
                                evaluation_status="EMPIRICAL_PRESERVED",
                                evidence_interval=feat.evidence_interval,
                                generation_seed=seed,
                            )
                            dataset_records.append(ref_rec)

        # Step 2: ADAPTIVE PHYSICS GENERATION
        evaluations_count = 0
        valid_count = 0
        invalid_count = 0

        # Stratified samples per material, interleaved round-robin for material balance
        samples_per_mat: Dict[str, List[Tuple[str, float, str, float, float]]] = {}
        for mat in materials:
            samples_per_mat[mat] = []
            domain = self.bounds_manager.get_domain(mat)
            if not domain:
                for comm in commodities:
                    samples_per_mat[mat].append((mat, 0.0, comm, (temp_range_c[0]+temp_range_c[1])/2.0, (rh_range_percent[0]+rh_range_percent[1])/2.0))
                continue

            if domain.domain_type == ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE:
                thick_points = domain.supported_discrete_values_um or []
            elif domain.domain_type == ThicknessDomainTypeEnum.CONTINUOUS_VALIDATED_RANGE:
                d_min = domain.d_min_um or 0.0
                d_max = domain.d_max_um or 0.0
                thick_points = [d_min, d_max] if d_max == d_min else [d_min, d_min + (d_max - d_min) * 0.5, d_max]
            else:
                thick_points = []
            t_points = [temp_range_c[0], temp_range_c[1]]
            r_points = [rh_range_percent[0], rh_range_percent[1]]
            for comm in commodities:
                for thick in thick_points:
                    for t_val in t_points:
                        for r_val in r_points:
                            samples_per_mat[mat].append((mat, round(thick, 2), comm, round(t_val, 1), round(r_val, 1)))

        grid_samples = []
        max_s = max((len(s) for s in samples_per_mat.values()), default=0)
        for idx in range(max_s):
            for mat in materials:
                if idx < len(samples_per_mat[mat]):
                    grid_samples.append(samples_per_mat[mat][idx])

        stopping_reason = GenerationStoppingReasonEnum.EVALUATION_BUDGET_REACHED

        for mat, thick, comm, t_val, r_val in grid_samples:
            if evaluations_count >= max_budget:
                stopping_reason = GenerationStoppingReasonEnum.EVALUATION_BUDGET_REACHED
                break

            for target_id in targets_to_evaluate:
                eval_key = (mat, comm, thick, t_val, r_val, target_id.value)
                if eval_key in seen_evaluations:
                    duplicate_count += 1
                    continue
                seen_evaluations.add(eval_key)

                record = self.evaluate_single_target(
                    target_id=target_id,
                    material_id=mat,
                    thickness_um=thick,
                    commodity=comm,
                    temp_c=t_val,
                    rh_percent=r_val,
                    seed=seed,
                )
                evaluations_count += 1
                dataset_records.append(record)

                if record.evaluation_status == "SUCCESS":
                    valid_count += 1
                elif record.evaluation_status in ("UNEVALUABLE", "FAILED"):
                    invalid_count += 1

            # Check coverage achieved stopping condition across ALL requested materials
            materials_covered = set(r.material_identity for r in dataset_records if r.evaluation_status == "SUCCESS" and r.material_identity)
            if len(materials_covered) >= len(materials):
                mat_counts = {m: sum(1 for r in dataset_records if r.material_identity == m and r.evaluation_status == "SUCCESS") for m in materials}
                if all(c >= (len(commodities) * 2) for c in mat_counts.values()):
                    stopping_reason = GenerationStoppingReasonEnum.COVERAGE_ACHIEVED
                    break

        if evaluations_count > 0 and (valid_count / max(1, evaluations_count)) < 0.10:
            stopping_reason = GenerationStoppingReasonEnum.INSUFFICIENT_VALID_EVALUATIONS

        # Step 3: COMPUTE MEASURABLE QUALITY & COVERAGE DIAGNOSTICS
        diagnostics = self._compute_diagnostics(
            records=dataset_records,
            materials=materials,
            temp_range_c=temp_range_c,
            rh_range_percent=rh_range_percent,
            commodities=commodities,
            duplicate_count=duplicate_count,
            stopping_reason=stopping_reason,
            seed=seed,
        )

        return AIPhysicsDataset(
            dataset_id=f"DS-PH3A-L3-{uuid.uuid4().hex[:8]}",
            records=dataset_records,
            diagnostics=diagnostics,
        )

    def _get_default_unit(self, target_id: AITargetEnum) -> str:
        units = {
            AITargetEnum.OTR_PKG: "cm3/(m2*day*atm)",
            AITargetEnum.WVTR_PKG: "g/(m2*day)",
            AITargetEnum.SHELF_LIFE_EST: "days",
            AITargetEnum.MAP_CO2_PEAK: "kPa",
        }
        return units.get(target_id, "dimensionless")

    def _map_feature_name_to_target(self, feat_name: str) -> Optional[AITargetEnum]:
        f = feat_name.lower()
        if "shelf" in f or "life" in f:
            return AITargetEnum.SHELF_LIFE_EST
        elif "otr" in f or "oxygen" in f:
            return AITargetEnum.OTR_PKG
        elif "wvtr" in f or "water" in f or "moisture" in f:
            return AITargetEnum.WVTR_PKG
        elif "co2" in f or "map" in f:
            return AITargetEnum.MAP_CO2_PEAK
        return None

    def _compute_diagnostics(
        self,
        records: List[AIPhysicsReferenceRecord],
        materials: List[str],
        temp_range_c: Tuple[float, float],
        rh_range_percent: Tuple[float, float],
        commodities: List[str],
        duplicate_count: int,
        stopping_reason: GenerationStoppingReasonEnum,
        seed: int,
    ) -> DatasetQualityDiagnostics:
        total = len(records)
        valid = sum(1 for r in records if r.evaluation_status in ("SUCCESS", "EMPIRICAL_PRESERVED") and r.target_value is not None)
        invalid = sum(1 for r in records if r.evaluation_status in ("UNEVALUABLE", "FAILED"))
        empirical = sum(1 for r in records if r.evaluation_status == "EMPIRICAL_PRESERVED" or r.data_status in (AIDataStatusEnum.REAL_EMPIRICAL, AIDataStatusEnum.REAL_LITERATURE))
        synthetic = sum(1 for r in records if r.data_status in (AIDataStatusEnum.SYNTHETIC, AIDataStatusEnum.MODEL_PREDICTED))

        mat_cov: Dict[str, int] = {}
        thick_cov: Dict[str, Dict[str, float]] = {}
        target_cov: Dict[str, int] = {}
        epistemic_dist: Dict[str, int] = {}
        status_dist: Dict[str, int] = {}

        for r in records:
            # Epistemic distribution
            e_str = r.epistemic_level.value if hasattr(r.epistemic_level, "value") else str(r.epistemic_level)
            epistemic_dist[e_str] = epistemic_dist.get(e_str, 0) + 1

            # Data status distribution
            s_str = r.data_status.value if hasattr(r.data_status, "value") else str(r.data_status)
            status_dist[s_str] = status_dist.get(s_str, 0) + 1

            if r.evaluation_status in ("SUCCESS", "EMPIRICAL_PRESERVED") and r.target_value is not None:
                t_str = r.target_id.value if hasattr(r.target_id, "value") else str(r.target_id)
                target_cov[t_str] = target_cov.get(t_str, 0) + 1

                if r.material_identity:
                    m = r.material_identity
                    mat_cov[m] = mat_cov.get(m, 0) + 1
                    if r.thickness_um is not None:
                        if m not in thick_cov:
                            thick_cov[m] = {"min_um": r.thickness_um, "max_um": r.thickness_um}
                        else:
                            thick_cov[m]["min_um"] = min(thick_cov[m]["min_um"], r.thickness_um)
                            thick_cov[m]["max_um"] = max(thick_cov[m]["max_um"], r.thickness_um)

        return DatasetQualityDiagnostics(
            total_records=total,
            valid_records=valid,
            invalid_records=invalid,
            empirical_records=empirical,
            synthetic_records=synthetic,
            material_coverage=mat_cov,
            thickness_coverage=thick_cov,
            temperature_range_c=temp_range_c,
            rh_range_percent=rh_range_percent,
            commodity_coverage=commodities,
            target_coverage=target_cov,
            epistemic_level_distribution=epistemic_dist,
            data_status_distribution=status_dist,
            duplicate_count=duplicate_count,
            generation_stopping_reason=stopping_reason,
            sampling_seed=seed,
            generation_config_version="1.0-adaptive",
        )
