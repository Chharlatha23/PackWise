"""
Schema definitions for the Recommendation Service and API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.packaging_request import PackagingRequest
from app.schemas.inference import PropertyInferenceProfile
from app.schemas.packaging_requirements import PackagingRequirementEnvelope
from app.schemas.optimization import ParetoFront, CandidateConstraintStatus
from app.schemas.physics import ScientificTraceability
from app.schemas.explainability import (
    CandidateExplainabilityReport,
    PipelineExplainabilitySummary
)


class CandidateEvaluationSummary(BaseModel):
    """Structured summary of a single candidate material's evaluation against Phase 5 constraints."""

    candidate_id: str = Field(..., description="Unique candidate ID")
    material_id: str = Field(..., description="M5 material ID")
    material_name: str = Field(..., description="Descriptive name of candidate material")
    total_thickness_um: Optional[float] = Field(default=None, description="Total nominal thickness in µm")
    constraint_status: str = Field(..., description="Phase 5 constraint status: FEASIBLE, INFEASIBLE, UNKNOWN")
    all_hard_constraints_satisfied: bool = Field(..., description="True if all hard barrier constraints pass")
    evaluation_details: Optional[CandidateConstraintStatus] = Field(default=None, description="Detailed constraint evaluations")
    applicability_state: Optional[str] = Field(default=None, description="Surrogate applicability state: IN_DOMAIN, OUT_OF_DOMAIN, UNEVALUABLE, NEAR_BOUNDARY")
    prediction_status: Optional[str] = Field(default=None, description="Surrogate prediction status: PREDICTED, BYPASSED_OOD, DISABLED_UNEVALUABLE, FAILED_COMPATIBILITY")
    evaluation_state: Optional[str] = Field(default=None, description="Exact-physics evaluation state: NOT_EVALUATED, EVALUATION_UNRESOLVED, EVALUATED_NOT_ELIGIBLE, ELIGIBLE")
    gate3_evaluable: Optional[bool] = Field(default=None, description="Pre-execution Gate 3 scientific evaluability check result")
    predicted_shelf_life: Optional[float] = Field(default=None, description="Layer 4 surrogate predicted shelf life in days if PREDICTED")
    surrogate_lineage: Optional[Dict[str, Any]] = Field(default=None, description="Registered model manifest lineage if PREDICTED")
    explainability: Optional[CandidateExplainabilityReport] = Field(default=None, description="M11 candidate feasibility, constraint, objective, provenance, and counterfactual explanation report")


class RecommendationResponse(BaseModel):
    """
    Structured end-to-end response for a food packaging recommendation request.

    Preserves exact Pareto sets, interval-valued scientific outputs, and provenance
    traceability. Does NOT assign scalar material rankings or fake 'best material' scores.
    """

    recommendation_run_id: str = Field(..., description="Unique run identifier for this recommendation execution")
    timestamp: str = Field(..., description="ISO 8601 timestamp of execution")
    request: PackagingRequest = Field(..., description="Original input request")
    inference_profile: PropertyInferenceProfile = Field(..., description="Phase 3 resolved commodity properties")
    requirement_envelope: PackagingRequirementEnvelope = Field(..., description="Phase 4 scientific requirement envelope")
    total_candidates_evaluated: int = Field(..., description="Total candidate designs evaluated from evidence database")
    feasible_candidates_count: int = Field(..., description="Number of candidates satisfying all hard constraints")
    infeasible_candidates_count: int = Field(..., description="Number of candidates violating at least one hard constraint")
    unknown_candidates_count: int = Field(..., description="Number of candidates with indeterminate constraint evaluations")
    pareto_front: ParetoFront = Field(..., description="Exact non-dominated Pareto front of feasible candidates")
    candidate_summaries: List[CandidateEvaluationSummary] = Field(default_factory=list, description="Summaries of all evaluated candidates")
    all_warnings: List[str] = Field(default_factory=list, description="Warnings encountered across the pipeline")
    traceability_log: List[ScientificTraceability] = Field(default_factory=list, description="Scientific equation and model traceability log")
    pipeline_explainability: Optional[PipelineExplainabilitySummary] = Field(default=None, description="M11 pipeline-wide explainability summary report")
