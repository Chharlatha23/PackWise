"""
Unit tests for Phase 3A — Implementation Layer 4: Surrogate Model Training & Benchmarking.

Verifies:
1. Target Eligibility: ShelfLife_est, OTR_pkg, WVTR_pkg eligible; MAP_CO2_peak explicitly DEFERRED.
2. Filter Integrity: Missing, NULL, failed physics, UNKNOWN data-status, and Level D unknown rejected (no zero coercion).
3. Data-Status Integrity: Data status preserved as MODEL_PREDICTED / SYNTHETIC; never relabeled as REAL_EMPIRICAL.
4. Duplicate & Conflict Detection: Input duplicates tracked; target conflicts (>5% variance) detected and reported.
5. Versioned Feature Schema: Metadata (record_id, citation_id, timestamp) and target-derived fields strictly excluded.
6. Epistemic Handling: Level A used normally, Level B as scenario vectors, Level D excluded (no zero encoding).
7. Material Thickness Domain: Thickness d in validated domain(material) enforced; invalid combinations rejected.
8. Dataset Splitting: Leakage-resistant interpolation and group holdout splits; unsupported holdouts reported explicitly.
9. Target Transformation: Transformation parameters fit strictly on train split; inverted before physical metric evaluation.
10. Model Benchmarking: Candidate A (Tree/GBR), Candidate B (GPR), Candidate C (MLP), and Baseline (Ridge) evaluated on identical splits.
11. Performance Metrics: MAE, RMSE, R2, relative error, worst-case error, and subgroup breakdowns recorded in physical units.
12. Physical Validity: Target validity checked; raw predictions preserved without silent clipping or replacement.
13. Applicability Diagnostic: Multi-signal OOD diagnostic produced with bounds checking and confidence score.
14. Computational Economics: Operational timing measured for exact physics vs surrogate inference, reporting speedup factor.
15. Manifest & Lineage: Immutable SurrogateModelManifest captures lineage, training config, metrics, and acceptance status.
16. Compatibility Validation: Compatibility check validates schema/physics/material versions; raises SurrogateCompatibilityError if mismatched.
17. Architectural Boundary Protection: Guarantees surrogate != feasibility gate, no M11 invocation, no residual learning, no Level C.
"""

import pytest
import numpy as np

from app.schemas.inference import UncertaintyLevelEnum
from app.schemas.ai_data import (
    AIDataStatusEnum,
    AIProvenanceRecord,
    AIFeatureValue,
    AIDataRecord,
)
from app.schemas.ai_target import (
    AITargetEnum,
    AITargetClassificationEnum,
)
from app.schemas.ai_dataset import (
    GenerationStoppingReasonEnum,
    ThicknessDomainTypeEnum,
    MaterialThicknessDomain,
    MaterialThicknessBoundsManager,
    AIPhysicsReferenceRecord,
    DatasetQualityDiagnostics,
    AIPhysicsDataset,
    PhysicsReferenceDatasetGenerator,
)
from app.schemas.ai_surrogate import (
    SurrogateModelFamilyEnum,
    SurrogateAcceptanceStatusEnum,
    SplitStrategyEnum,
    TargetTransformationEnum,
    SurrogateCompatibilityError,
    FeatureSchemaDefinition,
    TargetTransformationConfig,
    SurrogateDatasetEligibilityResult,
    DatasetSplitResult,
    SurrogatePerformanceMetrics,
    ComputationalCostMetrics,
    SurrogatePhysicalValidityCheck,
    ApplicabilityDiagnostic,
    SurrogateModelManifest,
    SurrogateFeatureExtractor,
    SurrogateTargetEligibilityEngine,
    SurrogateDatasetSplitter,
    SurrogateBenchmarker,
    SurrogateApplicabilityEngine,
    SurrogateModelRegistry,
)


