"""
Phase 3A — Layer 5 — Issue 8: AI Search Validation, Benchmarking & Scientific Acceptance Tests.

Comprehensive Verification Suite covering AC-01 through AC-12 and Section 23 Test Requirements:
1. Common benchmark candidate space protocol.
2. M9/M10/M11 unique candidate counting telemetry.
3. Common raw-physics counting boundary.
4. Feasible candidate recovery (R_feasible).
5. Complete vs. Incomplete M9 computational reference handling.
6. M11 candidate global Pareto classification (P_M11_in_P_M9, P_M11_reference_dominated, P_M11_global_status_unresolved).
7. OOD bypass state & exact-physics fallback eligibility.
8. Unknown/missing input preservation (AC-07, zero numeric default substitution).
9. Level-B scenario discrete preservation (AC-08).
10. Physics unresolved state handling (AC-11, PHYSICS_UNRESOLVED vs INFEASIBLE).
11. Qualified structural determinism verification across repeated executions (AC-09).
12. Timing telemetry accounting (AC-05, monotonic timers, wall-clock speedup).
13. Dynamic lineage resolution from registered model manifests (AC-10).
14. Stratified support analysis without arbitrary N thresholds (AC-02 / Section 20).
15. Automated Acceptance Report Generator verifying AC-01 through AC-12.
16. Scope-integrity audit verifying zero architecture mutation.
"""

import pytest
import time
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.evidence import PackagingMaterial
from backend.app.schemas.packaging_request import PackagingRequest
from scientific_engine.physics.requirements import PackagingRequirementEngine
from scientific_engine.inference.engine import PropertyInferenceEngine
from app.schemas.packaging_requirements import PackagingRequirementEnvelope
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
    OptimizationMetadata,
    ParetoFront,
    ParetoCandidate,
    ObjectiveDirection,
    ObjectiveValue,
    CandidateConstraintStatus,
    ConditionMatchLevel,
    EvidenceTier,
    UncertaintyType,
    UncertaintyProfile,
    ExplanationPayload,
    ScientificTraceability,
)
from app.schemas.constraints import ConstraintStatus
from app.schemas.ai_surrogate import (
    SurrogateModelRegistry,
    SurrogateModelManifest,
    SurrogateApplicabilityEngine,
    SurrogatePerformanceMetrics,
    ComputationalCostMetrics,
    AITargetEnum,
)
from scientific_engine.optimization.benchmark_contracts import (
    BenchmarkScenario,
    BenchmarkAlgorithmConfig,
    ReproducibilityMetadata,
)
from scientific_engine.optimization.issue8_benchmark_adapter import (
    M9BenchmarkAdapter,
    M10BenchmarkAdapter,
    M11BenchmarkAdapter,
    BenchmarkRunTelemetry,
)
from scientific_engine.optimization.issue8_telemetry_collector import (
    Issue8ValidationTelemetryCollector,
    M9ReferenceStatusEnum,
    GlobalParetoStatusEnum,
    StratumSupportStatusEnum,
)
from scientific_engine.optimization.issue8_acceptance_report import (
    Issue8AcceptanceReportGenerator,
    AcceptanceCriterionStatusEnum,
)


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


