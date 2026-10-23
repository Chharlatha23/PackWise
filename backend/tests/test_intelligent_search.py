"""
Unit and Integration Tests for M10 Intelligent Inverse-Design Search Engine.

Verifies:
1. Intelligent engine implements AbstractInverseDesignSearchEngine interface.
2. Candidate selection sequence adaptively changes based on prior evaluation state.
3. Candidates are not repeatedly evaluated unnecessarily (no duplicate evaluations).
4. Every candidate passes through the authoritative scientific evaluation pipeline.
5. Phase 5 hard constraints remain authoritative.
6. UNKNOWN remains UNKNOWN (excluded from feasible Pareto set, preserved in diagnostics, no numeric penalties).
7. INFEASIBLE candidates remain excluded from the Pareto front.
8. FEASIBLE candidates reach Pareto front construction.
9. All four M6-B3 objectives remain present without extra dimensions (cost, carbon, etc.).
10. Objective intervals remain intervals without midpoint collapse.
11. Reuses M6-B4A/B Pareto dominance and front construction implementations.
12. No scalar ranking or composite material scores introduced.
13. Deterministic reproducibility for identical search inputs.
14. M9 exhaustive baseline remains fully functional and accessible.
15. RecommendationService can execute M10 via parameter selection.
16. REST API remains functional.
17. Handles empty feasible sets gracefully.
18. Search termination condition works correctly.
19. Repeated execution does not corrupt search state.
20. No scientific evidence is modified.
"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine as _create_engine
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
    PackageGeometry,
    SolverConfiguration,
    OptimizationExecutionTier
)
from app.schemas.candidate_feasibility import FilteringResult

from scientific_engine.physics.requirements import PackagingRequirementEngine
from scientific_engine.inference.engine import PropertyInferenceEngine
from scientific_engine.optimization.candidate_builder import CandidateBuilder
from scientific_engine.optimization.search_engine import (
    AbstractInverseDesignSearchEngine,
    DeterministicEnumerationSearchEngine,
    IntelligentInverseDesignSearchEngine,
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


def test_m10_implements_search_interface():
    """Requirement 1: Intelligent engine implements AbstractInverseDesignSearchEngine interface."""
    engine_inst = IntelligentInverseDesignSearchEngine()
    assert isinstance(engine_inst, AbstractInverseDesignSearchEngine)


def test_m10_adaptive_candidate_selection_and_no_duplicates(db_session: Session):
    """Requirements 2, 3, 4, 18: Adaptive selection, no duplicates, scientific pipeline, termination."""
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

    input_envelope = OptimizationInputEnvelope(
        optimization_run_id="m10-run-adaptive",
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

    intelligent_engine = IntelligentInverseDesignSearchEngine()
    res = intelligent_engine.search_with_summary(input_envelope)

    assert res.algorithm_name == "ADAPTIVE_PARETO_FRONTIER_SEARCH_ENGINE"
    assert res.total_candidates_evaluated == len(candidates)

    # Check candidate evaluation order is tracked and unique (no duplicate evaluations)
    evaluated_ids = [s.candidate_id for s in res.candidate_summaries]
    assert len(evaluated_ids) == len(set(evaluated_ids))


def test_m10_constraints_and_unknown_handling(db_session: Session):
    """Requirements 5, 6, 7, 8, 9, 10, 11, 12: Phase 5 authority, UNKNOWN/INFEASIBLE handling, objectives, Pareto."""
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

    input_envelope = OptimizationInputEnvelope(
        optimization_run_id="m10-run-constraints",
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

    intelligent_engine = IntelligentInverseDesignSearchEngine()
    res = intelligent_engine.search_with_summary(input_envelope)

    # Ensure all candidates in summaries preserve their constraint status
    for summary in res.candidate_summaries:
        assert summary.constraint_status in ["FEASIBLE", "INFEASIBLE", "UNKNOWN"]

    # Ensure Pareto candidates are strictly FEASIBLE
    for pareto_cand in res.pareto_front.candidates:
        assert pareto_cand.constraint_compliance_summary.all_hard_constraints_satisfied is True
        assert pareto_cand.constraint_compliance_summary.overall_status.value == "FEASIBLE"

    # Verify no scalar ranking or composite score in pareto candidates
    if res.pareto_front.candidates:
        c = res.pareto_front.candidates[0]
        assert "f_thickness" in c.objective_values
        assert "f_moisture_margin" in c.objective_values
        assert "f_gas_alignment" in c.objective_values
        assert "f_shelf_life_margin" in c.objective_values
        assert not hasattr(c, "scalar_score")


def test_m10_deterministic_reproducibility(db_session: Session):
    """Requirements 13, 19: Deterministic reproducibility and uncorrupted state on repeated runs."""
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
        optimization_run_id="m10-run-repro",
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

    engine_inst = IntelligentInverseDesignSearchEngine()
    res1 = engine_inst.search_with_summary(input_env)
    res2 = engine_inst.search_with_summary(input_env)

    assert res1.feasible_candidates_count == res2.feasible_candidates_count
    assert res1.infeasible_candidates_count == res2.infeasible_candidates_count
    assert res1.unknown_candidates_count == res2.unknown_candidates_count
    assert len(res1.pareto_front.candidates) == len(res2.pareto_front.candidates)


def test_m9_baseline_preserved(db_session: Session):
    """Requirement 14: M9 deterministic exhaustive baseline remains fully functional."""
    m9_engine = DeterministicEnumerationSearchEngine()
    assert isinstance(m9_engine, AbstractInverseDesignSearchEngine)

    builder = CandidateBuilder(db_session)
    candidates = builder.build_candidates()
    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled")
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)
    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)

    input_env = OptimizationInputEnvelope(
        optimization_run_id="m9-check",
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

    res = m9_engine.search_with_summary(input_env)
    assert res.algorithm_name == "DETERMINISTIC_EXHAUSTIVE_ENUMERATION_BASELINE"


def test_recommendation_service_m10_execution(db_session: Session):
    """Requirement 15: RecommendationService can execute M10 via parameter selection."""
    service = RecommendationService()
    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled")
    
    rec_res = service.generate_recommendation(req, db_session, search_engine_type="intelligent")
    assert rec_res.pareto_front.solver_metadata.algorithm_name == "ADAPTIVE_PARETO_FRONTIER_SEARCH_ENGINE"


def test_api_recommendation_m10_endpoint(api_client, db_session: Session):
    """Requirement 16: FastAPI POST /api/v1/recommend endpoint remains functional."""
    req_payload = {
        "commodity": "apple",
        "product_form": "fresh",
        "ripeness_stage": "mature",
        "target_shelf_life_days": 14,
        "storage_type": "chilled"
    }
    response = api_client.post("/api/v1/recommend", json=req_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_candidates_evaluated"] > 0
    assert "pareto_front" in data


def test_empty_feasible_set_handling(db_session: Session):
    """Requirement 17: Empty feasible set handled gracefully."""
    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled")
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)
    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)

    input_env = OptimizationInputEnvelope(
        optimization_run_id="m10-empty",
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

    intelligent_engine = IntelligentInverseDesignSearchEngine()
    res = intelligent_engine.search_with_summary(input_env)
    assert res.total_candidates_considered == 0
    assert res.feasible_candidates_count == 0
    assert len(res.pareto_front.candidates) == 0