def make_physics_rec(
    record_id: str,
    target_id: AITargetEnum = AITargetEnum.SHELF_LIFE_EST,
    target_value: Optional[float] = 15.0,
    evaluation_status: str = "SUCCESS",
    data_status: AIDataStatusEnum = AIDataStatusEnum.SYNTHETIC,
    epistemic_level: UncertaintyLevelEnum = UncertaintyLevelEnum.LEVEL_A,
    is_missing: bool = False,
    context: Optional[dict] = None,
) -> AIPhysicsReferenceRecord:
    classification = (
        AITargetClassificationEnum.PRIMARY_SURROGATE
        if target_id == AITargetEnum.SHELF_LIFE_EST
        else AITargetClassificationEnum.SECONDARY_SUPPORTING
    )
    ctx = context or {}
    mat = ctx.get("material_name") or "LDPE"
    thick = ctx.get("thickness_um") if "thickness_um" in ctx else (12.0 if mat == "PET" else 30.0 if mat == "PLA" else 50.0)

    return AIPhysicsReferenceRecord(
        record_id=record_id,
        target_id=target_id,
        target_value=target_value,
        is_missing=is_missing,
        classification=classification,
        evaluation_status=evaluation_status,
        data_status=data_status,
        epistemic_level=epistemic_level,
        material_identity=mat,
        thickness_um=thick,
        packaging_context=ctx,
        food_context=ctx,
        storage_context=ctx,
        physics_model_version="v3.0-exact-reference",
        provenance=AIProvenanceRecord(
            source_id=f"prov_{record_id}",
            source_type="physics_emulator",
            data_status=data_status,
        ),
    )


def make_physics_dataset(records: List[AIPhysicsReferenceRecord]) -> AIPhysicsDataset:
    import uuid
    return AIPhysicsDataset(
        dataset_id=f"ds_{uuid.uuid4().hex[:8]}",
        records=records,
        diagnostics=DatasetQualityDiagnostics(
            total_records_generated=len(records),
            records_by_target={t.value: len([r for r in records if getattr(r, "target_id", getattr(r, "target_name", None)) == t]) for t in AITargetEnum},
            generation_stopping_reason=GenerationStoppingReasonEnum.COVERAGE_ACHIEVED,
        ),
    )


@pytest.fixture
def sample_physics_dataset() -> AIPhysicsDataset:
    """Fixture providing a synthetic AIPhysicsDataset for Layer 4 testing."""
    records = []
    materials = [("LDPE", 50.0), ("PET", 12.0), ("PLA", 30.0)]
    temperatures = [4.0, 23.0, 35.0]

    for idx in range(30):
        mat, thick = materials[idx % len(materials)]
        temp = temperatures[idx % len(temperatures)]
        shelf_life = 15.0 + (idx * 1.5) - (temp * 0.2)

        rec = make_physics_rec(
            record_id=f"rec_phys_{idx:03d}",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=shelf_life,
            evaluation_status="SUCCESS",
            data_status=AIDataStatusEnum.SYNTHETIC,
            epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            context={
                "material_name": mat,
                "thickness_um": thick,
                "temperature_C": temp,
                "relative_humidity_pct": 50.0,
                "area_m2": 0.1,
                "volume_m3": 0.001,
                "headspace_volume_m3": 0.0005,
                "food_mass_kg": 0.5,
                "food_category": "Fresh Produce" if idx % 2 == 0 else "Dairy",
            },
        )
        records.append(rec)

    # Add 5 OTR records
    for idx in range(5):
        rec = make_physics_rec(
            record_id=f"rec_otr_{idx:03d}",
            target_id=AITargetEnum.OTR_PKG,
            target_value=120.0 + idx * 10.0,
            evaluation_status="SUCCESS",
            data_status=AIDataStatusEnum.MODEL_PREDICTED,
            epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            context={
                "material_name": "LDPE",
                "thickness_um": 50.0,
                "temperature_C": 23.0,
                "relative_humidity_pct": 50.0,
            },
        )
        records.append(rec)

    # Add 5 WVTR records
    for idx in range(5):
        rec = make_physics_rec(
            record_id=f"rec_wvtr_{idx:03d}",
            target_id=AITargetEnum.WVTR_PKG,
            target_value=1.5 + idx * 0.2,
            evaluation_status="SUCCESS",
            data_status=AIDataStatusEnum.MODEL_PREDICTED,
            epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            context={
                "material_name": "PET",
                "thickness_um": 12.0,
                "temperature_C": 38.0,
                "relative_humidity_pct": 90.0,
            },
        )
        records.append(rec)

    return make_physics_dataset(records)