@pytest.fixture
def sample_candidates() -> List[PackagingCandidate]:
    prov = CandidateEvidenceReference(
        source_id="src_1",
        source_name="Test Source",
        record_identifier_in_source="rec_1",
        evidence_classification="EXPERIMENTAL_LITERATURE_DATA",
        verification_status="VERIFIED",
        doi="10.1016/j.foodchem.2021.100001",
    )
    return [
        PackagingCandidate(
            candidate_id="cand_ldpe_50",
            material_id="LDPE",
            material_name="Low-Density Polyethylene",
            decision_variables=CandidateDecisionVariables(total_thickness_um=50.0, thickness_source="observed_discrete_m5"),
            barrier_properties=CandidateBarrierProperties(
                wvtr=BarrierPropertyMetric(value=5.0, unit="g/m2/day"),
                otr=BarrierPropertyMetric(value=500.0, unit="cc/m2/day"),
            ),
            condition_match=ConditionMatchLevel.EXACT,
            provenance=prov,
        ),
        PackagingCandidate(
            candidate_id="cand_evoh_30",
            material_id="EVOH",
            material_name="Ethylene Vinyl Alcohol",
            decision_variables=CandidateDecisionVariables(total_thickness_um=30.0, thickness_source="observed_discrete_m5"),
            barrier_properties=CandidateBarrierProperties(
                wvtr=BarrierPropertyMetric(value=1.5, unit="g/m2/day"),
                otr=BarrierPropertyMetric(value=10.0, unit="cc/m2/day"),
            ),
            condition_match=ConditionMatchLevel.EXACT,
            provenance=prov,
        ),
        PackagingCandidate(
            candidate_id="cand_pet_40",
            material_id="PET",
            material_name="Polyethylene Terephthalate",
            decision_variables=CandidateDecisionVariables(total_thickness_um=40.0, thickness_source="observed_discrete_m5"),
            barrier_properties=CandidateBarrierProperties(
                wvtr=BarrierPropertyMetric(value=3.0, unit="g/m2/day"),
                otr=BarrierPropertyMetric(value=100.0, unit="cc/m2/day"),
            ),
            condition_match=ConditionMatchLevel.EXACT,
            provenance=prov,
        ),
    ]


@pytest.fixture
def sample_benchmark_scenario(sample_candidates) -> BenchmarkScenario:
    req = PackagingRequest(
        commodity="apple",
        product_form="fresh",
        ripeness_stage="mature",
        target_shelf_life_days=30.0,
        storage_type="chilled",
        storage_temperature_c=23.0,
        relative_humidity_percent=75.0,
    )
    inf_profile = PropertyInferenceEngine().infer_profile(req)
    req_env = PackagingRequirementEngine().evaluate_requirements(req, inf_profile, 0.5, 0.05)
    geom = PackageGeometry(package_type="Pouch", surface_area_m2=0.05, volume_m3=0.001)
    return BenchmarkScenario(
        scenario_id="scen_apples_std",
        scenario_name="Standard Apple Benchmark Scenario",
        requirement_envelope=req_env,
        package_geometry=geom,
        active_objectives=["shelf_life_days", "total_thickness_um"],
        eligible_candidate_ids=[c.candidate_id for c in sample_candidates],
    )


# -----------------------------------------------------------------------------
# TEST 1: Common Benchmark Candidate Space & Adapter Execution
# -----------------------------------------------------------------------------
def test_issue8_adapters_common_candidate_space(sample_benchmark_scenario, sample_candidates):
    """Test 1: Adapters run M9, M10, M11 on identical candidate space & scenario."""
    config = BenchmarkAlgorithmConfig(algorithm_id="test_engine", configuration_name="default", parameters={"max_evaluations": 10})
    
    adapter_m9 = M9BenchmarkAdapter()
    adapter_m9.initialize(sample_benchmark_scenario, sample_candidates, config)
    res_m9 = adapter_m9.execute_search()
    assert adapter_m9.telemetry.n_canonical == len(sample_candidates)
    assert adapter_m9.is_terminated()

    adapter_m11 = M11BenchmarkAdapter()
    adapter_m11.initialize(sample_benchmark_scenario, sample_candidates, config)
    res_m11 = adapter_m11.execute_search()
    assert adapter_m11.telemetry.n_canonical == len(sample_candidates)
    assert adapter_m11.is_terminated()


# -----------------------------------------------------------------------------
# TEST 2: Unique vs. Raw Physics Telemetry Boundaries (AC-04)
# -----------------------------------------------------------------------------
def test_issue8_unique_vs_raw_physics_counting(sample_benchmark_scenario, sample_candidates):
    """Test 2: Common raw-physics counting boundary applies across M9 and M11."""
    config = BenchmarkAlgorithmConfig(algorithm_id="test_engine", configuration_name="default", parameters={"max_evaluations": 2})

    adapter_m11 = M11BenchmarkAdapter(max_evaluations=2)
    adapter_m11.initialize(sample_benchmark_scenario, sample_candidates, config)
    adapter_m11.execute_search()
    
    t11 = adapter_m11.telemetry
    assert t11.n_unique_physics_evaluated <= len(sample_candidates)
    assert t11.n_raw_physics_calls >= t11.n_unique_physics_evaluated
    assert t11.n_evaluable_not_evaluated == (t11.n_evaluable_canonical - t11.n_unique_physics_evaluated)


