"""
M12: Real-World Feedback & Model Update Candidate Database Models.

Stores observed packaging trial outcomes, predicted-vs-observed comparison results,
and structured model-update candidate records without automatically retraining models
or modifying frozen scientific equations.
"""

from sqlalchemy import Column, String, Float, Boolean, ForeignKey, DateTime, Enum, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime, timezone

from app.core.database import Base

# SQLAlchemy JSONB & UUID fallback for sqlite testing
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(UUID, 'sqlite')
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


# --- ENUMS ---

class ObservationOrigin(str, enum.Enum):
    REAL_PRODUCTION = "REAL_PRODUCTION"
    REAL_PILOT = "REAL_PILOT"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"
    DEMO = "DEMO"


class ValidationStatus(str, enum.Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING_REVIEW = "PENDING_REVIEW"


class ComparisonStatus(str, enum.Enum):
    MATCHED_WITHIN_INTERVAL = "MATCHED_WITHIN_INTERVAL"
    OUTSIDE_PREDICTION_INTERVAL = "OUTSIDE_PREDICTION_INTERVAL"
    OBSERVED_ONLY = "OBSERVED_ONLY"
    PREDICTION_ONLY = "PREDICTION_ONLY"
    UNKNOWN = "UNKNOWN"


class ModelUpdateStatus(str, enum.Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ACCEPTED_FOR_UPDATE = "ACCEPTED_FOR_UPDATE"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"


# --- MODELS ---

class PackagingFeedbackRecord(Base):
    """
    Database model for real-world packaging trial feedback records.
    Associates observations with recommendation runs, candidate designs, and materials.
    """
    __tablename__ = 'packaging_feedback_record'
    __table_args__ = (
        CheckConstraint("observed_shelf_life_days > 0 OR observed_shelf_life_days IS NULL", name="ck_pfr_shelf_life_pos"),
        CheckConstraint("observed_otr >= 0 OR observed_otr IS NULL", name="ck_pfr_otr_nonneg"),
        CheckConstraint("observed_co2tr >= 0 OR observed_co2tr IS NULL", name="ck_pfr_co2tr_nonneg"),
        CheckConstraint("observed_wvtr >= 0 OR observed_wvtr IS NULL", name="ck_pfr_wvtr_nonneg"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_run_id = Column(String, index=True, nullable=True)
    candidate_id = Column(String, index=True, nullable=True)
    material_id = Column(String, index=True, nullable=True)
    
    trial_identifier = Column(String, nullable=False, index=True)
    observation_origin = Column(Enum(ObservationOrigin, name="observationorigin"), nullable=False, index=True)
    observation_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    package_configuration = Column(JSONB, nullable=True)
    storage_conditions = Column(JSONB, nullable=True)
    
    observed_shelf_life_days = Column(Float, nullable=True)
    observed_otr = Column(Float, nullable=True)
    observed_co2tr = Column(Float, nullable=True)
    observed_wvtr = Column(Float, nullable=True)
    observed_product_condition = Column(String, nullable=True)
    
    predicted_outputs = Column(JSONB, nullable=True)
    comparison_summary = Column(JSONB, nullable=True)
    
    validation_status = Column(Enum(ValidationStatus, name="validationstatus"), nullable=False, default=ValidationStatus.VALID, index=True)
    validation_message = Column(String, nullable=True)
    evidence_source_metadata = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    model_update_candidates = relationship("ModelUpdateCandidate", back_populates="feedback_record", cascade="all, delete-orphan")


class ModelUpdateCandidate(Base):
    """
    Database model for structured model update candidate records.
    Captures prediction/observation discrepancies for human review and offline learning.
    """
    __tablename__ = 'model_update_candidate'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_record_id = Column(UUID(as_uuid=True), ForeignKey('packaging_feedback_record.id'), nullable=False, index=True)
    
    affected_component = Column(String, nullable=False, index=True) # e.g. BARRIER_PHYSICS, SHELF_LIFE_ENGINE
    affected_property = Column(String, nullable=False, index=True)  # e.g. WVTR, OTR, shelf_life_days
    
    prediction_value = Column(Float, nullable=True)
    prediction_min = Column(Float, nullable=True)
    prediction_max = Column(Float, nullable=True)
    observed_value = Column(Float, nullable=True)
    discrepancy_residual = Column(Float, nullable=True)
    units = Column(String, nullable=False)
    
    interval_status = Column(Enum(ComparisonStatus, name="comparisonstatus"), nullable=False, index=True)
    update_status = Column(Enum(ModelUpdateStatus, name="modelupdatestatus"), nullable=False, default=ModelUpdateStatus.REVIEW_REQUIRED, index=True)
    human_review_required = Column(Boolean, nullable=False, default=True)
    discrepancy_evidence_summary = Column(String, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    feedback_record = relationship("PackagingFeedbackRecord", back_populates="model_update_candidates")
