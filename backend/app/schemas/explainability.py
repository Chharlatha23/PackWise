"""
M11: Explainability and Counterfactual Analysis Schemas.

Defines structured data models for:
- ConstraintExplanation
- ObjectiveExplanation
- CounterfactualExplanation
- EvidenceProvenanceReference
- CandidateExplainabilityReport
- PipelineExplainabilitySummary
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConstraintExplanation(BaseModel):
    """Structured explanation of a single candidate barrier constraint evaluation."""

    constraint_type: str = Field(..., description="Constraint dimension e.g. gas_exchange_otr, moisture_wvtr")
    required_relationship: str = Field(..., description="Comparison operator e.g. '>=', '<='")
    required_value: Optional[float] = Field(default=None, description="Scalar required value if deterministic point")
    required_value_min: Optional[float] = Field(default=None, description="Min required value if range")
    required_value_max: Optional[float] = Field(default=None, description="Max required value if range")
    required_unit: str = Field(..., description="Canonical unit for requirement")
    candidate_value: Optional[float] = Field(default=None, description="Candidate scalar metric value")
    candidate_value_min: Optional[float] = Field(default=None, description="Candidate min metric value if interval")
    candidate_value_max: Optional[float] = Field(default=None, description="Candidate max metric value if interval")
    candidate_unit: str = Field(..., description="Canonical unit for candidate metric")
    status: str = Field(..., description="FEASIBLE, INFEASIBLE, or UNKNOWN")
    explanation_text: str = Field(..., description="Human-readable scientific explanation of constraint outcome")
    evidence_reference_ids: List[str] = Field(default_factory=list, description="IDs of underlying M5 evidence records")


class ObjectiveExplanation(BaseModel):
    """Structured explanation of an M6-B3 objective value and trade-off comparisons."""

    objective_name: str = Field(..., description="M6-B3 objective identifier")
    direction: str = Field(..., description="MINIMIZE or MAXIMIZE")
    value: Optional[float] = Field(default=None, description="Scalar objective value if deterministic point")
    value_min: Optional[float] = Field(default=None, description="Min objective value if interval")
    value_max: Optional[float] = Field(default=None, description="Max objective value if interval")
    is_interval: bool = Field(default=False, description="True if objective value is a bounded interval")
    unit: str = Field(..., description="Objective metric unit")
    status: str = Field(..., description="CALCULATED or UNKNOWN")
    explanation_text: str = Field(..., description="Descriptive explanation of objective value")
    trade_off_comparisons: List[str] = Field(default_factory=list, description="Descriptive comparisons against other Pareto candidates")


class CounterfactualExplanation(BaseModel):
    """Structured explanation of a deterministic feasibility status-flip threshold."""

    counterfactual_type: str = Field(..., description="Type of threshold flip analysis")
    target_property: str = Field(..., description="Target property name e.g. allowable_wvtr, required_otr")
    current_status: str = Field(..., description="Current status: FEASIBLE, INFEASIBLE, or UNKNOWN")
    current_candidate_value: Optional[float] = Field(default=None, description="Current candidate value")
    current_threshold_value: Optional[float] = Field(default=None, description="Current baseline threshold value")
    counterfactual_threshold_value: Optional[float] = Field(default=None, description="Scalar threshold causing status flip")
    counterfactual_threshold_min: Optional[float] = Field(default=None, description="Min threshold if interval")
    counterfactual_threshold_max: Optional[float] = Field(default=None, description="Max threshold if interval")
    is_interval_threshold: bool = Field(default=False, description="True if counterfactual threshold is an interval")
    unit: str = Field(..., description="Metric unit for threshold")
    status_flip_condition: str = Field(..., description="BECOMES_INFEASIBLE_IF, BECOMES_FEASIBLE_IF, or UNRESOLVED_DUE_TO_UNKNOWN")
    explanation_text: str = Field(..., description="Scientific description of counterfactual condition")
    is_resolved: bool = Field(default=True, description="False if counterfactual is unresolved due to UNKNOWN missing data")


class EvidenceProvenanceReference(BaseModel):
    """Structured reference for candidate evidence provenance and verification status."""

    evidence_id: Optional[str] = Field(default=None, description="Evidence record ID")
    source_id: Optional[str] = Field(default=None, description="Original source ID")
    source_name: Optional[str] = Field(default=None, description="Original source name")
    material_id: str = Field(..., description="M5 material ID")
    record_identifier_in_source: Optional[str] = Field(default=None, description="Record identifier in source database")
    evidence_classification: str = Field(..., description="EXPERIMENTAL_LITERATURE_DATA, MODEL_PREDICTED, etc.")
    verification_status: str = Field(..., description="Verification status e.g. VERIFIED_EXTRACT")
    synthetic_prediction_warning: Optional[str] = Field(default=None, description="Warning if data is predicted")
    is_model_predicted: bool = Field(default=False, description="True if data originates from predictive model/QSAR")


class CandidateExplainabilityReport(BaseModel):
    """Comprehensive explainability and counterfactual report for a single evaluated candidate."""

    candidate_id: str = Field(..., description="Candidate UUID")
    material_id: str = Field(..., description="M5 Material UUID")
    material_name: str = Field(..., description="Human-readable material name")
    total_thickness_um: float = Field(..., description="Total nominal thickness in µm")
    overall_feasibility_status: str = Field(..., description="FEASIBLE, INFEASIBLE, or UNKNOWN")
    applicability_state: Optional[str] = Field(default=None, description="Surrogate applicability state: IN_DOMAIN, OUT_OF_DOMAIN, UNEVALUABLE, NEAR_BOUNDARY")
    prediction_status: Optional[str] = Field(default=None, description="Surrogate prediction status: PREDICTED, BYPASSED_OOD, DISABLED_UNEVALUABLE, FAILED_COMPATIBILITY")
    evaluation_state: Optional[str] = Field(default=None, description="Exact-physics evaluation state: NOT_EVALUATED, EVALUATION_UNRESOLVED, EVALUATED_NOT_ELIGIBLE, ELIGIBLE")
    ai_search_explanation: Optional[str] = Field(default=None, description="AI surrogate prioritization & search behavior explanation")
    physics_limiting_explanation: Optional[str] = Field(default=None, description="Physics-derived limiting factor explanation")
    surrogate_lineage: Optional[Dict[str, Any]] = Field(default=None, description="Registered model manifest lineage if prediction exists")
    constraint_explanations: List[ConstraintExplanation] = Field(default_factory=list, description="Per-constraint explanations")
    objective_explanations: List[ObjectiveExplanation] = Field(default_factory=list, description="Per-objective explanations")
    provenance_reference: EvidenceProvenanceReference = Field(..., description="Evidence provenance reference")
    counterfactual_explanations: List[CounterfactualExplanation] = Field(default_factory=list, description="Deterministic counterfactual threshold analysis")
    pareto_explanation: Optional[str] = Field(default=None, description="Descriptive explanation of Pareto dominance membership")
    warnings: List[str] = Field(default_factory=list, description="Candidate-specific warnings")


class PipelineExplainabilitySummary(BaseModel):
    """Pipeline-wide summary containing individual candidate explainability reports."""

    total_candidates_explained: int = Field(..., description="Total candidates with generated explainability reports")
    feasible_candidates_explained: int = Field(..., description="Feasible candidate count")
    infeasible_candidates_explained: int = Field(..., description="Infeasible candidate count")
    unknown_candidates_explained: int = Field(..., description="Unknown candidate count")
    candidate_reports: Dict[str, CandidateExplainabilityReport] = Field(default_factory=dict, description="Candidate reports mapped by candidate_id")
