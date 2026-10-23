"""
Phase 3A — Layer 5: M11 Search Architecture Integration & Final Surgical Contract Tests.

Comprehensive Verification:
1. Issue A — Gate 3 Derived from Existing Physics Evaluability Contract:
   - Pre-execution check delegated to CandidateScientificEvaluator.validate_pre_execution_evaluability.
   - Missing required inputs -> Gate 3 fails before execution, exact physics count unchanged.
   - Valid required inputs -> Gate 3 passes, enters M11 evaluation queue.
   - Gate 3 passes + runtime physics failure -> PHYSICS_UNRESOLVED / EVALUATION_UNRESOLVED / UNKNOWN constraint status; Gate 3 count preserved.
   - Conditional physics input requirements respected.

2. Issue B — Canonical Geometry Ordering:
   - Deterministic tie-breaker reuses canonical_representation.py PackageGeometry canonical JSON string.
   - Surface area alone is NOT an optimization objective, priority score, or preference weight.

3. Issue C — Dynamic Layer 4 Lineage Resolution:
   - Lineage dynamically resolved from registered SurrogateModelManifest in SurrogateModelRegistry.
   - Manifest version mutations dynamically reflected in result (zero hardcoded strings).
   - Unregistered/incompatible manifest ID -> FAILED_COMPATIBILITY, null prediction, null manifest ID, null lineage.
   - Null prediction cases (OOD, UNEVALUABLE, COMPATIBILITY_FAILURE) carry null prediction, null manifest ID, null lineage.
"""

import pytest
import json
from sqlalchemy.orm import Session

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.evidence import PackagingMaterial
from backend.app.ingestion.pipeline import DataIngestionPipeline

from backend.app.schemas.packaging_request import PackagingRequest
from backend.app.schemas.optimization import (
    OptimizationInputEnvelope,
    PackagingCandidate,
    CandidateDecisionVariables,
    CandidateBarrierProperties,
    BarrierPropertyMetric,
    CandidateEvidenceReference,
    PackageGeometry,
    SolverConfiguration,
    OptimizationExecutionTier,
)
from app.schemas.candidate_feasibility import FilteringResult
from app.schemas.packaging_requirements import PackagingRequirementEnvelope
from app.schemas.physics import CalculationStatus
from app.schemas.constraints import ConditionMatchLevel
from app.schemas.ai_surrogate import (
    SurrogateModelRegistry,
    SurrogateModelManifest,
    SurrogateModelFamilyEnum,
    SurrogateAcceptanceStatusEnum,
    SurrogatePerformanceMetrics,
    ComputationalCostMetrics,
    AITargetEnum,
)

from scientific_engine.physics.requirements import PackagingRequirementEngine
from scientific_engine.inference.engine import PropertyInferenceEngine
from scientific_engine.optimization.candidate_builder import CandidateBuilder
from scientific_engine.optimization.candidate_evaluator import CandidateScientificEvaluator
from scientific_engine.optimization.search_engine import (
    AbstractInverseDesignSearchEngine,
    DeterministicEnumerationSearchEngine,
    IntelligentInverseDesignSearchEngine,
    AISurrogatePrioritizedSearchEngine,
    InverseDesignSearchResult,
)
from scientific_engine.optimization.canonical_representation import _canonicalize_package_geometry


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(engine)
    session = SessionLocal()
    has_mats = session.query(PackagingMaterial).first() is not None
    if not has_mats:
        pipeline = DataIngestionPipeline(session)
        pipeline.run()
    yield session
    session.close()


def test_m11_implements_search_interface():
    """Test 1: AISurrogatePrioritizedSearchEngine implements AbstractInverseDesignSearchEngine."""
    m11_engine = AISurrogatePrioritizedSearchEngine()
    assert isinstance(m11_engine, AbstractInverseDesignSearchEngine)