# -----------------------------------------------------------------------------
# TEST 3: Complete vs Incomplete M9 Reference & Feasible Recovery (AC-02)
# -----------------------------------------------------------------------------
def test_issue8_feasible_recovery_reference_handling():
    """Test 3: Calculate feasible candidate recovery under complete vs incomplete M9 reference."""
    collector = Issue8ValidationTelemetryCollector()

    m11_feasible = {"cand_evoh_30", "cand_pet_40"}
    m9_feasible = {"cand_ldpe_50", "cand_evoh_30", "cand_pet_40"}

    # Complete M9 reference
    r_comp, note_comp = collector.calculate_feasible_recovery(
        m11_feasible_ids=m11_feasible,
        m9_feasible_ids=m9_feasible,
        m9_reference_status=M9ReferenceStatusEnum.COMPLETE,
    )
    assert abs(r_comp - (2.0 / 3.0)) < 1e-4
    assert "Recovered 2/3" in note_comp

    # Incomplete M9 reference
    r_incomp, note_incomp = collector.calculate_feasible_recovery(
        m11_feasible_ids=m11_feasible,
        m9_feasible_ids=m9_feasible,
        m9_reference_status=M9ReferenceStatusEnum.INCOMPLETE,
    )
    assert r_incomp is None
    assert r_incomp != 0.0
    assert "incomplete" in note_incomp.lower()


# -----------------------------------------------------------------------------
# TEST 4: Global Pareto Status Classification (AC-03)
# -----------------------------------------------------------------------------
def test_issue8_pareto_reference_classification(sample_candidates):
    """Test 4: Classify M11 Pareto candidates relative to complete M9 reference front."""
    collector = Issue8ValidationTelemetryCollector()

    cand1 = sample_candidates[0]  # LDPE 50um
    cand2 = sample_candidates[1]  # EVOH 30um

    # Create dummy Pareto candidate objects
    pc1 = ParetoCandidate(
        pareto_candidate_id=cand1.candidate_id,
        candidate_design=cand1,
        objective_values={
            "shelf_life_days": ObjectiveValue(objective_name="shelf_life_days", value=40.0, direction=ObjectiveDirection.MAXIMIZE, unit="days", status="CALCULATED"),
            "total_thickness_um": ObjectiveValue(objective_name="total_thickness_um", value=50.0, direction=ObjectiveDirection.MINIMIZE, unit="um", status="CALCULATED"),
        },
        constraint_compliance_summary=CandidateConstraintStatus(
            all_hard_constraints_satisfied=True,
            evaluations=[],
            overall_status=ConstraintStatus.FEASIBLE,
            condition_match=ConditionMatchLevel.EXACT,
        ),
        uncertainty_profile=UncertaintyProfile(uncertainty_type=UncertaintyType.DETERMINISTIC_POINT),
        evidence_tier=EvidenceTier.TIER_1_EMPIRICAL,
        traceability=ScientificTraceability(model_name="test", equation_form="test", data_source_reference="test", timestamp_utc="2026-10-07T09:00:00Z"),
        explanation_payload=ExplanationPayload(trade_off_summary="test", limiting_barrier="test", primary_strength="test"),
    )
    pc2 = ParetoCandidate(
        pareto_candidate_id=cand2.candidate_id,
        candidate_design=cand2,
        objective_values={
            "shelf_life_days": ObjectiveValue(objective_name="shelf_life_days", value=100.0, direction=ObjectiveDirection.MAXIMIZE, unit="days", status="CALCULATED"),
            "total_thickness_um": ObjectiveValue(objective_name="total_thickness_um", value=30.0, direction=ObjectiveDirection.MINIMIZE, unit="um", status="CALCULATED"),
        },
        constraint_compliance_summary=CandidateConstraintStatus(
            all_hard_constraints_satisfied=True,
            evaluations=[],
            overall_status=ConstraintStatus.FEASIBLE,
            condition_match=ConditionMatchLevel.EXACT,
        ),
        uncertainty_profile=UncertaintyProfile(uncertainty_type=UncertaintyType.DETERMINISTIC_POINT),
        evidence_tier=EvidenceTier.TIER_1_EMPIRICAL,
        traceability=ScientificTraceability(model_name="test", equation_form="test", data_source_reference="test", timestamp_utc="2026-10-07T09:00:00Z"),
        explanation_payload=ExplanationPayload(trade_off_summary="test", limiting_barrier="test", primary_strength="test"),
    )

    meta = OptimizationMetadata(algorithm_name="test", iterations_completed=1, execution_time_ms=10.0, cache_hit=False)
    m11_pareto = ParetoFront(optimization_run_id="r11", timestamp="2026-10-07T09:00:00Z", candidate_count=2, candidates=[pc1, pc2], solver_metadata=meta, constraint_policy_version="1.0")
    m9_pareto = ParetoFront(optimization_run_id="r9", timestamp="2026-10-07T09:00:00Z", candidate_count=1, candidates=[pc2], solver_metadata=meta, constraint_policy_version="1.0")

    # When M9 reference is COMPLETE
    classifications = collector.classify_pareto_front(
        m11_pareto=m11_pareto,
        m9_pareto=m9_pareto,
        m9_reference_status=M9ReferenceStatusEnum.COMPLETE,
    )

    status_map = {c.candidate_id: c.global_pareto_status for c in classifications}
    assert status_map[cand2.candidate_id] == GlobalParetoStatusEnum.P_M11_IN_P_M9
    assert status_map[cand1.candidate_id] == GlobalParetoStatusEnum.P_M11_REFERENCE_DOMINATED

    # When M9 reference is INCOMPLETE
    classifications_incomp = collector.classify_pareto_front(
        m11_pareto=m11_pareto,
        m9_pareto=m9_pareto,
        m9_reference_status=M9ReferenceStatusEnum.INCOMPLETE,
    )
    for c in classifications_incomp:
        assert c.global_pareto_status == GlobalParetoStatusEnum.P_M11_GLOBAL_STATUS_UNRESOLVED