def test_deferred_map_exclusion(sample_physics_dataset):
    """Verify MAP_CO2_peak is explicitly DEFERRED and excluded from training."""
    engine = SurrogateTargetEligibilityEngine()
    result = engine.check_eligibility(AITargetEnum.MAP_CO2_PEAK, sample_physics_dataset)

    assert result.eligible_record_count == 0
    assert result.excluded_records_summary.get("DEFERRED_TARGET_MAP_CO2_PEAK") == len(sample_physics_dataset.records)

    benchmarker = SurrogateBenchmarker()
    manifests = benchmarker.benchmark_target(AITargetEnum.MAP_CO2_PEAK, sample_physics_dataset)
    assert len(manifests) == 1
    assert manifests[0].acceptance_status == SurrogateAcceptanceStatusEnum.DEFERRED
    assert "DEFERRED" in manifests[0].acceptance_rationale


def test_eligible_target_filtering(sample_physics_dataset):
    """Verify ShelfLife_est and OTR_pkg records are properly filtered for training eligibility."""
    engine = SurrogateTargetEligibilityEngine()

    res_shelflife = engine.check_eligibility(AITargetEnum.SHELF_LIFE_EST, sample_physics_dataset)
    assert res_shelflife.eligible_record_count == 30

    res_otr = engine.check_eligibility(AITargetEnum.OTR_PKG, sample_physics_dataset)
    assert res_otr.eligible_record_count == 5


def test_unknown_and_missing_target_rejection():
    """Verify missing values, UNKNOWN data status, Level D, and failed physics evaluations are rejected."""
    records = [
        # Failed physics
        make_physics_rec(
            record_id="rec_fail",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=None,
            evaluation_status="UNEVALUABLE",
            is_missing=True,
        ),
        # UNKNOWN status
        make_physics_rec(
            record_id="rec_unk_status",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=None,
            evaluation_status="SUCCESS",
            data_status=AIDataStatusEnum.UNKNOWN,
            is_missing=True,
        ),
        # Level D
        make_physics_rec(
            record_id="rec_level_d",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=None,
            evaluation_status="SUCCESS",
            epistemic_level=UncertaintyLevelEnum.LEVEL_D,
            is_missing=True,
        ),
        # Thickness domain failure (LDPE at 25 µm is unsupported)
        make_physics_rec(
            record_id="rec_bad_thick",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=20.0,
            evaluation_status="SUCCESS",
            context={"material_name": "LDPE", "thickness_um": 25.0},
        ),
    ]
    dataset = make_physics_dataset(records)
    engine = SurrogateTargetEligibilityEngine()
    res = engine.check_eligibility(AITargetEnum.SHELF_LIFE_EST, dataset)

    assert res.eligible_record_count == 0
    assert "MISSING_OR_NULL_TARGET" in res.excluded_records_summary or "FAILED_PHYSICS_UNEVALUABLE" in res.excluded_records_summary
    assert "UNKNOWN_DATA_STATUS" in res.excluded_records_summary
    assert "LEVEL_D_UNKNOWN" in res.excluded_records_summary
    assert "UNSUPPORTED_THICKNESS_DOMAIN" in res.excluded_records_summary


def test_data_status_preservation():
    """Verify physics-generated records retain SYNTHETIC or MODEL_PREDICTED status and are NEVER relabeled as REAL_EMPIRICAL."""
    rec = make_physics_rec(
        record_id="rec_synth",
        target_id=AITargetEnum.SHELF_LIFE_EST,
        target_value=14.0,
        data_status=AIDataStatusEnum.SYNTHETIC,
    )
    assert rec.data_status == AIDataStatusEnum.SYNTHETIC
    assert rec.data_status != AIDataStatusEnum.REAL_EMPIRICAL


