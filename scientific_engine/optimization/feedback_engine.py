"""
M12: Feedback Processing & Model Update Candidate Generation Engine.

Provides deterministic validation, predicted vs. observed property comparison,
interval containment analysis, and model-update candidate creation without
modifying frozen scientific equations or executing automatic retraining.
"""

from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timezone
import uuid

from app.models.feedback import (
    PackagingFeedbackRecord,
    ModelUpdateCandidate,
    ObservationOrigin,
    ValidationStatus,
    ComparisonStatus,
    ModelUpdateStatus
)
from app.schemas.feedback import (
    FeedbackSubmission,
    PredictedOutputSchema,
    MeasurementComparison,
    ModelUpdateCandidateSchema,
    FeedbackResponse
)


class FeedbackEngine:
    """
    Deterministic feedback engine for validating packaging trial observations,
    evaluating predicted-vs-observed discrepancies, and generating traceable
    model-update candidates.
    """

    def validate_submission(self, submission: FeedbackSubmission) -> Tuple[ValidationStatus, Optional[str]]:
        """
        Deterministically validate incoming feedback submission.
        Checks required fields, unit sanity, numeric boundaries, and origin classifications.
        """
        errors: List[str] = []

        if not submission.trial_identifier or not submission.trial_identifier.strip():
            errors.append("Missing required field: trial_identifier.")

        if not isinstance(submission.observation_origin, ObservationOrigin):
            try:
                submission.observation_origin = ObservationOrigin(submission.observation_origin)
            except ValueError:
                errors.append(f"Invalid observation_origin value: {submission.observation_origin}.")

        # Check numeric non-negativity and physical sanity boundaries
        if submission.observed_shelf_life_days is not None:
            if submission.observed_shelf_life_days <= 0:
                errors.append(f"Invalid observed_shelf_life_days: {submission.observed_shelf_life_days}. Must be strictly positive (> 0).")

        if submission.observed_otr is not None:
            if submission.observed_otr < 0:
                errors.append(f"Invalid observed_otr: {submission.observed_otr}. Cannot be negative.")

        if submission.observed_co2tr is not None:
            if submission.observed_co2tr < 0:
                errors.append(f"Invalid observed_co2tr: {submission.observed_co2tr}. Cannot be negative.")

        if submission.observed_wvtr is not None:
            if submission.observed_wvtr < 0:
                errors.append(f"Invalid observed_wvtr: {submission.observed_wvtr}. Cannot be negative.")

        if submission.storage_conditions:
            conds = submission.storage_conditions
            if conds.temperature_c is not None and (conds.temperature_c < -50.0 or conds.temperature_c > 100.0):
                errors.append(f"Physically impossible storage temperature: {conds.temperature_c} °C.")
            if conds.rh_percent is not None and (conds.rh_percent < 0.0 or conds.rh_percent > 100.0):
                errors.append(f"Invalid relative humidity percentage: {conds.rh_percent} %.")
            if conds.duration_days is not None and conds.duration_days < 0.0:
                errors.append(f"Invalid trial duration: {conds.duration_days} days.")

        if errors:
            return ValidationStatus.INVALID, " Validation errors: " + " | ".join(errors)

        return ValidationStatus.VALID, "Submission passed deterministic feedback validation."

    def compare_predicted_vs_observed(
        self,
        submission: FeedbackSubmission,
        predicted: Optional[PredictedOutputSchema] = None
    ) -> List[MeasurementComparison]:
        """
        Deterministic comparison layer for observed vs predicted properties.
        Preserves interval boundaries without midpoint collapse.
        Preserves missingness semantics (UNKNOWN).
        """
        comparisons: List[MeasurementComparison] = []

        if predicted is None:
            predicted = submission.predicted_outputs_override or PredictedOutputSchema()

        # Metrics to compare
        metrics = [
            ("shelf_life_days", submission.observed_shelf_life_days, predicted.shelf_life_days, predicted.shelf_life_min, predicted.shelf_life_max, "days"),
            ("OTR", submission.observed_otr, predicted.otr, predicted.otr_min, predicted.otr_max, "cm3/(m2*day*atm)"),
            ("CO2TR", submission.observed_co2tr, predicted.co2tr, predicted.co2tr_min, predicted.co2tr_max, "cm3/(m2*day*atm)"),
            ("WVTR", submission.observed_wvtr, predicted.wvtr, predicted.wvtr_min, predicted.wvtr_max, "g/(m2*day)"),
        ]

        for name, obs, pred_val, pred_min, pred_max, unit in metrics:
            is_interval = (pred_min is not None and pred_max is not None)
            
            if obs is not None and (pred_val is not None or is_interval):
                if is_interval:
                    if pred_min <= obs <= pred_max:
                        status = ComparisonStatus.MATCHED_WITHIN_INTERVAL
                        residual = 0.0
                        exp = f"Observed {name} ({obs} {unit}) falls within predicted interval [{pred_min}, {pred_max}] {unit}."
                    else:
                        status = ComparisonStatus.OUTSIDE_PREDICTION_INTERVAL
                        residual = obs - pred_max if obs > pred_max else obs - pred_min
                        exp = f"Observed {name} ({obs} {unit}) falls OUTSIDE predicted interval [{pred_min}, {pred_max}] {unit} (residual: {residual:+.4f} {unit})."
                else:
                    # Point prediction
                    residual = obs - pred_val
                    # Consider matched if relative difference <= 1% or absolute <= 0.01
                    abs_tol = max(0.01, 0.01 * abs(pred_val))
                    if abs(residual) <= abs_tol:
                        status = ComparisonStatus.MATCHED_WITHIN_INTERVAL
                        exp = f"Observed {name} ({obs} {unit}) matches predicted value ({pred_val} {unit}) within tolerance."
                    else:
                        status = ComparisonStatus.OUTSIDE_PREDICTION_INTERVAL
                        exp = f"Observed {name} ({obs} {unit}) differs from predicted value ({pred_val} {unit}) by residual {residual:+.4f} {unit}."

                comparisons.append(MeasurementComparison(
                    property_name=name,
                    predicted_value=pred_val,
                    predicted_min=pred_min,
                    predicted_max=pred_max,
                    is_predicted_interval=is_interval,
                    observed_value=obs,
                    discrepancy_residual=residual,
                    unit=unit,
                    comparison_status=status,
                    explanation=exp
                ))
            elif obs is not None and pred_val is None and not is_interval:
                comparisons.append(MeasurementComparison(
                    property_name=name,
                    predicted_value=None,
                    predicted_min=None,
                    predicted_max=None,
                    is_predicted_interval=False,
                    observed_value=obs,
                    discrepancy_residual=None,
                    unit=unit,
                    comparison_status=ComparisonStatus.OBSERVED_ONLY,
                    explanation=f"Observed {name} ({obs} {unit}) recorded; no baseline prediction was available."
                ))
            elif obs is None and (pred_val is not None or is_interval):
                comparisons.append(MeasurementComparison(
                    property_name=name,
                    predicted_value=pred_val,
                    predicted_min=pred_min,
                    predicted_max=pred_max,
                    is_predicted_interval=is_interval,
                    observed_value=None,
                    discrepancy_residual=None,
                    unit=unit,
                    comparison_status=ComparisonStatus.PREDICTION_ONLY,
                    explanation=f"Predicted {name} available; no trial observation was submitted."
                ))
            else:
                comparisons.append(MeasurementComparison(
                    property_name=name,
                    predicted_value=None,
                    predicted_min=None,
                    predicted_max=None,
                    is_predicted_interval=False,
                    observed_value=None,
                    discrepancy_residual=None,
                    unit=unit,
                    comparison_status=ComparisonStatus.UNKNOWN,
                    explanation=f"Both prediction and observation for {name} are UNKNOWN/missing."
                ))

        return comparisons

    def generate_model_update_candidates(
        self,
        feedback_record_id: uuid.UUID,
        origin: ObservationOrigin,
        comparisons: List[MeasurementComparison]
    ) -> List[ModelUpdateCandidate]:
        """
        Generate traceable ModelUpdateCandidate objects for expert review.
        Does NOT execute automatic model retraining or equation mutation.
        """
        candidates: List[ModelUpdateCandidate] = []

        component_map = {
            "shelf_life_days": "SHELF_LIFE_ENGINE",
            "OTR": "GAS_EXCHANGE_ENGINE",
            "CO2TR": "GAS_EXCHANGE_ENGINE",
            "WVTR": "MOISTURE_ENGINE"
        }

        synthetic_warning = ""
        if origin in (ObservationOrigin.SYNTHETIC_TEST, ObservationOrigin.DEMO):
            synthetic_warning = f" [NOTICE: Origin is {origin.value}; MUST NOT be used for production retraining.]"

        for comp in comparisons:
            if comp.comparison_status == ComparisonStatus.OUTSIDE_PREDICTION_INTERVAL:
                affected = component_map.get(comp.property_name, "BARRIER_PHYSICS")
                
                summary = (
                    f"Discrepancy detected in {comp.property_name} for trial feedback {feedback_record_id}. "
                    f"Observed: {comp.observed_value} {comp.unit}, Predicted: {comp.predicted_value or f'[{comp.predicted_min}, {comp.predicted_max}]'} {comp.unit}. "
                    f"Residual: {comp.discrepancy_residual:+.4f} {comp.unit}. Requires expert scientific review.{synthetic_warning}"
                )

                candidates.append(ModelUpdateCandidate(
                    id=uuid.uuid4(),
                    feedback_record_id=feedback_record_id,
                    affected_component=affected,
                    affected_property=comp.property_name,
                    prediction_value=comp.predicted_value,
                    prediction_min=comp.predicted_min,
                    prediction_max=comp.predicted_max,
                    observed_value=comp.observed_value,
                    discrepancy_residual=comp.discrepancy_residual,
                    units=comp.unit,
                    interval_status=comp.comparison_status,
                    update_status=ModelUpdateStatus.REVIEW_REQUIRED,
                    human_review_required=True,
                    discrepancy_evidence_summary=summary,
                    created_at=datetime.now(timezone.utc)
                ))

        return candidates