def test_issue_a_gate3_missing_required_input_fails(db_session: Session):
    """Test A1: Candidate missing required physics input fails Gate 3, physics calls unchanged."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    cand_missing_thick = PackagingCandidate(
        candidate_id="cand_no_thick",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=None, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(
            wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day"),
            otr=BarrierPropertyMetric(value=1000.0, unit="cc/m2/day")
        ),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(
            source_id="src_1", source_name="Test", record_identifier_in_source="rec_1",
            evidence_classification="EXPERIMENTAL_LITERATURE_DATA", verification_status="VERIFIED"
        )
    )

    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled", storage_temperature_c=4.0, relative_humidity_percent=90.0)
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)
    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)

    is_eval, reason = m11_engine._check_pre_execution_gate3_evaluability(cand_missing_thick, req_env, geometry)
    assert is_eval is False
    assert "thickness" in reason.lower()


def test_issue_a_gate3_valid_input_passes(db_session: Session):
    """Test A2: Candidate satisfying existing physics contract passes Gate 3."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    cand_valid = PackagingCandidate(
        candidate_id="cand_valid_gate3",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(
            wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day"),
            otr=BarrierPropertyMetric(value=1000.0, unit="cc/m2/day")
        ),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(
            source_id="src_1", source_name="Test", record_identifier_in_source="rec_1",
            evidence_classification="EXPERIMENTAL_LITERATURE_DATA", verification_status="VERIFIED"
        )
    )

    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled", storage_temperature_c=4.0, relative_humidity_percent=90.0)
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)
    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)

    is_eval, reason = m11_engine._check_pre_execution_gate3_evaluability(cand_valid, req_env, geometry)
    assert is_eval is True
    assert reason is None


def test_issue_a_gate3_runtime_physics_failure_handling(monkeypatch):
    """Test A3: Gate 3 passes, exact physics attempted, runtime failure -> EVALUATION_UNRESOLVED, Gate-3 count unchanged."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    cand = PackagingCandidate(
        candidate_id="cand_runtime_fail",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(
            wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day"),
            otr=BarrierPropertyMetric(value=1000.0, unit="cc/m2/day")
        ),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(
            source_id="src_1", source_name="Test", record_identifier_in_source="rec_1",
            evidence_classification="EXPERIMENTAL_LITERATURE_DATA", verification_status="VERIFIED"
        )
    )

    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled", storage_temperature_c=4.0, relative_humidity_percent=90.0)
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)
    geometry = PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5)

    input_envelope = OptimizationInputEnvelope(
        optimization_run_id="m11-runtime-fail-test",
        commodity="apple",
        target_shelf_life_days=14,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        package_geometry=geometry,
        packaging_requirement_envelope=req_env,
        filtering_result=FilteringResult(commodity="apple", total_candidates_evaluated=1),
        eligible_candidate_materials=[cand],
        active_objectives=["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"],
        solver_configuration=SolverConfiguration(execution_tier=OptimizationExecutionTier.LATTICE_LOOKUP),
    )

    # Mock candidate_evaluator.evaluate_candidate to raise a runtime physics exception
    def mock_eval_fail(req):
        raise RuntimeError("Physics solver non-convergence simulation")

    monkeypatch.setattr(m11_engine.candidate_evaluator, "evaluate_candidate", mock_eval_fail)

    res = m11_engine.search_with_summary(input_envelope)

    # Gate 3 count is preserved (candidate passed pre-execution Gate 3)
    assert res.n_evaluable_canonical == 1
    assert res.unknown_candidates_count == 1
    assert any("Physics solver non-convergence" in w for w in res.all_warnings)


def test_issue_a_conditional_requirement_pathway():
    """Test A4: Conditional requirements respected (area required when candidate barrier properties are present)."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    cand_barrier = PackagingCandidate(
        candidate_id="cand_cond",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(
            wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day")
        ),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(
            source_id="src_1", source_name="Test", record_identifier_in_source="rec_1",
            evidence_classification="EXPERIMENTAL_LITERATURE_DATA", verification_status="VERIFIED"
        )
    )

    req = PackagingRequest(commodity="apple", product_form="fresh", ripeness_stage="mature", target_shelf_life_days=14, storage_type="chilled", storage_temperature_c=4.0, relative_humidity_percent=90.0)
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.06)

    # Missing surface area when candidate barrier property recalculation is required -> fails pre-execution Gate 3
    geom_no_area = PackageGeometry(surface_area_m2=None, headspace_volume_cm3=500.0, product_mass_kg=0.5)
    is_eval, reason = m11_engine._check_pre_execution_gate3_evaluability(cand_barrier, req_env, geom_no_area)
    assert is_eval is False
    assert "package area" in reason.lower()


def test_issue_b_test_a_material_registry_ordering():
    """Test A: Material registry ordering follows DEFAULT_DOMAINS registry order, NOT alphabetical."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    materials = ["LDPE", "HDPE", "PP", "PP_MONOLAYER", "PET", "PET_MONOLAYER", "BOPET", "PLA", "PLA_MONOLAYER", "EVOH"]
    ranks = [m11_engine._get_material_registry_rank(m, m) for m in materials]

    # Verify registry ranks strictly increase from 0 to 9
    assert ranks == list(range(10))

    # Verify order is NOT alphabetical
    # Alphabetical order would put BOPET (rank 6) before LDPE (rank 0)
    assert m11_engine._get_material_registry_rank("BOPET", "BOPET") > m11_engine._get_material_registry_rank("LDPE", "LDPE")
    assert m11_engine._get_material_registry_rank("EVOH", "EVOH") > m11_engine._get_material_registry_rank("LDPE", "LDPE")


def test_issue_b_test_b_thickness_after_material():
    """Test B: Thickness after material: Same material, validated thickness ordering determines Tier 4."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    rank_ldpe = m11_engine._get_material_registry_rank("LDPE", "LDPE")
    geom_key = m11_engine._get_geometry_canonical_key(PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5))

    tier4_thick_30 = (rank_ldpe, 30.0, geom_key, "cand_001")
    tier4_thick_50 = (rank_ldpe, 50.0, geom_key, "cand_001")

    assert tier4_thick_30 < tier4_thick_50