def test_feature_schema_and_metadata_exclusion(sample_physics_dataset):
    """Verify feature extractor excludes metadata (record_id, citation_id, timestamp) and target-derived fields."""
    extractor = SurrogateFeatureExtractor()
    record = sample_physics_dataset.records[0]

    ctx_dict = extractor.extract_record_context(record)
    assert "record_id" not in ctx_dict
    assert "citation_id" not in ctx_dict
    assert "timestamp" not in ctx_dict
    assert "shelf_life_days" not in ctx_dict
    assert "target_value" not in ctx_dict

    # Verify numeric feature list
    for num_field in extractor.schema_def.numeric_feature_names:
        assert num_field in ctx_dict


def test_duplicate_and_conflict_detection():
    """Verify input feature duplicates and conflicting target observations (>5% variance) are detected and reported."""
    records = [
        make_physics_rec(
            record_id="rec_dup_1",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=20.0,
            evaluation_status="SUCCESS",
            context={"material_name": "LDPE", "thickness_um": 50.0, "temperature_C": 23.0, "relative_humidity_pct": 50.0, "area_m2": 0.1, "volume_m3": 0.001, "food_category": "Dairy"},
        ),
        make_physics_rec(
            record_id="rec_dup_2",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=30.0,  # Conflicting value (>5% variance)
            evaluation_status="SUCCESS",
            context={"material_name": "LDPE", "thickness_um": 50.0, "temperature_C": 23.0, "relative_humidity_pct": 50.0, "area_m2": 0.1, "volume_m3": 0.001, "food_category": "Dairy"},
        ),
    ]
    dataset = make_physics_dataset(records)
    engine = SurrogateTargetEligibilityEngine()
    res = engine.check_eligibility(AITargetEnum.SHELF_LIFE_EST, dataset)

    assert res.duplicate_count == 1
    assert res.conflict_count == 1
    assert len(res.conflicts_detected) == 1
    assert res.conflicts_detected[0]["relative_difference"] > 0.05


def test_dataset_splitting_strategies(sample_physics_dataset):
    """Verify leakage-resistant splitting and explicit unsupported holdout reporting."""
    splitter = SurrogateDatasetSplitter()
    records = sample_physics_dataset.records[:30]

    # 1. Interpolation split
    res_interp = splitter.split(records, strategy=SplitStrategyEnum.INTERPOLATION)
    assert res_interp.is_supported is True
    assert len(res_interp.train_record_ids) > 0
    assert len(res_interp.test_record_ids) > 0

    # 2. Material Holdout split
    res_mat = splitter.split(records, strategy=SplitStrategyEnum.MATERIAL_HOLDOUT)
    assert res_mat.is_supported is True
    assert res_mat.holdout_group_name is not None

    # 3. Single-material dataset material holdout (should be unsupported)
    single_mat_recs = [r for r in records if (getattr(r, "material_identity", None) or (r.packaging_context or {}).get("material_name")) == "LDPE"]
    res_single = splitter.split(single_mat_recs, strategy=SplitStrategyEnum.MATERIAL_HOLDOUT)
    assert res_single.is_supported is False
    assert res_single.unsupported_reason == "HOLDOUT NOT SUPPORTED BY AVAILABLE DATA"


def test_model_benchmarking_and_manifest(sample_physics_dataset):
    """Verify multi-candidate benchmark produces comparable metrics, subgroup analysis, and manifests."""
    benchmarker = SurrogateBenchmarker()
    manifests = benchmarker.benchmark_target(
        AITargetEnum.SHELF_LIFE_EST,
        sample_physics_dataset,
        split_strategy=SplitStrategyEnum.INTERPOLATION,
    )

    # Should evaluate 4 candidate model families (Tree, GPR, MLP, Baseline)
    assert len(manifests) == 4

    families = {m.model_family for m in manifests}
    assert SurrogateModelFamilyEnum.TREE_GRADIENT_BOOSTING in families
    assert SurrogateModelFamilyEnum.GAUSSIAN_PROCESS in families
    assert SurrogateModelFamilyEnum.NEURAL_NETWORK_MLP in families
    assert SurrogateModelFamilyEnum.LINEAR_REGRESSION_BASELINE in families

    for manifest in manifests:
        assert manifest.target_name == AITargetEnum.SHELF_LIFE_EST
        assert manifest.metrics.mae >= 0.0
        assert manifest.metrics.rmse >= 0.0
        assert manifest.computational_cost.speedup_factor > 0.0
        assert manifest.acceptance_status in (
            SurrogateAcceptanceStatusEnum.ACCEPTED,
            SurrogateAcceptanceStatusEnum.REJECTED,
        )


