import pytest
from pathlib import Path
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

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


def test_scenario_dynamics_and_property_preservation(api_client, db_session: Session):
    """
    Phase 6 Test 1, 2, 3, 4:
    Verify that changing commodity, temperature, and RH updates the evaluation inputs,
    and user-provided properties are strictly preserved without being overwritten by UNKNOWN.
    """
    user_payload = {
        "commodity": "strawberry",
        "variety": "Camarosa",
        "product_form": "whole",
        "ripeness_stage": "ripe",
        "target_shelf_life_days": 10,
        "storage_type": "chilled",
        "storage_temperature_c": 2.0,
        "relative_humidity_percent": 95.0,
        "moisture_percent": 91.5,
        "fat_percent": 0.3,
        "ph": 3.8,
        "respiration_rate": 8.5,
        "package_surface_area_m2": 0.05,
        "package_headspace_volume_cm3": 250.0,
        "product_mass_kg": 0.25
    }
    resp = api_client.post("/api/v1/recommend", json=user_payload)
    assert resp.status_code == 200
    data = resp.json()

    # 1. User-supplied parameters reach backend
    req = data["request"]
    assert req["commodity"] == "strawberry"
    assert req["storage_temperature_c"] == 2.0
    assert req["relative_humidity_percent"] == 95.0

    # 2. Inferred properties preserve user-supplied values
    props = data["inference_profile"]["properties"]
    assert props["moisture_percent"]["value"] == 91.5
    assert props["moisture_percent"]["resolution_level"] == "user_supplied"
    assert props["fat_percent"]["value"] == 0.3
    assert props["fat_percent"]["resolution_level"] == "user_supplied"
    assert props["ph"]["value"] == 3.8
    assert props["ph"]["resolution_level"] == "user_supplied"
    assert props["respiration_rate"]["value"] == 8.5
    assert props["respiration_rate"]["resolution_level"] == "user_supplied"

    # 3. Environmental conditions reach requirement envelope
    req_env = data["requirement_envelope"]
    assert req_env["storage_temperature_c"] == 2.0
    assert req_env["relative_humidity_percent"] == 95.0


def test_candidate_counts_and_unknown_separation(api_client, db_session: Session):
    """
    Phase 6 Test 5, 8, 9, 10:
    Verify that candidate counts are mathematically exact,
    UNKNOWN candidates are never counted as feasible or infeasible,
    and only exact-physics verified candidates enter the Pareto front.
    """
    payload = {
        "commodity": "salmon",
        "product_form": "fillet",
        "ripeness_stage": "fresh",
        "target_shelf_life_days": 7,
        "storage_type": "chilled",
        "storage_temperature_c": 0.5,
        "relative_humidity_percent": 98.0
    }
    resp = api_client.post("/api/v1/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    total = data["total_candidates_evaluated"]
    feasible = data["feasible_candidates_count"]
    infeasible = data["infeasible_candidates_count"]
    unknown = data["unknown_candidates_count"]

    # Candidate count conservation law
    assert feasible + infeasible + unknown == total
    assert total > 0

    # Unknown candidates must not be counted as feasible or infeasible
    assert unknown >= 0
    if feasible == 0 and infeasible == 0:
        assert unknown == total

    # Only feasible candidates enter Pareto front
    pareto_candidates = data["pareto_front"]["candidates"]
    assert len(pareto_candidates) == data["pareto_front"]["candidate_count"]
    assert len(pareto_candidates) == feasible


def test_material_candidates_sourced_from_actual_db(api_client, db_session: Session):
    """
    Phase 6 Test 6:
    Verify material candidates are retrieved from the actual material database,
    and all candidate summaries contain database-backed material names and IDs.
    """
    payload = {
        "commodity": "apple",
        "product_form": "whole",
        "ripeness_stage": "ripe",
        "target_shelf_life_days": 30,
        "storage_type": "chilled"
    }
    resp = api_client.post("/api/v1/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    summaries = data["candidate_summaries"]
    assert len(summaries) == data["total_candidates_evaluated"]
    assert len(summaries) >= 5

    material_names = [s["material_name"] for s in summaries]
    # Check diverse materials from the actual M5 packaging material database
    assert any("LDPE" in name for name in material_names)
    assert any("HDPE" in name for name in material_names)
    assert any("BOPP" in name for name in material_names)
    assert any("EVOH" in name or "PET" in name for name in material_names)