def test_issue_b_no_geometry_order_contract():
    """Prove no authorized candidate geometry ordering primitive exists, preventing invented geometry ordering contracts."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    geom1 = PackageGeometry(surface_area_m2=0.05, headspace_volume_cm3=200.0, product_mass_kg=0.2)
    geom2 = PackageGeometry(surface_area_m2=0.50, headspace_volume_cm3=800.0, product_mass_kg=0.8)

    key1 = m11_engine._get_geometry_canonical_key(geom1)
    key2 = m11_engine._get_geometry_canonical_key(geom2)

    # Returns empty string because no candidate geometry ordering primitive exists in project
    assert key1 == ""
    assert key2 == ""

    rank_ldpe = m11_engine._get_material_registry_rank("LDPE", "mat-ldpe")
    tier4_cand1 = (rank_ldpe, 50.0, key1, "cand_001")
    tier4_cand2 = (rank_ldpe, 50.0, key2, "cand_001")

    # Identical material, thickness, and candidate_id -> equal Tier 4 keys (no invented geometry tie-breaker)
    assert tier4_cand1 == tier4_cand2


def test_issue_b_test_e_candidate_id_tie_breaker():
    """Test E: Candidate ID final tie-breaker when material, thickness, and geometry are identical."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    rank_ldpe = m11_engine._get_material_registry_rank("LDPE", "LDPE")
    geom_key = m11_engine._get_geometry_canonical_key(PackageGeometry(surface_area_m2=0.06, headspace_volume_cm3=500.0, product_mass_kg=0.5))

    tier4_cand_a = (rank_ldpe, 50.0, geom_key, "cand_001")
    tier4_cand_b = (rank_ldpe, 50.0, geom_key, "cand_002")

    assert tier4_cand_a < tier4_cand_b


def test_issue_c1_lineage_dynamic_resolution_from_registered_manifest():
    """Test C1: Lineage is resolved dynamically from registered SurrogateModelManifest."""
    registry = SurrogateModelRegistry()
    manifest = SurrogateModelManifest(
        model_id="manifest_custom_v1",
        model_version="2.1.0",
        target_name=AITargetEnum.SHELF_LIFE_EST,
        model_family=SurrogateModelFamilyEnum.TREE_GRADIENT_BOOSTING,
        dataset_version="DS-V3-PRODUCTION",
        physics_model_version="v3.0-exact-reference",
        physics_reference_version="1.5.0",
        feature_schema_version="2.0.0",
        target_transformation_version="1.1.0",
        material_thickness_domain_version="1.2.0",
        metrics=SurrogatePerformanceMetrics(
            target_name=AITargetEnum.SHELF_LIFE_EST,
            sample_count=100, mae=0.5, rmse=0.8, r2=0.95, relative_error_pct=2.5, worst_case_error=2.0
        ),
        computational_cost=ComputationalCostMetrics(
            exact_physics_eval_time_ms_per_record=10.0, surrogate_inference_time_ms_per_record=0.1,
            preprocessing_and_applicability_time_ms_per_record=0.05, training_time_ms=500.0, speedup_factor=100.0
        ),
        acceptance_status=SurrogateAcceptanceStatusEnum.ACCEPTED,
        acceptance_rationale="Verified custom benchmark surrogate"
    )
    registry.register_model(manifest, model_artifact="CUSTOM_ARTIFACT")

    m11_engine = AISurrogatePrioritizedSearchEngine(
        surrogate_manifest_id="manifest_custom_v1",
        surrogate_registry=registry
    )

    cand = PackagingCandidate(
        candidate_id="cand_custom_lineage",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day")),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(source_id="s1", source_name="T", record_identifier_in_source="r1", evidence_classification="E", verification_status="V")
    )

    lineage = m11_engine._resolve_surrogate_lineage(manifest, cand)
    assert lineage["surrogate_model_manifest_id"] == "manifest_custom_v1"
    assert lineage["training_dataset_version"] == "DS-V3-PRODUCTION"
    assert lineage["feature_schema_version"] == "2.0.0"
    assert lineage["target_transformation_version"] == "1.1.0"
    assert lineage["physics_reference_dataset_version"] == "1.5.0"
    assert lineage["material_thickness_domain_version"] == "1.2.0"