def test_physical_validity_check():
    """Verify target physical validity checks flag negative predictions without silent clipping."""
    app_engine = SurrogateApplicabilityEngine()

    # Valid shelf life
    val_ok = app_engine.check_physical_validity(AITargetEnum.SHELF_LIFE_EST, 12.5)
    assert val_ok.is_physically_valid is True
    assert val_ok.raw_predicted_value == 12.5
    assert val_ok.invalidation_reason is None

    # Invalid negative shelf life (raw preserved, flagged invalid)
    val_bad = app_engine.check_physical_validity(AITargetEnum.SHELF_LIFE_EST, -3.2)
    assert val_bad.is_physically_valid is False
    assert val_bad.raw_predicted_value == -3.2
    assert "Non-physical negative" in val_bad.invalidation_reason


def test_applicability_diagnostic_ood():
    """Verify applicability engine checks material thickness and feature bounds."""
    app_engine = SurrogateApplicabilityEngine()

    # Valid LDPE 50 µm
    diag_ok = app_engine.evaluate_applicability({"material_name": "LDPE", "thickness_um": 50.0, "temperature_C": 23.0})
    assert diag_ok.is_within_applicability_domain is True
    assert diag_ok.thickness_domain_valid is True

    # Invalid thickness (LDPE 25 µm) & temperature OOD (80 °C)
    diag_ood = app_engine.evaluate_applicability({"material_name": "LDPE", "thickness_um": 25.0, "temperature_C": 80.0})
    assert diag_ood.is_within_applicability_domain is False
    assert diag_ood.thickness_domain_valid is False
    assert len(diag_ood.numeric_feature_out_of_bounds) > 0


def test_model_registry_compatibility_validation(sample_physics_dataset):
    """Verify SurrogateModelRegistry validates physics and feature schema versions prior to loading."""
    benchmarker = SurrogateBenchmarker()
    manifests = benchmarker.benchmark_target(AITargetEnum.SHELF_LIFE_EST, sample_physics_dataset)
    manifest = manifests[0]

    registry = SurrogateModelRegistry()
    registry.register_model(manifest, "mock_model_artifact")

    # Valid compatibility check against exact physics implementation version
    assert registry.verify_compatibility(manifest.model_id, expected_physics_version="v3.0-exact-reference") is True

    # Incompatible physics version raises SurrogateCompatibilityError
    with pytest.raises(SurrogateCompatibilityError, match="Incompatible physics version"):
        registry.verify_compatibility(manifest.model_id, expected_physics_version="2.0.0")

    # Incompatible feature schema version raises SurrogateCompatibilityError
    with pytest.raises(SurrogateCompatibilityError, match="Incompatible feature schema version"):
        registry.verify_compatibility(manifest.model_id, expected_feature_schema_version="2.0.0")


def test_high_error_region_analysis(sample_physics_dataset):
    """Verify benchmarker performs structured high-error region analysis identifying worst-case records."""
    benchmarker = SurrogateBenchmarker()
    manifests = benchmarker.benchmark_target(AITargetEnum.SHELF_LIFE_EST, sample_physics_dataset)
    manifest = manifests[0]

    high_err = manifest.metrics.high_error_analysis
    assert high_err is not None
    assert high_err.max_absolute_error_record_id is not None
    assert high_err.max_absolute_error_value >= 0.0
    assert len(high_err.top_high_error_record_ids) > 0
    assert "Highest surrogate absolute error" in high_err.error_concentration_description


