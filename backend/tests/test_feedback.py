"""
M12: Real-World Feedback & Model Update Candidate Test Suite.

Verifies:
1. Valid feedback submission
2. Invalid feedback rejection
3. Candidate association
4. Recommendation association
5. Predicted-vs-observed comparison
6. Interval containment
7. Outside-interval observation
8. Missing observation handling
9. Prediction-only state handling
10. Repeated trial tracking
11. Conflicting observation preservation
12. Provenance preservation
13. Synthetic/demo origin distinction
14. Model-update candidate creation
15. Review-required state
16. Guarantee of no automatic model modification
17. Database persistence
18. API integration (POST /api/v1/feedback & GET /api/v1/feedback/{id})
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.core.database import Base, get_db
from app.main import app
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
    PackageConfigurationSchema,
    StorageConditionsSchema
)
from app.services.feedback_service import FeedbackService
from scientific_engine.optimization.feedback_engine import FeedbackEngine


@pytest.fixture
def db_session():
    """In-memory SQLite database session fixture."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(db_session):
    """TestClient with get_db overridden to use the in-memory SQLite session."""
    def _override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


def test_valid_feedback_submission(db_session: Session):
    """Test 1: Valid feedback submission is processed and stored correctly."""
    service = FeedbackService()
    submission = FeedbackSubmission(
        recommendation_run_id="run-123456",
        candidate_id="cand-001",
        material_id="mat-ldpe",
        trial_identifier="TRIAL-2026-A1",
        observation_origin=ObservationOrigin.REAL_PRODUCTION,
        observed_shelf_life_days=22.0,
        observed_wvtr=1.2,
        predicted_outputs_override=PredictedOutputSchema(
            shelf_life_min=20.0,
            shelf_life_max=25.0,
            wvtr=1.2
        )
    )

    response = service.submit_feedback(submission, db_session)
    assert response.validation_status == ValidationStatus.VALID
    assert response.trial_identifier == "TRIAL-2026-A1"
    assert len(response.comparisons) > 0


def test_invalid_feedback_rejection(db_session: Session):
    """Test 2: Invalid feedback (e.g. negative shelf life or empty trial ID) is rejected."""
    service = FeedbackService()
    submission = FeedbackSubmission(
        trial_identifier="", # Invalid empty string
        observation_origin=ObservationOrigin.REAL_PILOT,
        observed_shelf_life_days=-5.0 # Invalid negative shelf life
    )

    response = service.submit_feedback(submission, db_session)
    assert response.validation_status == ValidationStatus.INVALID
    assert "trial_identifier" in response.validation_message
    assert "observed_shelf_life_days" in response.validation_message


def test_candidate_and_recommendation_association(db_session: Session):
    """Test 3 & 4: Recommendation ID and candidate ID are properly associated."""
    service = FeedbackService()
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    cand_id = "cand-poly-40"
    mat_id = "mat-pet"

    submission = FeedbackSubmission(
        recommendation_run_id=run_id,
        candidate_id=cand_id,
        material_id=mat_id,
        trial_identifier="TRIAL-ASSOC-01",
        observation_origin=ObservationOrigin.REAL_PILOT,
        observed_shelf_life_days=15.0
    )

    response = service.submit_feedback(submission, db_session)
    assert response.recommendation_run_id == run_id
    assert response.candidate_id == cand_id
    assert response.material_id == mat_id

    rec = db_session.query(PackagingFeedbackRecord).filter_by(trial_identifier="TRIAL-ASSOC-01").first()
    assert rec is not None
    assert rec.recommendation_run_id == run_id
    assert rec.candidate_id == cand_id


def test_predicted_vs_observed_interval_containment(db_session: Session):
    """Test 5 & 6: Predicted interval containment (MATCHED_WITHIN_INTERVAL)."""
    engine = FeedbackEngine()
    submission = FeedbackSubmission(
        trial_identifier="TRIAL-INT-01",
        observation_origin=ObservationOrigin.REAL_PRODUCTION,
        observed_shelf_life_days=23.0,
        predicted_outputs_override=PredictedOutputSchema(
            shelf_life_min=20.0,
            shelf_life_max=25.0
        )
    )

    comparisons = engine.compare_predicted_vs_observed(submission)
    shelf_comp = next(c for c in comparisons if c.property_name == "shelf_life_days")
    assert shelf_comp.comparison_status == ComparisonStatus.MATCHED_WITHIN_INTERVAL
    assert shelf_comp.discrepancy_residual == 0.0
    assert shelf_comp.is_predicted_interval is True


def test_outside_prediction_interval_observation(db_session: Session):
    """Test 7: Observation outside predicted interval (OUTSIDE_PREDICTION_INTERVAL)."""
    engine = FeedbackEngine()
    submission = FeedbackSubmission(
        trial_identifier="TRIAL-OUT-01",
        observation_origin=ObservationOrigin.REAL_PRODUCTION,
        observed_shelf_life_days=30.0, # Outside [20, 25]
        predicted_outputs_override=PredictedOutputSchema(
            shelf_life_min=20.0,
            shelf_life_max=25.0
        )
    )

    comparisons = engine.compare_predicted_vs_observed(submission)
    shelf_comp = next(c for c in comparisons if c.property_name == "shelf_life_days")
    assert shelf_comp.comparison_status == ComparisonStatus.OUTSIDE_PREDICTION_INTERVAL
    assert shelf_comp.discrepancy_residual == 5.0 # 30 - 25


