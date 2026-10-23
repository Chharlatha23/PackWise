"""
M12: Real-World Feedback & Model Update Schemas.

Defines structured data models for:
- FeedbackSubmission
- PackageConfigurationSchema
- StorageConditionsSchema
- PredictedOutputSchema
- MeasurementComparison
- ModelUpdateCandidateSchema
- FeedbackResponse
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from app.models.feedback import (
    ObservationOrigin,
    ValidationStatus,
    ComparisonStatus,
    ModelUpdateStatus
)


class PackageConfigurationSchema(BaseModel):
    """Configuration metrics for the packaging trial design."""

    total_thickness_um: Optional[float] = Field(default=None, description="Nominal thickness in µm")
    package_surface_area_m2: Optional[float] = Field(default=None, description="Package surface area in m²")
    package_headspace_volume_cm3: Optional[float] = Field(default=None, description="Headspace volume in cm³")
    product_mass_kg: Optional[float] = Field(default=None, description="Product mass in kg")


class StorageConditionsSchema(BaseModel):
    """Storage environment conditions during trial."""

    temperature_c: Optional[float] = Field(default=None, description="Storage temperature in °C")
    rh_percent: Optional[float] = Field(default=None, description="Relative humidity percentage (0-100%)")
    duration_days: Optional[float] = Field(default=None, description="Storage trial duration in days")


class PredictedOutputSchema(BaseModel):
    """Baseline prediction/evaluation outputs for comparison against observations."""

    shelf_life_days: Optional[float] = Field(default=None, description="Predicted shelf life point value in days")
    shelf_life_min: Optional[float] = Field(default=None, description="Predicted shelf life min interval bound")
    shelf_life_max: Optional[float] = Field(default=None, description="Predicted shelf life max interval bound")
    
    otr: Optional[float] = Field(default=None, description="Predicted OTR in cm3/(m2*day*atm)")
    otr_min: Optional[float] = Field(default=None, description="Predicted OTR min interval bound")
    otr_max: Optional[float] = Field(default=None, description="Predicted OTR max interval bound")
    
    co2tr: Optional[float] = Field(default=None, description="Predicted CO2TR in cm3/(m2*day*atm)")
    co2tr_min: Optional[float] = Field(default=None, description="Predicted CO2TR min interval bound")
    co2tr_max: Optional[float] = Field(default=None, description="Predicted CO2TR max interval bound")
    
    wvtr: Optional[float] = Field(default=None, description="Predicted WVTR in g/(m2*day)")
    wvtr_min: Optional[float] = Field(default=None, description="Predicted WVTR min interval bound")
    wvtr_max: Optional[float] = Field(default=None, description="Predicted WVTR max interval bound")
    
    feasibility_status: Optional[str] = Field(default=None, description="Predicted feasibility status (FEASIBLE, INFEASIBLE, UNKNOWN)")


class FeedbackSubmission(BaseModel):
    """Incoming feedback submission payload for real-world or trial packaging observations."""

    recommendation_run_id: Optional[str] = Field(default=None, description="Associated recommendation run ID if available")
    candidate_id: Optional[str] = Field(default=None, description="Associated candidate design ID")
    material_id: Optional[str] = Field(default=None, description="Associated M5 material ID")
    
    trial_identifier: str = Field(..., description="Unique trial or experiment identifier e.g. TRIAL-2026-001")
    observation_origin: ObservationOrigin = Field(..., description="Origin of feedback: REAL_PRODUCTION, REAL_PILOT, SYNTHETIC_TEST, DEMO")
    observation_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of trial observation")
    
    package_configuration: Optional[PackageConfigurationSchema] = Field(default=None, description="Trial package geometry and thickness")
    storage_conditions: Optional[StorageConditionsSchema] = Field(default=None, description="Observed trial storage environment")
    
    observed_shelf_life_days: Optional[float] = Field(default=None, description="Measured shelf life in days")
    observed_otr: Optional[float] = Field(default=None, description="Measured OTR in cm3/(m2*day*atm)")
    observed_co2tr: Optional[float] = Field(default=None, description="Measured CO2TR in cm3/(m2*day*atm)")
    observed_wvtr: Optional[float] = Field(default=None, description="Measured WVTR in g/(m2*day)")
    observed_product_condition: Optional[str] = Field(default=None, description="Observed qualitative product state e.g. ACCEPTABLE, SPOILED")
    
    predicted_outputs_override: Optional[PredictedOutputSchema] = Field(default=None, description="Explicit baseline prediction values if not querying database recommendation run")
    evidence_source_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Lab, investigator, or trial source metadata")


class MeasurementComparison(BaseModel):
    """Deterministic predicted vs. observed comparison result for a single property."""

    property_name: str = Field(..., description="Property metric identifier: shelf_life_days, OTR, CO2TR, WVTR")
    predicted_value: Optional[float] = Field(default=None, description="Predicted point value")
    predicted_min: Optional[float] = Field(default=None, description="Predicted interval min bound")
    predicted_max: Optional[float] = Field(default=None, description="Predicted interval max bound")
    is_predicted_interval: bool = Field(default=False, description="True if baseline prediction is an interval")
    
    observed_value: Optional[float] = Field(default=None, description="Measured trial value")
    discrepancy_residual: Optional[float] = Field(default=None, description="Mathematical residual (Observed - Predicted)")
    unit: str = Field(..., description="Metric unit")
    
    comparison_status: ComparisonStatus = Field(..., description="MATCHED_WITHIN_INTERVAL, OUTSIDE_PREDICTION_INTERVAL, OBSERVED_ONLY, PREDICTION_ONLY, UNKNOWN")
    explanation: str = Field(..., description="Deterministic comparison text summary")


class ModelUpdateCandidateSchema(BaseModel):
    """Structured model update candidate representation."""

    id: str = Field(..., description="Model update candidate UUID")
    feedback_record_id: str = Field(..., description="Associated feedback record UUID")
    affected_component: str = Field(..., description="Affected pipeline component e.g. BARRIER_PHYSICS, SHELF_LIFE_ENGINE")
    affected_property: str = Field(..., description="Affected scientific property metric")
    
    prediction_value: Optional[float] = Field(default=None, description="Original prediction point value")
    prediction_min: Optional[float] = Field(default=None, description="Original prediction interval min")
    prediction_max: Optional[float] = Field(default=None, description="Original prediction interval max")
    observed_value: Optional[float] = Field(default=None, description="Observed trial measurement")
    discrepancy_residual: Optional[float] = Field(default=None, description="Discrepancy residual")
    units: str = Field(..., description="Metric units")
    
    interval_status: ComparisonStatus = Field(..., description="Comparison status classification")
    update_status: ModelUpdateStatus = Field(..., description="Governance review status: NOT_REVIEWED, REVIEW_REQUIRED, etc.")
    human_review_required: bool = Field(default=True, description="Always True for M12 candidate updates")
    discrepancy_evidence_summary: str = Field(..., description="Evidence summary of discrepancy for expert review")
    created_at: str = Field(..., description="ISO creation timestamp")


class FeedbackResponse(BaseModel):
    """Response payload returned for feedback submission or retrieval."""

    feedback_id: str = Field(..., description="Unique feedback record UUID")
    recommendation_run_id: Optional[str] = Field(default=None, description="Associated recommendation run ID")
    candidate_id: Optional[str] = Field(default=None, description="Associated candidate design ID")
    material_id: Optional[str] = Field(default=None, description="Associated M5 material ID")
    
    trial_identifier: str = Field(..., description="Trial identifier")
    observation_origin: ObservationOrigin = Field(..., description="Origin classification")
    observation_timestamp: str = Field(..., description="Observation ISO timestamp")
    
    validation_status: ValidationStatus = Field(..., description="VALID or INVALID")
    validation_message: Optional[str] = Field(default=None, description="Validation summary or error messages")
    
    comparisons: List[MeasurementComparison] = Field(default_factory=list, description="Predicted vs observed property comparisons")
    model_update_candidates: List[ModelUpdateCandidateSchema] = Field(default_factory=list, description="Generated model update candidate records")
    created_at: str = Field(..., description="ISO creation timestamp")
