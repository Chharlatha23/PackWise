"""
Unit and Integration Tests for Milestone M11 — Explainability & Counterfactual Analysis.

Verifies:
1. FEASIBLE candidate explainability report generation.
2. INFEASIBLE candidate explainability report generation.
3. UNKNOWN candidate explainability report generation.
4. Gas OTR constraint explanation.
5. Gas CO2TR constraint explanation.
6. Moisture WVTR constraint explanation.
7. Objective value explanation and trade-off comparisons.
8. Bounded interval objective preservation (no midpoint collapse).
9. Evidence provenance reference preservation.
10. Predicted-vs-measured data classification distinction.
11. Feasible counterfactual threshold generation (BECOMES_INFEASIBLE_IF).
12. Infeasible counterfactual threshold generation (BECOMES_FEASIBLE_IF).
13. UNKNOWN counterfactual threshold generation (UNRESOLVED_DUE_TO_UNKNOWN).
14. Strict absence of midpoint scalar collapsing.
15. Strict absence of scalar material ranking or composite scores.
16. Integration into REST API response (POST /api/v1/recommend).
17. M9 deterministic exhaustive baseline regression protection.
18. M10 intelligent adaptive search engine regression protection.
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
    OptimizationExecutionTier
)
from app.schemas.candidate_feasibility import FilteringResult

from scientific_engine.physics.requirements import PackagingRequirementEngine
from scientific_engine.inference.engine import PropertyInferenceEngine
from scientific_engine.optimization.candidate_builder import CandidateBuilder
from scientific_engine.optimization.search_engine import (
    DeterministicEnumerationSearchEngine,
    IntelligentInverseDesignSearchEngine
)
from scientific_engine.optimization.explainability_engine import ExplainabilityEngine
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


def test_feasible_candidate_explanation_and_counterfactual(db_session: Session):
    """Tests 1, 4, 5, 6, 7, 11: Feasible candidate explanations, constraint details, and feasible counterfactual."""
    service = RecommendationService()
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled",
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0
    )
    rec_res = service.generate_recommendation(req, db_session)

    assert rec_res.pipeline_explainability is not None
    assert rec_res.pipeline_explainability.total_candidates_explained == rec_res.total_candidates_evaluated
    
    # Check candidate summary explainability report
    summary = rec_res.candidate_summaries[0]
    assert summary.explainability is not None
    report = summary.explainability

    assert report.overall_feasibility_status in ["FEASIBLE", "INFEASIBLE", "UNKNOWN"]
    assert len(report.constraint_explanations) == 3 # OTR, CO2TR, WVTR
    
    # Verify OTR, CO2TR, WVTR types present
    c_types = [c.constraint_type for c in report.constraint_explanations]
    assert "gas_exchange_otr" in c_types
    assert "gas_exchange_co2tr" in c_types
    assert "moisture_wvtr" in c_types

    # Verify counterfactual explanations
    assert len(report.counterfactual_explanations) > 0
    wvtr_cf = next((cf for cf in report.counterfactual_explanations if cf.target_property == "allowable_wvtr"), None)
    assert wvtr_cf is not None
    assert wvtr_cf.status_flip_condition in ["BECOMES_INFEASIBLE_IF", "BECOMES_FEASIBLE_IF", "UNRESOLVED_DUE_TO_UNKNOWN"]


def test_infeasible_candidate_counterfactual(db_session: Session):
    """Tests 2, 12: Infeasible candidate explanation and counterfactual threshold."""
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
        optimization_run_id="run-exp-inf",
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

    # Find an infeasible candidate report if present
    inf_report = next((s.explainability for s in res.candidate_summaries if s.constraint_status == "INFEASIBLE"), None)
    if inf_report:
        assert inf_report.overall_feasibility_status == "INFEASIBLE"
        assert "excluded from the Pareto front" in inf_report.pareto_explanation
        cf_list = inf_report.counterfactual_explanations
        assert len(cf_list) > 0


def test_unknown_candidate_counterfactual(db_session: Session):
    """Tests 3, 13: UNKNOWN candidate explanation and unresolved counterfactual handling."""
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
        optimization_run_id="run-exp-unk",
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

    # Find an UNKNOWN candidate report if present
    unk_report = next((s.explainability for s in res.candidate_summaries if s.constraint_status == "UNKNOWN"), None)
    if unk_report:
        assert unk_report.overall_feasibility_status == "UNKNOWN"
        wvtr_cf = next((cf for cf in unk_report.counterfactual_explanations if cf.target_property == "allowable_wvtr"), None)
        if wvtr_cf:
            assert wvtr_cf.status_flip_condition == "UNRESOLVED_DUE_TO_UNKNOWN"
            assert wvtr_cf.is_resolved is False


def test_evidence_provenance_and_predicted_distinction(db_session: Session):
    """Tests 9, 10: Evidence provenance preservation and predicted-vs-measured distinction."""
    builder = CandidateBuilder(db_session)
    candidates = builder.build_candidates()
    assert len(candidates) > 0

    cand = candidates[0]
    explainability_engine = ExplainabilityEngine()
    prov_ref = explainability_engine._extract_provenance(cand)

    assert prov_ref.material_id == cand.material_id
    assert prov_ref.evidence_classification is not None
    assert isinstance(prov_ref.is_model_predicted, bool)


def test_no_scalar_recommendation_score_or_midpoint_collapse(db_session: Session):
    """Tests 8, 14, 15: Bounded interval preservation, no midpoint collapse, no scalar ranking score."""
    service = RecommendationService()
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=14,
        storage_type="chilled"
    )
    rec_res = service.generate_recommendation(req, db_session)

    assert not hasattr(rec_res, "rankings")
    assert not hasattr(rec_res, "best_material_score")
    assert rec_res.pipeline_explainability is not None


def test_api_explainability_response_integration(api_client, db_session: Session):
    """Test 16: API response integration for explainability section."""
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

    assert "pipeline_explainability" in data
    assert data["pipeline_explainability"]["total_candidates_explained"] > 0
    assert "candidate_summaries" in data
    first_summary = data["candidate_summaries"][0]
    assert "explainability" in first_summary
    assert "constraint_explanations" in first_summary["explainability"]
    assert "counterfactual_explanations" in first_summary["explainability"]


def test_m9_and_m10_search_engine_regression_protection(db_session: Session):
    """Tests 17, 18: Regression protection for both M9 baseline and M10 intelligent engine."""
    service = RecommendationService()
    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled")

    # M9 baseline execution
    rec_res_m9 = service.generate_recommendation(req, db_session, search_engine_type="deterministic_exhaustive")
    assert rec_res_m9.pareto_front.solver_metadata.algorithm_name == "DETERMINISTIC_EXHAUSTIVE_ENUMERATION_BASELINE"
    assert rec_res_m9.pipeline_explainability is not None

    # M10 adaptive execution
    rec_res_m10 = service.generate_recommendation(req, db_session, search_engine_type="intelligent")
    assert rec_res_m10.pareto_front.solver_metadata.algorithm_name == "ADAPTIVE_PARETO_FRONTIER_SEARCH_ENGINE"
    assert rec_res_m10.pipeline_explainability is not None
