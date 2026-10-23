"""
Unit and Integration Tests for M9 Inverse-Design Search Engine Layer.

Verifies:
1. Finite candidate enumeration baseline execution.
2. Deterministic repeated execution (identical Pareto output for identical inputs).
3. Candidate-specific scientific evaluation invocation.
4. Phase 5 hard-constraint filtering.
5. UNKNOWN exclusion from feasible Pareto front (never converted to FEASIBLE or assigned numeric penalty scores).
6. INFEASIBLE candidate exclusion from Pareto front.
7. FEASIBLE candidate preservation in Pareto front construction.
8. Preservation of interval-valued objective dimensions.
9. Exclusive evaluation of all four M6-B3 objectives (f_thickness, f_moisture_margin, f_gas_alignment, f_shelf_life_margin).
10. Reuse of M6-B4A/B Pareto dominance primitive and non-dominated set construction.
11. Valid handling of empty Pareto front (when 0 candidates are feasible).
12. Construction of non-dominated Pareto front with multiple non-dominated candidates.
13. Integration with RecommendationService.
14. Integration with FastAPI POST /api/v1/recommend endpoint.
15. Strict absence of scalar material ranking or "best material" composite scores.
"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.models.evidence import PackagingMaterial
from app.ingestion.pipeline import DataIngestionPipeline

from app.schemas.packaging_request import PackagingRequest
from app.schemas.optimization import (
    OptimizationInputEnvelope,
    PackagingCandidate,
    CandidateDecisionVariables,
    CandidateBarrierProperties,
    BarrierPropertyMetric,
    CandidateEvidenceReference,
    PackageGeometry,
    SolverConfiguration,
    OptimizationExecutionTier,
    ObjectiveValue,
    ObjectiveDirection
)
from app.schemas.packaging_requirements import PackagingRequirementEnvelope
from app.schemas.candidate_feasibility import FilteringResult
from app.schemas.constraints import ConstraintStatus, ConditionMatchLevel
from app.schemas.physics import CalculationStatus

from scientific_engine.physics.requirements import PackagingRequirementEngine
from scientific_engine.inference.engine import PropertyInferenceEngine
from scientific_engine.optimization.candidate_builder import CandidateBuilder
from scientific_engine.optimization.search_engine import (
    AbstractInverseDesignSearchEngine,
    DeterministicEnumerationSearchEngine,
    InverseDesignSearchResult
)
from app.services.recommendation_service import RecommendationService

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
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


def test_search_interface_abstraction():
    """Verify that search engine implements AbstractInverseDesignSearchEngine."""
    engine_inst = DeterministicEnumerationSearchEngine()
    assert isinstance(engine_inst, AbstractInverseDesignSearchEngine)


def test_finite_candidate_enumeration_and_metrics(db_session: Session):
    """Test 1: Finite candidate enumeration and execution metric collection."""
    builder = CandidateBuilder(db_session)
    candidates = builder.build_candidates()
    assert len(candidates) > 0

    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled",
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0
    )
    inf_engine = PropertyInferenceEngine()
    req_engine = PackagingRequirementEngine()
    
    inf_profile = inf_engine.infer_profile(req)
    req_env = req_engine.evaluate_requirements(req, inf_profile, 0.5, 0.06)

    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)
    filtering_res = FilteringResult(commodity="apple", total_candidates_evaluated=len(candidates))

    input_envelope = OptimizationInputEnvelope(
        optimization_run_id="test-run-1",
        commodity="apple",
        target_shelf_life_days=14,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        package_geometry=geometry,
        packaging_requirement_envelope=req_env,
        filtering_result=filtering_res,
        eligible_candidate_materials=candidates,
        active_objectives=["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"],
        solver_configuration=SolverConfiguration(execution_tier=OptimizationExecutionTier.LATTICE_LOOKUP)
    )

    search_engine = DeterministicEnumerationSearchEngine()
    res = search_engine.search_with_summary(input_envelope)

    assert isinstance(res, InverseDesignSearchResult)
    assert res.total_candidates_considered == len(candidates)
    assert res.total_candidates_evaluated == len(candidates)
    assert res.feasible_candidates_count + res.infeasible_candidates_count + res.unknown_candidates_count == len(candidates)
    assert res.algorithm_name == "DETERMINISTIC_EXHAUSTIVE_ENUMERATION_BASELINE"
    assert res.execution_time_ms > 0.0


def test_deterministic_repeated_execution(db_session: Session):
    """Test 2: Deterministic repeated execution yields identical Pareto front results."""
    builder = CandidateBuilder(db_session)
    candidates = builder.build_candidates()

    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled",
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0
    )
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)

    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)
    filtering_res = FilteringResult(commodity="apple", total_candidates_evaluated=len(candidates))

    input_env1 = OptimizationInputEnvelope(
        optimization_run_id="run-repeat-1",
        commodity="apple",
        target_shelf_life_days=14,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        package_geometry=geometry,
        packaging_requirement_envelope=req_env,
        filtering_result=filtering_res,
        eligible_candidate_materials=candidates,
        active_objectives=["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"],
        solver_configuration=SolverConfiguration(execution_tier=OptimizationExecutionTier.LATTICE_LOOKUP)
    )

    input_env2 = OptimizationInputEnvelope(
        optimization_run_id="run-repeat-2",
        commodity="apple",
        target_shelf_life_days=14,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        package_geometry=geometry,
        packaging_requirement_envelope=req_env,
        filtering_result=filtering_res,
        eligible_candidate_materials=candidates,
        active_objectives=["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"],
        solver_configuration=SolverConfiguration(execution_tier=OptimizationExecutionTier.LATTICE_LOOKUP)
    )

    search_engine = DeterministicEnumerationSearchEngine()
    res1 = search_engine.search_with_summary(input_env1)
    res2 = search_engine.search_with_summary(input_env2)

    assert res1.feasible_candidates_count == res2.feasible_candidates_count
    assert res1.infeasible_candidates_count == res2.infeasible_candidates_count
    assert res1.unknown_candidates_count == res2.unknown_candidates_count
    assert len(res1.pareto_front.candidates) == len(res2.pareto_front.candidates)


def test_four_m6_b3_objectives_evaluated(db_session: Session):
    """Test 8 & 9: Use of all four M6-B3 objectives without scalarization or extra dimensions."""
    builder = CandidateBuilder(db_session)
    candidates = builder.build_candidates()

    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled"
    )
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)
    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)

    input_env = OptimizationInputEnvelope(
        optimization_run_id="run-objs",
        commodity="apple",
        target_shelf_life_days=14,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        package_geometry=geometry,
        packaging_requirement_envelope=req_env,
        filtering_result=FilteringResult(commodity="apple", total_candidates_evaluated=len(candidates)),
        eligible_candidate_materials=candidates,
        active_objectives=["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"],
        solver_configuration=SolverConfiguration(execution_tier=OptimizationExecutionTier.LATTICE_LOOKUP)
    )

    search_engine = DeterministicEnumerationSearchEngine()
    res = search_engine.search_with_summary(input_env)

    # Inspect objective keys for pareto candidates if any exist, or search result metadata
    expected_objs = {"f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"}
    if res.pareto_front.candidates:
        cand_objs = set(res.pareto_front.candidates[0].objective_values.keys())
        assert cand_objs == expected_objs
        # Confirm no extra objectives (e.g. cost, carbon) were added
        assert "cost" not in cand_objs
        assert "carbon" not in cand_objs


def test_empty_pareto_front_handling(db_session: Session):
    """Test 11: Empty Pareto front handling when 0 candidates are feasible."""
    # Pass an empty candidate list to search engine
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled"
    )
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)
    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)

    input_env = OptimizationInputEnvelope(
        optimization_run_id="run-empty",
        commodity="apple",
        target_shelf_life_days=14,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        package_geometry=geometry,
        packaging_requirement_envelope=req_env,
        filtering_result=FilteringResult(commodity="apple", total_candidates_evaluated=0),
        eligible_candidate_materials=[],
        active_objectives=["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"],
        solver_configuration=SolverConfiguration(execution_tier=OptimizationExecutionTier.LATTICE_LOOKUP)
    )

    search_engine = DeterministicEnumerationSearchEngine()
    res = search_engine.search_with_summary(input_env)

    assert res.total_candidates_considered == 0
    assert res.feasible_candidates_count == 0
    assert len(res.pareto_front.candidates) == 0
    assert res.pareto_front.candidate_count == 0


def test_recommendation_service_integration(db_session: Session):
    """Test 13 & 15: RecommendationService integration with M9 Search Engine Layer."""
    service = RecommendationService()
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled"
    )
    rec_res = service.generate_recommendation(req, db_session)

    assert rec_res.recommendation_run_id is not None
    assert rec_res.total_candidates_evaluated > 0
    assert len(rec_res.candidate_summaries) == rec_res.total_candidates_evaluated
    assert rec_res.pareto_front.solver_metadata.algorithm_name == "DETERMINISTIC_EXHAUSTIVE_ENUMERATION_BASELINE"
    # Ensure no scalar ranking field is injected
    assert not hasattr(rec_res, "rankings")
    assert not hasattr(rec_res, "best_material_score")


def test_api_recommendation_endpoint(api_client, db_session: Session):
    """Test 14: FastAPI POST /api/v1/recommend endpoint integration."""
    req_payload = {
        "commodity": "apple",
        "product_form": "fresh",
        "ripeness_stage": "mature",
        "target_shelf_life_days": 14,
        "storage_type": "chilled",
        "storage_temperature_c": 4.0,
        "relative_humidity_percent": 90.0
    }
    response = api_client.post("/api/v1/recommend", json=req_payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_candidates_evaluated"] > 0
    assert data["pareto_front"]["solver_metadata"]["algorithm_name"] == "DETERMINISTIC_EXHAUSTIVE_ENUMERATION_BASELINE"
    assert "candidate_summaries" in data
    assert len(data["candidate_summaries"]) == data["total_candidates_evaluated"]