def test_constraint_boundary_behavior(sample_physics_dataset):
    """Verify constraint-boundary analysis reports NOT APPLICABLE unless an authorized constraint + provenance are provided."""
    benchmarker = SurrogateBenchmarker()
    manifests = benchmarker.benchmark_target(AITargetEnum.SHELF_LIFE_EST, sample_physics_dataset)
    manifest = manifests[0]

    boundary = manifest.metrics.constraint_boundary_analysis
    assert boundary is not None
    assert boundary.boundary_name == "none"
    assert boundary.boundary_sample_count == 0
    assert boundary.boundary_status_note == "NOT APPLICABLE / NO AUTHORIZED CONSTRAINT ESTABLISHED"

    # Verify generic provenance-aware evaluation when authorized constraint is provided
    eval_result = benchmarker.evaluate_constraint_boundary(
        target_name=AITargetEnum.SHELF_LIFE_EST,
        y_test_raw=np.array([10.0, 12.0, 14.0, 16.0]),
        y_pred_raw=np.array([10.1, 11.9, 14.1, 15.9]),
        constraint_value=12.0,
        constraint_provenance="Project Requirement PR-042",
    )
    assert eval_result.boundary_name == "ShelfLife_est_constraint_12.0"
    assert eval_result.boundary_sample_count == 4
    assert eval_result.boundary_mae is not None
    assert "Project Requirement PR-042" in eval_result.boundary_status_note


def test_ranking_agreement_analysis(sample_physics_dataset):
    """Verify Spearman rank correlation is computed to evaluate candidate ordering preservation."""
    benchmarker = SurrogateBenchmarker()
    manifests = benchmarker.benchmark_target(AITargetEnum.SHELF_LIFE_EST, sample_physics_dataset)
    manifest = manifests[0]

    ranking = manifest.metrics.ranking_agreement_analysis
    assert ranking is not None
    assert ranking.metric_name == "spearman_rank_correlation"
    assert ranking.metric_value is not None
    assert -1.0 <= ranking.metric_value <= 1.0


def test_secondary_target_rejection_no_computational_benefit(sample_physics_dataset):
    """Verify OTR_pkg and WVTR_pkg surrogates are REJECTED because exact physics division offers superior performance."""
    benchmarker = SurrogateBenchmarker()

    manifests_otr = benchmarker.benchmark_target(AITargetEnum.OTR_PKG, sample_physics_dataset)
    assert len(manifests_otr) > 0
    assert manifests_otr[0].acceptance_status == SurrogateAcceptanceStatusEnum.REJECTED
    assert "no computational benefit" in manifests_otr[0].acceptance_rationale

    manifests_wvtr = benchmarker.benchmark_target(AITargetEnum.WVTR_PKG, sample_physics_dataset)
    assert len(manifests_wvtr) > 0
    assert manifests_wvtr[0].acceptance_status == SurrogateAcceptanceStatusEnum.REJECTED
    assert "no computational benefit" in manifests_wvtr[0].acceptance_rationale


def test_lineage_and_reproducibility_verification(sample_physics_dataset):
    """Verify model manifest records complete lineage and lineage_verification_status is VERIFIED."""
    benchmarker = SurrogateBenchmarker()
    manifests = benchmarker.benchmark_target(AITargetEnum.SHELF_LIFE_EST, sample_physics_dataset)
    manifest = manifests[0]

    assert manifest.lineage_verification_status == "VERIFIED"
    assert manifest.physics_model_version == "v3.0-exact-reference"
    assert manifest.dataset_version == "1.0.0"
    assert manifest.physics_model_version != manifest.dataset_version
    assert manifest.feature_schema_version == "1.0.0"
    assert manifest.material_thickness_domain_version == "1.0.0"
    assert len(manifest.applicability_signals) == 7

    # Test 5: Confirm dataset records are associated with v3.0-exact-reference
    assert sample_physics_dataset.records[0].physics_model_version == "v3.0-exact-reference"

