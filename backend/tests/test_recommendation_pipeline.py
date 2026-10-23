import pytest
import httpx
from pathlib import Path
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import Base, get_db
from app.schemas.packaging_request import PackagingRequest
from app.services.recommendation_service import RecommendationService
from app.schemas.constraints import ConstraintStatus
from app.ingestion.pipeline import DataIngestionPipeline

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BASE_DIR = str(_PROJECT_ROOT / "data" / "processed")
_REFERENCE_DIR = str(_PROJECT_ROOT / "data" / "reference")


@pytest.fixture(scope="module")
def db_session():
    """Isolated in-memory SQLite session; no live PostgreSQL connection required."""
    _eng = _create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(_eng)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_eng)
    session = TestSession()
    pipeline = DataIngestionPipeline(session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()
    yield session
    session.close()
    Base.metadata.drop_all(_eng)
    _eng.dispose()


@pytest.fixture(scope="module")
def api_client(db_session):
    """TestClient with get_db overridden to use the in-memory SQLite session."""
    def _override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


def test_service_end_to_end_flow(db_session: Session):
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled",
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        package_surface_area_m2=0.06,
        package_headspace_volume_cm3=500.0,
        product_mass_kg=0.5
    )

    service = RecommendationService()
    res = service.generate_recommendation(req, db_session)

    # 1. Valid request reaches pipeline
    assert res.request.commodity == "apple"
    assert res.request.target_shelf_life_days == 14

    # 2. Property inference invoked
    assert res.inference_profile.commodity == "apple"
    assert res.inference_profile.overall_confidence > 0.0

    # 3. Phase 4 requirements generated
    assert res.requirement_envelope is not None
    assert res.requirement_envelope.target_shelf_life_days == 14

    # 4. Phase 5 constraints & candidate evaluation
    assert res.total_candidates_evaluated > 0
    assert len(res.candidate_summaries) == res.total_candidates_evaluated

    # 5. Objectives & Pareto front constructed
    assert res.pareto_front is not None
    assert res.pareto_front.solver_metadata.algorithm_name in ["DETERMINISTIC_EXHAUSTIVE_ENUMERATION_BASELINE", "M8_EXACT_PARETO_PIPELINE"]

    # 6. Check status counts match
    assert res.feasible_candidates_count + res.infeasible_candidates_count + res.unknown_candidates_count == res.total_candidates_evaluated


def test_unknown_not_converted_to_feasible(db_session: Session):
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled",
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0
    )

    service = RecommendationService()
    res = service.generate_recommendation(req, db_session)

    # Candidates marked UNKNOWN must NOT be in the feasible Pareto front
    unknown_summaries = [c for c in res.candidate_summaries if c.constraint_status == ConstraintStatus.UNKNOWN.value]
    pareto_cand_ids = {c.pareto_candidate_id for c in res.pareto_front.candidates}

    for unk in unknown_summaries:
        assert unk.candidate_id not in pareto_cand_ids


def test_interval_values_remain_intervals(db_session: Session):
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled",
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0
    )

    service = RecommendationService()
    res = service.generate_recommendation(req, db_session)

    # Check objective values across pareto candidates preserve interval metadata
    for p_cand in res.pareto_front.candidates:
        for obj_name, obj_val in p_cand.objective_values.items():
            assert hasattr(obj_val, "is_interval")
            assert hasattr(obj_val, "value_min")
            assert hasattr(obj_val, "value_max")


def test_api_recommendation_endpoint(api_client, db_session: Session):
    """FastAPI POST /api/v1/recommend endpoint integration."""
    payload = {
        "commodity": "apple",
        "product_form": "fresh",
        "ripeness_stage": "mature",
        "target_shelf_life_days": 14,
        "storage_type": "chilled",
        "storage_temperature_c": 4.0,
        "relative_humidity_percent": 90.0,
        "package_surface_area_m2": 0.06,
        "package_headspace_volume_cm3": 500.0,
        "product_mass_kg": 0.5
    }
    response = api_client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["recommendation_run_id"].startswith("run-")
    assert data["request"]["commodity"] == "apple"
    assert "pareto_front" in data
    assert "total_candidates_evaluated" in data
    assert data["total_candidates_evaluated"] > 0
