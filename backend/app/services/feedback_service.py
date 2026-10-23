"""
M12: Feedback Service.

Orchestrates real-world trial feedback submission, predicted-vs-observed evaluation,
database persistence, and model update candidate creation.
"""

from typing import List, Optional
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

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
from scientific_engine.optimization.feedback_engine import FeedbackEngine


class FeedbackService:
    """Service layer for feedback ingestion, evaluation, and DB persistence."""

    def __init__(self):
        self.engine = FeedbackEngine()

    def submit_feedback(self, submission: FeedbackSubmission, db: Session) -> FeedbackResponse:
        """
        Validate, compare, persist, and return feedback record with model-update candidates.
        """
        # 1. Validate submission
        val_status, val_msg = self.engine.validate_submission(submission)

        # 2. Perform predicted vs observed comparisons
        comparisons = self.engine.compare_predicted_vs_observed(submission)

        feedback_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Prepare JSON fields
        pkg_config = submission.package_configuration.model_dump() if submission.package_configuration else None
        storage_cond = submission.storage_conditions.model_dump() if submission.storage_conditions else None
        pred_outputs = (submission.predicted_outputs_override.model_dump() if submission.predicted_outputs_override else None)
        comp_summary = [c.model_dump() for c in comparisons]

        # Sanitize numeric fields for DB column check constraints if validation failed
        db_shelf_life = submission.observed_shelf_life_days if (submission.observed_shelf_life_days is not None and submission.observed_shelf_life_days > 0) else None
        db_otr = submission.observed_otr if (submission.observed_otr is not None and submission.observed_otr >= 0) else None
        db_co2tr = submission.observed_co2tr if (submission.observed_co2tr is not None and submission.observed_co2tr >= 0) else None
        db_wvtr = submission.observed_wvtr if (submission.observed_wvtr is not None and submission.observed_wvtr >= 0) else None

        # 3. Create PackagingFeedbackRecord DB model
        feedback_record = PackagingFeedbackRecord(
            id=feedback_id,
            recommendation_run_id=submission.recommendation_run_id,
            candidate_id=submission.candidate_id,
            material_id=submission.material_id,
            trial_identifier=submission.trial_identifier if submission.trial_identifier else f"TRIAL-INVALID-{feedback_id.hex[:6]}",
            observation_origin=submission.observation_origin,
            observation_timestamp=now,
            package_configuration=pkg_config,
            storage_conditions=storage_cond,
            observed_shelf_life_days=db_shelf_life,
            observed_otr=db_otr,
            observed_co2tr=db_co2tr,
            observed_wvtr=db_wvtr,
            observed_product_condition=submission.observed_product_condition,
            predicted_outputs=pred_outputs,
            comparison_summary=comp_summary,
            validation_status=val_status,
            validation_message=val_msg,
            evidence_source_metadata=submission.evidence_source_metadata,
            created_at=now
        )

        db.add(feedback_record)
        db.flush()

        # 4. Generate ModelUpdateCandidate objects if VALID and discrepancies exist
        db_candidates: List[ModelUpdateCandidate] = []
        if val_status == ValidationStatus.VALID:
            db_candidates = self.engine.generate_model_update_candidates(
                feedback_record_id=feedback_id,
                origin=submission.observation_origin,
                comparisons=comparisons
            )
            for cand in db_candidates:
                db.add(cand)

        db.commit()
        db.refresh(feedback_record)

        # 5. Build response schemas
        update_candidate_schemas = [
            ModelUpdateCandidateSchema(
                id=str(cand.id),
                feedback_record_id=str(cand.feedback_record_id),
                affected_component=cand.affected_component,
                affected_property=cand.affected_property,
                prediction_value=cand.prediction_value,
                prediction_min=cand.prediction_min,
                prediction_max=cand.prediction_max,
                observed_value=cand.observed_value,
                discrepancy_residual=cand.discrepancy_residual,
                units=cand.units,
                interval_status=cand.interval_status,
                update_status=cand.update_status,
                human_review_required=cand.human_review_required,
                discrepancy_evidence_summary=cand.discrepancy_evidence_summary,
                created_at=cand.created_at.isoformat() if cand.created_at else now.isoformat()
            )
            for cand in db_candidates
        ]

        return FeedbackResponse(
            feedback_id=str(feedback_id),
            recommendation_run_id=submission.recommendation_run_id,
            candidate_id=submission.candidate_id,
            material_id=submission.material_id,
            trial_identifier=submission.trial_identifier,
            observation_origin=submission.observation_origin,
            observation_timestamp=now.isoformat(),
            validation_status=val_status,
            validation_message=val_msg,
            comparisons=comparisons,
            model_update_candidates=update_candidate_schemas,
            created_at=now.isoformat()
        )

    def get_feedback_by_id(self, feedback_id: str, db: Session) -> Optional[FeedbackResponse]:
        """
        Retrieve feedback record by UUID.
        """
        try:
            fb_uuid = uuid.UUID(feedback_id)
        except ValueError:
            return None

        record = db.query(PackagingFeedbackRecord).filter_by(id=fb_uuid).first()
        if not record:
            return None

        comparisons = []
        if record.comparison_summary:
            comparisons = [MeasurementComparison(**c) for c in record.comparison_summary]

        update_candidate_schemas = [
            ModelUpdateCandidateSchema(
                id=str(cand.id),
                feedback_record_id=str(cand.feedback_record_id),
                affected_component=cand.affected_component,
                affected_property=cand.affected_property,
                prediction_value=cand.prediction_value,
                prediction_min=cand.prediction_min,
                prediction_max=cand.prediction_max,
                observed_value=cand.observed_value,
                discrepancy_residual=cand.discrepancy_residual,
                units=cand.units,
                interval_status=cand.interval_status,
                update_status=cand.update_status,
                human_review_required=cand.human_review_required,
                discrepancy_evidence_summary=cand.discrepancy_evidence_summary,
                created_at=cand.created_at.isoformat() if cand.created_at else ""
            )
            for cand in record.model_update_candidates
        ]

        return FeedbackResponse(
            feedback_id=str(record.id),
            recommendation_run_id=record.recommendation_run_id,
            candidate_id=record.candidate_id,
            material_id=record.material_id,
            trial_identifier=record.trial_identifier,
            observation_origin=record.observation_origin,
            observation_timestamp=record.observation_timestamp.isoformat() if record.observation_timestamp else "",
            validation_status=record.validation_status,
            validation_message=record.validation_message,
            comparisons=comparisons,
            model_update_candidates=update_candidate_schemas,
            created_at=record.created_at.isoformat() if record.created_at else ""
        )

    def list_model_update_candidates(self, db: Session) -> List[ModelUpdateCandidateSchema]:
        """
        List all recorded model update candidates across trials.
        """
        records = db.query(ModelUpdateCandidate).all()
        return [
            ModelUpdateCandidateSchema(
                id=str(cand.id),
                feedback_record_id=str(cand.feedback_record_id),
                affected_component=cand.affected_component,
                affected_property=cand.affected_property,
                prediction_value=cand.prediction_value,
                prediction_min=cand.prediction_min,
                prediction_max=cand.prediction_max,
                observed_value=cand.observed_value,
                discrepancy_residual=cand.discrepancy_residual,
                units=cand.units,
                interval_status=cand.interval_status,
                update_status=cand.update_status,
                human_review_required=cand.human_review_required,
                discrepancy_evidence_summary=cand.discrepancy_evidence_summary,
                created_at=cand.created_at.isoformat() if cand.created_at else ""
            )
            for cand in records
        ]