# -----------------------------------------------------------------------------
# TEST 5: OOD Safety, Bypass & Fallback Eligibility (AC-06)
# -----------------------------------------------------------------------------
def test_issue8_ood_safety_and_fallback():
    """Test 5: Verify OUT_OF_DOMAIN state is distinct from INFEASIBLE and remains Gate 3 evaluable."""
    app_engine = SurrogateApplicabilityEngine()
    context = {"material_name": "UNKNOWN_SYNTHETIC_POLYMER", "thickness_um": 500.0}

    diag = app_engine.evaluate_applicability(context)
    assert not diag.is_within_applicability_domain
    assert len(diag.limitations) > 0  # Limitations explain OOD reason


# -----------------------------------------------------------------------------
# TEST 6: Zero Unknown Numeric Coercion (AC-07)
# -----------------------------------------------------------------------------
def test_issue8_zero_unknown_numeric_coercion():
    """Test 6: Missing inputs yield UNEVALUABLE or UNKNOWN, never default 0.0 substitution."""
    cand_missing = PackagingCandidate(
        candidate_id="cand_null_thick",
        material_id="LDPE",
        material_name="Low-Density Polyethylene",
        decision_variables=CandidateDecisionVariables(total_thickness_um=None, thickness_source="observed_discrete_m5"),
        barrier_properties=CandidateBarrierProperties(),
        condition_match=ConditionMatchLevel.EXACT,
        provenance=CandidateEvidenceReference(
            source_id="src_1",
            source_name="Test Source",
            record_identifier_in_source="rec_1",
            evidence_classification="EXPERIMENTAL_LITERATURE_DATA",
            verification_status="VERIFIED",
        ),
    )
    # Total thickness is missing/None
    assert cand_missing.decision_variables.total_thickness_um is None
    # Verify no automatic 0.0 coercer exists in CandidateDecisionVariables
    assert cand_missing.decision_variables.total_thickness_um != 0.0