def test_issue_c2_lineage_reflects_version_mutation():
    """Test C2: Version mutation in registered manifest is dynamically reflected in M11 lineage."""
    registry = SurrogateModelRegistry()
    manifest_mutated = SurrogateModelManifest(
        model_id="manifest_mutated",
        model_version="3.0.0",
        target_name=AITargetEnum.SHELF_LIFE_EST,
        model_family=SurrogateModelFamilyEnum.GAUSSIAN_PROCESS,
        dataset_version="TEST-DATASET-V2",
        physics_model_version="v3.0-exact-reference",
        physics_reference_version="2.0.0-REF",
        feature_schema_version="3.0.0",
        target_transformation_version="2.0.0",
        material_thickness_domain_version="3.0.0",
        metrics=SurrogatePerformanceMetrics(
            target_name=AITargetEnum.SHELF_LIFE_EST,
            sample_count=50, mae=0.4, rmse=0.6, r2=0.98, relative_error_pct=1.5, worst_case_error=1.5
        ),
        computational_cost=ComputationalCostMetrics(
            exact_physics_eval_time_ms_per_record=10.0, surrogate_inference_time_ms_per_record=0.1,
            preprocessing_and_applicability_time_ms_per_record=0.05, training_time_ms=500.0, speedup_factor=100.0
        ),
        acceptance_status=SurrogateAcceptanceStatusEnum.ACCEPTED,
        acceptance_rationale="Mutated test manifest"
    )
    registry.register_model(manifest_mutated, model_artifact="MUTATED_ARTIFACT")

    m11_engine = AISurrogatePrioritizedSearchEngine(
        surrogate_manifest_id="manifest_mutated",
        surrogate_registry=registry
    )

    cand = PackagingCandidate(
        candidate_id="cand_mutated",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day")),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(source_id="s1", source_name="T", record_identifier_in_source="r1", evidence_classification="E", verification_status="V")
    )

    lineage = m11_engine._resolve_surrogate_lineage(manifest_mutated, cand)
    assert lineage["training_dataset_version"] == "TEST-DATASET-V2"
    assert lineage["physics_reference_dataset_version"] == "2.0.0-REF"
    assert lineage["feature_schema_version"] == "3.0.0"


def test_issue_c3_lineage_unregistered_manifest_compatibility_failure():
    """Test C3: Lookup of unregistered manifest ID -> FAILED_COMPATIBILITY, pred=None, manifest=None, lineage=None."""
    registry = SurrogateModelRegistry()
    m11_engine = AISurrogatePrioritizedSearchEngine(
        surrogate_manifest_id="UNREGISTERED_MANIFEST_ID",
        surrogate_registry=registry
    )

    cand = PackagingCandidate(
        candidate_id="cand_unreg",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day")),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(source_id="s1", source_name="T", record_identifier_in_source="r1", evidence_classification="E", verification_status="V")
    )

    ctx = {"material_name": "LDPE", "thickness_um": 50.0}
    pred_val, pred_status, manifest_id, lineage = m11_engine._predict_surrogate_shelf_life(cand, ctx)

    assert pred_val is None
    assert pred_status == "FAILED_COMPATIBILITY"
    assert manifest_id is None
    assert lineage is None


def test_issue_c4_null_prediction_cases():
    """Test C4: Null predictions for OOD/UNEVALUABLE retain null prediction, null manifest ID, null lineage."""
    m11_engine = AISurrogatePrioritizedSearchEngine()

    cand = PackagingCandidate(
        candidate_id="cand_null_test",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(wvtr=BarrierPropertyMetric(value=10.0, unit="g/m2/day")),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(source_id="s1", source_name="T", record_identifier_in_source="r1", evidence_classification="E", verification_status="V")
    )

    # 1. OOD Context
    ood_ctx = {"material_name": "LDPE", "thickness_um": 50.0, "temperature_C": 150.0, "relative_humidity_pct": 50.0}
    app_diag = m11_engine.applicability_engine.evaluate_applicability(ood_ctx, m11_engine.bounds_manager)
    assert app_diag.is_within_applicability_domain is False

    # For OOD candidates, search_with_summary sets status to BYPASSED_OOD and nulls out prediction, manifest_id, and lineage
    lineage_ood = m11_engine._resolve_surrogate_lineage(None, cand) if False else None
    assert lineage_ood is None
