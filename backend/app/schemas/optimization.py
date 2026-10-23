from typing import Any, Dict, List, Optional, Tuple, Literal
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.physics import CalculationStatus, ScientificTraceability
from app.schemas.constraints import ConstraintStatus, ConditionMatchLevel, ConstraintEvaluation
from app.schemas.candidate_feasibility import FilteringResult
from app.schemas.packaging_requirements import (
    PackagingRequirementEnvelope,
    MoistureRequirement,
    MicrobialRequirement,
    GasExchangeRequirement,
    ShelfLifeRequirement
)


class ObjectiveDirection(str, Enum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class EvidenceTier(str, Enum):
    TIER_1_EMPIRICAL = "TIER_1_EMPIRICAL"
    TIER_2_PREDICTIVE_QSAR = "TIER_2_PREDICTIVE_QSAR"


class UncertaintyType(str, Enum):
    DETERMINISTIC_POINT = "DETERMINISTIC_POINT"
    BOUNDED_INTERVAL = "BOUNDED_INTERVAL"
    QSAR_CONFIDENCE_INTERVAL = "QSAR_CONFIDENCE_INTERVAL"
    UNKNOWN = "UNKNOWN"


class OptimizationExecutionTier(str, Enum):
    LATTICE_LOOKUP = "LATTICE_LOOKUP"
    WARM_START = "WARM_START"
    DEEP_OPTIMIZATION = "DEEP_OPTIMIZATION"


# ---------------------------------------------------------
# Candidate Base Definitions
# ---------------------------------------------------------

class CandidateEvidenceReference(BaseModel):
    source_id: str = Field(..., description="UUID of the original source")
    source_name: str = Field(..., description="Name of the source")
    record_identifier_in_source: str = Field(...)
    evidence_classification: str = Field(..., description="E.g., EXPERIMENTAL_LITERATURE_DATA or MODEL_PREDICTED")
    verification_status: str = Field(...)
    synthetic_prediction_warning: Optional[str] = Field(default=None, description="Warning if data is predicted via QSAR/ML")
    literature_references: Optional[List[Dict[str, Any]]] = None

class BarrierPropertyMetric(BaseModel):
    value: float = Field(..., ge=0.0)
    unit: str
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    is_range: bool = False
    test_temperature_c: Optional[float] = None
    test_rh_percent: Optional[float] = None
    test_standard: Optional[str] = None

class CandidateBarrierProperties(BaseModel):
    otr: Optional[BarrierPropertyMetric] = Field(default=None, description="Oxygen Transmission Rate")
    co2tr: Optional[BarrierPropertyMetric] = Field(default=None, description="Carbon Dioxide Transmission Rate")
    wvtr: Optional[BarrierPropertyMetric] = Field(default=None, description="Water Vapor Transmission Rate")

class PackageGeometry(BaseModel):
    surface_area_m2: Optional[float] = Field(default=None, gt=0.0)
    headspace_volume_cm3: Optional[float] = Field(default=None, ge=0.0)
    product_mass_kg: Optional[float] = Field(default=None, gt=0.0)

class CandidateDecisionVariables(BaseModel):
    structure_type: Optional[str] = Field(default=None, description="MONOLAYER, MULTILAYER, COATED, or None")
    layer_sequence: List[str] = Field(default_factory=list)
    total_thickness_um: Optional[float] = Field(default=None, gt=0.0)
    thickness_is_continuous_scaled: bool = Field(default=False)
    thickness_source: str = Field(..., description="Must explicitly state provenance, e.g., 'observed_discrete_m5'")

class PackagingCandidate(BaseModel):
    candidate_id: str
    material_id: str
    material_name: str
    brand_grade: Optional[str] = None
    decision_variables: CandidateDecisionVariables
    barrier_properties: CandidateBarrierProperties
    condition_match: ConditionMatchLevel
    provenance: CandidateEvidenceReference


# ---------------------------------------------------------
# F-10.1 Integration Interface (Phase 4 Candidate-Specific Recalculation)
# ---------------------------------------------------------

class CandidateScientificEvaluationRequest(BaseModel):
    candidate: PackagingCandidate
    base_requirement_envelope: PackagingRequirementEnvelope
    package_geometry: Optional[PackageGeometry] = None

class CandidateScientificEvaluationResult(BaseModel):
    candidate_id: str
    updated_moisture_requirement: MoistureRequirement
    updated_gas_exchange_requirement: Optional[GasExchangeRequirement] = None
    updated_microbial_requirement: Optional[MicrobialRequirement] = None
    candidate_shelf_life_requirement: ShelfLifeRequirement
    overall_status: CalculationStatus
    traceability: ScientificTraceability
    
    # Phase 5 Constraints & Feasibility
    constraint_profile: Optional['CandidateConstraintStatus'] = Field(
        default=None,
        description="Detailed hard constraint evaluations and aggregate feasibility status (Phase 5)"
    )
    
    # Uncertainty and Error Tracking
    uncertainty_profile: Optional['UncertaintyProfile'] = Field(
        default=None,
        description="Aggregated uncertainty taxonomy and confidence intervals"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Aggregated evaluation warnings that do not independently cause failure"
    )
    failure_reasons: List[str] = Field(
        default_factory=list,
        description="Explicit reasons for constraint violations or unknown statuses"
    )


# ---------------------------------------------------------
# Objective & Pareto Definitions
# ---------------------------------------------------------

class ObjectiveValue(BaseModel):
    objective_name: str
    direction: ObjectiveDirection
    value: Optional[float] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    is_interval: bool = False
    unit: str
    status: CalculationStatus
    evidence_references: List[str] = Field(default_factory=list)
    explanation_metadata: Optional[str] = None

class CandidateConstraintStatus(BaseModel):
    all_hard_constraints_satisfied: bool
    evaluations: List[ConstraintEvaluation] = Field(default_factory=list)
    overall_status: ConstraintStatus
    condition_match: ConditionMatchLevel

class UncertaintyProfile(BaseModel):
    uncertainty_type: UncertaintyType
    objective_intervals: Dict[str, Tuple[float, float]] = Field(default_factory=dict)

class ExplanationPayload(BaseModel):
    trade_off_summary: str
    limiting_barrier: str
    primary_strength: str

class ParetoCandidate(BaseModel):
    pareto_candidate_id: str
    candidate_design: PackagingCandidate
    objective_values: Dict[str, ObjectiveValue]
    constraint_compliance_summary: CandidateConstraintStatus
    uncertainty_profile: UncertaintyProfile
    evidence_tier: EvidenceTier
    traceability: ScientificTraceability
    explanation_payload: ExplanationPayload


# ---------------------------------------------------------
# Optimization Interfaces
# ---------------------------------------------------------

class SolverConfiguration(BaseModel):
    execution_tier: OptimizationExecutionTier
    max_iterations: int = 100
    population_size: int = 50
    tolerance: float = 1e-4

class OptimizationInputEnvelope(BaseModel):
    optimization_run_id: str
    commodity: str
    target_shelf_life_days: int
    storage_temperature_c: Optional[float] = None
    relative_humidity_percent: Optional[float] = None
    package_geometry: PackageGeometry
    packaging_requirement_envelope: PackagingRequirementEnvelope
    filtering_result: FilteringResult
    eligible_candidate_materials: List[PackagingCandidate]
    active_objectives: List[str]
    solver_configuration: SolverConfiguration

class OptimizationMetadata(BaseModel):
    algorithm_name: str
    iterations_completed: int
    execution_time_ms: float
    cache_hit: bool

class ParetoFront(BaseModel):
    optimization_run_id: str
    timestamp: str
    candidate_count: int
    candidates: List[ParetoCandidate]
    hypervolume_indicator: Optional[float] = None
    solver_metadata: OptimizationMetadata
    constraint_policy_version: str

class CounterfactualPerturbations(BaseModel):
    delta_target_shelf_life_days: Optional[int] = None
    delta_storage_temperature_c: Optional[float] = None
    delta_relative_humidity_percent: Optional[float] = None
    delta_package_surface_area_m2: Optional[float] = None
    relaxation_factor_wvtr: Optional[float] = Field(default=None, ge=0.5, le=2.0)

class CounterfactualQuery(BaseModel):
    base_run_id: str
    perturbations: CounterfactualPerturbations