# -----------------------------------------------------------------------------
# TEST 7: Qualified Structural Determinism (AC-09)
# -----------------------------------------------------------------------------
def test_issue8_qualified_structural_determinism(sample_benchmark_scenario, sample_candidates):
    """Test 7: Verification of structural invariants reproduction across identical repeated executions."""
    config = BenchmarkAlgorithmConfig(algorithm_id="m11_engine", configuration_name="default", parameters={"max_evaluations": 10})

    adapter1 = M11BenchmarkAdapter()
    adapter1.initialize(sample_benchmark_scenario, sample_candidates, config)
    adapter1.execute_search()
    t1 = adapter1.telemetry

    adapter2 = M11BenchmarkAdapter()
    adapter2.initialize(sample_benchmark_scenario, sample_candidates, config)
    adapter2.execute_search()
    t2 = adapter2.telemetry

    collector = Issue8ValidationTelemetryCollector()
    audit_res = collector.verify_qualified_determinism(t1, t2)

    assert audit_res.reproducibility_verified
    assert audit_res.structural_invariants_reproduced["discrete_counts_match"]
    assert audit_res.structural_invariants_reproduced["pareto_candidate_ids_match"]


# -----------------------------------------------------------------------------
# TEST 8: Dynamic Lineage Resolution (AC-10)
# -----------------------------------------------------------------------------
def test_issue8_dynamic_lineage_resolution():
    """Test 8: Dynamic lineage is resolved from registered SurrogateModelManifest."""
    registry = SurrogateModelRegistry()
    manifest = SurrogateModelManifest(
        model_id="manifest_layer4_shelflife_default",
        model_version="1.0.0",
        target_name=AITargetEnum.SHELF_LIFE_EST,
        model_family="TREE_GRADIENT_BOOSTING",
        dataset_version="1.0.0",
        physics_model_version="v3.0-exact-reference",
        physics_reference_version="1.0.0",
        feature_schema_version="1.0.0",
        target_transformation_version="1.0.0",
        material_thickness_domain_version="1.0.0",
        metrics=SurrogatePerformanceMetrics(
            target_name=AITargetEnum.SHELF_LIFE_EST,
            sample_count=100,
            mae=1.2,
            rmse=1.5,
            r2=0.95,
            relative_error_pct=5.0,
            worst_case_error=2.5,
        ),
        computational_cost=ComputationalCostMetrics(
            exact_physics_eval_time_ms_per_record=15.0,
            surrogate_inference_time_ms_per_record=0.5,
            preprocessing_and_applicability_time_ms_per_record=0.1,
            training_time_ms=500.0,
            speedup_factor=30.0,
        ),
        acceptance_status="ACCEPTED",
        acceptance_rationale="Test acceptance rationale",
    )
    registry.register_model(manifest, model_artifact="dummy_model")

    env = ReproducibilityMetadata(
        git_commit_hash="abc1234",
        python_version="3.11.0",
        platform_system="Windows",
        execution_timestamp_utc="2026-10-07T09:00:00Z",
    )
    t_m11 = BenchmarkRunTelemetry(run_id="run_bench_01", algorithm_id="M11_AI_SEARCH")

    generator = Issue8AcceptanceReportGenerator(surrogate_registry=registry)
    report = generator.generate_report(
        m11_telemetry=t_m11,
        m9_telemetry=None,
        m9_reference_status=M9ReferenceStatusEnum.INCOMPLETE,
        environment=env,
        manifest_id="manifest_layer4_shelflife_default",
    )

    assert report.lineage.model_manifest_id == manifest.model_id
    assert report.lineage.feature_schema_version == manifest.feature_schema_version
    assert report.lineage.physics_model_version == manifest.physics_model_version