def test_missing_observation_preservation(db_session: Session):
    """Test 8 & 9: Missing observations and prediction-only states are preserved as UNKNOWN or PREDICTION_ONLY."""
    engine = FeedbackEngine()
    submission = FeedbackSubmission(
        trial_identifier="TRIAL-MISSING-01",
        observation_origin=ObservationOrigin.REAL_PRODUCTION,
        observed_shelf_life_days=None, # Missing observation
        observed_wvtr=1.5,
        predicted_outputs_override=PredictedOutputSchema(
            shelf_life_days=20.0,
            wvtr=None # Missing prediction
        )
    )

    comparisons = engine.compare_predicted_vs_observed(submission)
    shelf_comp = next(c for c in comparisons if c.property_name == "shelf_life_days")
    wvtr_comp = next(c for c in comparisons if c.property_name == "WVTR")
    otr_comp = next(c for c in comparisons if c.property_name == "OTR")

    assert shelf_comp.comparison_status == ComparisonStatus.PREDICTION_ONLY
    assert wvtr_comp.comparison_status == ComparisonStatus.OBSERVED_ONLY
    assert otr_comp.comparison_status == ComparisonStatus.UNKNOWN


def test_repeated_and_conflicting_observations(db_session: Session):
    """Test 10 & 11: Repeated trials for the same candidate do not overwrite past observations."""
    service = FeedbackService()
    cand_id = "cand-repeated-01"

    sub1 = FeedbackSubmission(
        candidate_id=cand_id,
        trial_identifier="TRIAL-REP-01",
        observation_origin=ObservationOrigin.REAL_PILOT,
        observed_shelf_life_days=18.0
    )
    sub2 = FeedbackSubmission(
        candidate_id=cand_id,
        trial_identifier="TRIAL-REP-02",
        observation_origin=ObservationOrigin.REAL_PRODUCTION,
        observed_shelf_life_days=25.0 # Conflicting observation
    )

    resp1 = service.submit_feedback(sub1, db_session)
    resp2 = service.submit_feedback(sub2, db_session)

    records = db_session.query(PackagingFeedbackRecord).filter_by(candidate_id=cand_id).all()
    assert len(records) == 2
    shelf_lives = {r.observed_shelf_life_days for r in records}
    assert shelf_lives == {18.0, 25.0}


def test_synthetic_and_demo_origin_distinction(db_session: Session):
    """Test 12, 13 & 14: Synthetic/Demo origins are clearly labeled and update candidate summaries note non-production status."""
    service = FeedbackService()
    submission = FeedbackSubmission(
        trial_identifier="TRIAL-SYNTHETIC-99",
        observation_origin=ObservationOrigin.SYNTHETIC_TEST,
        observed_wvtr=5.0, # Outside interval
        predicted_outputs_override=PredictedOutputSchema(
            wvtr=1.0
        )
    )

    response = service.submit_feedback(submission, db_session)
    assert response.observation_origin == ObservationOrigin.SYNTHETIC_TEST
    assert len(response.model_update_candidates) > 0
    c_update = response.model_update_candidates[0]
    assert "SYNTHETIC_TEST" in c_update.discrepancy_evidence_summary
    assert "MUST NOT be used for production retraining" in c_update.discrepancy_evidence_summary


def test_model_update_candidate_review_required(db_session: Session):
    """Test 15 & 16: Model update candidate is created with REVIEW_REQUIRED and human_review_required=True."""
    service = FeedbackService()
    submission = FeedbackSubmission(
        trial_identifier="TRIAL-REV-01",
        observation_origin=ObservationOrigin.REAL_PRODUCTION,
        observed_otr=150.0, # Discrepancy
        predicted_outputs_override=PredictedOutputSchema(
            otr=50.0
        )
    )

    response = service.submit_feedback(submission, db_session)
    assert len(response.model_update_candidates) > 0
    cand = response.model_update_candidates[0]
    assert cand.update_status == ModelUpdateStatus.REVIEW_REQUIRED
    assert cand.human_review_required is True
    assert cand.affected_component == "GAS_EXCHANGE_ENGINE"


def test_api_feedback_endpoints(api_client):
    """Test 18: REST API endpoints for submitting and retrieving feedback records."""
    payload = {
        "trial_identifier": "API-TRIAL-01",
        "observation_origin": "REAL_PRODUCTION",
        "observed_shelf_life_days": 21.0,
        "predicted_outputs_override": {
            "shelf_life_min": 18.0,
            "shelf_life_max": 24.0
        }
    }

    response = api_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 201, f"Response: {response.json()}"
    data = response.json()
    assert data["trial_identifier"] == "API-TRIAL-01"
    assert data["validation_status"] == "VALID"
    feedback_id = data["feedback_id"]

    get_resp = api_client.get(f"/api/v1/feedback/{feedback_id}")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["feedback_id"] == feedback_id

    updates_resp = api_client.get("/api/v1/feedback/model-updates")
    assert updates_resp.status_code == 200
    assert isinstance(updates_resp.json(), list)