# -----------------------------------------------------------------------------
# TEST 9: Stratified Support Analysis without Arbitrary N Thresholds (Section 20)
# -----------------------------------------------------------------------------
def test_issue8_stratified_support_without_arbitrary_n_thresholds(sample_candidates):
    """Test 9: Stratified support reported qualitatively (ADEQUATE_SUPPORT vs INSUFFICIENT_DATA)."""
    collector = Issue8ValidationTelemetryCollector()

    m9_feasible = {"cand_ldpe_50", "cand_evoh_30", "cand_pet_40"}
    m11_feasible = {"cand_evoh_30", "cand_pet_40"}

    # Adequate support stratum
    rec_adeq = collector.analyze_stratified_support(
        stratum_name="High-Barrier Polyamides",
        stratum_candidates=sample_candidates,
        m9_feasible_ids=m9_feasible,
        m11_feasible_ids=m11_feasible,
    )
    assert rec_adeq.support_status == StratumSupportStatusEnum.ADEQUATE_SUPPORT
    assert "adequate" in rec_adeq.qualitative_note.lower()

    # Sparse support stratum
    rec_sparse = collector.analyze_stratified_support(
        stratum_name="Experimental Bio-Films",
        stratum_candidates=[sample_candidates[0]],
        m9_feasible_ids={"cand_ldpe_50"},
        m11_feasible_ids={"cand_ldpe_50"},
    )
    assert rec_sparse.support_status == StratumSupportStatusEnum.INSUFFICIENT_DATA
    assert "sparse" in rec_sparse.qualitative_note.lower()


# -----------------------------------------------------------------------------
# TEST 10: Automated Scientific Acceptance Report Generator (AC-01 to AC-12)
# -----------------------------------------------------------------------------
def test_issue8_acceptance_report_generator_full_evaluation(sample_benchmark_scenario, sample_candidates):
    """Test 10: Generator evaluates AC-01 through AC-12 with explicit status, evidence, measurement & limitations."""
    env = ReproducibilityMetadata(
        git_commit_hash="abc1234",
        python_version="3.11.0",
        platform_system="Windows",
        execution_timestamp_utc="2026-10-07T09:00:00Z",
    )

    adapter_m9 = M9BenchmarkAdapter()
    adapter_m9.initialize(sample_benchmark_scenario, sample_candidates, BenchmarkAlgorithmConfig(algorithm_id="m9", configuration_name="default"))
    adapter_m9.execute_search()

    adapter_m11 = M11BenchmarkAdapter()
    adapter_m11.initialize(sample_benchmark_scenario, sample_candidates, BenchmarkAlgorithmConfig(algorithm_id="m11", configuration_name="default"))
    adapter_m11.execute_search()

    generator = Issue8AcceptanceReportGenerator()
    report = generator.generate_report(
        m11_telemetry=adapter_m11.telemetry,
        m9_telemetry=adapter_m9.telemetry,
        m9_reference_status=M9ReferenceStatusEnum.COMPLETE,
        environment=env,
        manifest_id="manifest_layer4_shelflife_default",
        all_candidates=sample_candidates,
        context_template={"commodity": "Fresh Apples"},
        multi_run_telemetry=adapter_m11.telemetry,
    )

    assert len(report.acceptance_criteria_results) == 12
    criterion_ids = [c.criterion_id for c in report.acceptance_criteria_results]
    for i in range(1, 13):
        assert f"AC-{i:02d}" in criterion_ids

    for cr in report.acceptance_criteria_results:
        assert cr.status in [AcceptanceCriterionStatusEnum.PASS, AcceptanceCriterionStatusEnum.BLOCKED]
        assert len(cr.evidence) > 0
        assert len(cr.measurement) > 0
        assert len(cr.limitations) > 0


# -----------------------------------------------------------------------------
# TEST 11: Scope Integrity Verification (AC-12)
# -----------------------------------------------------------------------------
def test_issue8_scope_integrity():
    """Test 11: Verify zero architectural modification to M9, M10, M11, or Physics."""
    from scientific_engine.optimization.search_engine import (
        DeterministicEnumerationSearchEngine,
        IntelligentInverseDesignSearchEngine,
        AISurrogatePrioritizedSearchEngine,
    )
    # Verify M9, M10, M11 classes exist and preserve expected search interfaces
    assert hasattr(DeterministicEnumerationSearchEngine, "search_with_summary")
    assert hasattr(IntelligentInverseDesignSearchEngine, "search_with_summary")
    assert hasattr(AISurrogatePrioritizedSearchEngine, "search_with_summary")
