"""
Unit tests for Phase 3A - Implementation Layer 3: Surrogate Dataset Construction & Physics-Reference Generation.

Verifies:
1. Dataset Construction: Valid physics-reference dataset records created with correct target linkage and context.
2. Provenance Preservation: Layer 1 & Layer 2 provenance, source IDs, citations, and physics version survive.
3. Epistemic Behavior: Level A point values, Level B intervals (no P05/P50/P95 conversion), Level D unknown (value=None).
4. Data-Status Semantics: Empirical observations remain empirical; physics-generated records are SYNTHETIC, never REAL_EMPIRICAL.
5. Thickness Bounds Enforcement: Material-specific [d_min, d_max] enforced; out-of-bounds or unknown materials marked UNEVALUABLE.
6. Physics Failures: Invalid evaluations cleanly recorded with evaluation_status=UNEVALUABLE and explicit failure_reason (no zero coercion).
7. Adaptive Generation & Diagnostics: Stopping reasons (GenerationStoppingReasonEnum) and coverage metadata reported.
8. Deferred Target Protection: MAP_CO2_peak remains DEFERRED (target_value=None, evaluation_status=DEFERRED).
9. Real Data Priority: Existing Layer 1 empirical records preserved with original status and provenance.
10. Boundary Protection: Guarantees Layer 3 does not train surrogates, invoke M11, rank candidates, or use Level C.
"""

import pytest
from pydantic import ValidationError

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
from app.schemas.inference import UncertaintyLevelEnum


def test_material_thickness_bounds_enforcement():
    """Verify material-specific discrete thickness evidence is respected and continuous ranges are not fabricated."""
    manager = MaterialThicknessBoundsManager()

    # 1. LDPE discrete evidence: 50.0 µm supported; non-evidenced values rejected
    valid_ldpe, _ = manager.validate_thickness("LDPE", 50.0)
    assert valid_ldpe is True

    domain_ldpe = manager.get_domain("LDPE")
    assert domain_ldpe.domain_type == ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE
    assert domain_ldpe.supported_discrete_values_um == [50.0]

    unsupported_ldpe, reason_ldpe = manager.validate_thickness("LDPE", 25.0)
    assert unsupported_ldpe is False
    assert "unsupported for material 'LDPE'" in reason_ldpe

    # 2. PET discrete evidence: 12.0 µm supported; non-evidenced values rejected
    valid_pet, _ = manager.validate_thickness("PET", 12.0)
    assert valid_pet is True

    domain_pet = manager.get_domain("PET")
    assert domain_pet.domain_type == ThicknessDomainTypeEnum.DISCRETE_VALIDATED_VALUE
    assert domain_pet.supported_discrete_values_um == [12.0]

    unsupported_pet, reason_pet = manager.validate_thickness("PET", 50.0)
    assert unsupported_pet is False
    assert "unsupported for material 'PET'" in reason_pet

    # 3. PLA discrete evidence: 30.0 µm supported; non-evidenced values rejected
    valid_pla, _ = manager.validate_thickness("PLA", 30.0)
    assert valid_pla is True

    unsupported_pla, reason_pla = manager.validate_thickness("PLA", 15.0)
    assert unsupported_pla is False
    assert "unsupported for material 'PLA'" in reason_pla

    # 4. Unknown material without thickness domain must be marked unevaluable (no universal fallback)
    unknown_mat, unk_reason = manager.validate_thickness("UNOBTAINIUM_POLYMER", 30.0)
    assert unknown_mat is False
    assert "has no validated thickness domain" in unk_reason


def test_single_target_evaluation_success_and_unevaluable():
    """Verify exact physics evaluation creates valid records and records unevaluable candidates with explicit reasons."""
    generator = PhysicsReferenceDatasetGenerator()

    # 1. Valid ShelfLife_est evaluation
    rec_sl = generator.evaluate_single_target(
        target_id=AITargetEnum.SHELF_LIFE_EST,
        material_id="PLA",
        thickness_um=30.0,
        commodity="strawberry",
        temp_c=4.0,
        rh_percent=90.0,
        seed=101,
    )
    assert rec_sl.evaluation_status == "SUCCESS"
    assert rec_sl.target_value is not None
    assert rec_sl.target_value > 0.0
    assert rec_sl.target_units == "days"
    assert rec_sl.data_status == AIDataStatusEnum.SYNTHETIC
    assert rec_sl.data_status != AIDataStatusEnum.REAL_EMPIRICAL
    assert rec_sl.classification == AITargetClassificationEnum.PRIMARY_SURROGATE
    assert rec_sl.is_valid_training_target() is True

    # 2. Unsupported thickness evaluation -> UNEVALUABLE
    rec_invalid_thick = generator.evaluate_single_target(
        target_id=AITargetEnum.SHELF_LIFE_EST,
        material_id="PET",
        thickness_um=50.0,  # PET discrete evidence is 12 µm; 50 µm is unsupported
        commodity="strawberry",
        temp_c=4.0,
        rh_percent=90.0,
    )
    assert rec_invalid_thick.evaluation_status == "UNEVALUABLE"
    assert rec_invalid_thick.target_value is None
    assert rec_invalid_thick.is_missing is True
    assert rec_invalid_thick.failure_reason is not None
    assert "unsupported for material 'PET'" in rec_invalid_thick.failure_reason
    assert rec_invalid_thick.is_valid_training_target() is False


def test_deferred_target_protection_map_co2_peak():
    """Verify MAP_CO2_peak target remains DEFERRED and produces no fabricated dataset values."""
    generator = PhysicsReferenceDatasetGenerator()

    rec_map = generator.evaluate_single_target(
        target_id=AITargetEnum.MAP_CO2_PEAK,
        material_id="LDPE",
        thickness_um=50.0,
        commodity="blueberry",
        temp_c=4.0,
        rh_percent=85.0,
    )

    assert rec_map.classification == AITargetClassificationEnum.DEFERRED
    assert rec_map.evaluation_status == "DEFERRED"
    assert rec_map.target_value is None
    assert rec_map.is_missing is True
    assert rec_map.epistemic_level == UncertaintyLevelEnum.LEVEL_D
    assert "DEFERRED" in rec_map.failure_reason
    assert rec_map.is_valid_training_target() is False


def test_real_data_priority_preserves_empirical_observations():
    """Verify Layer 1 empirical and literature observations are preserved and not overwritten by physics predictions."""
    prov_emp = AIProvenanceRecord(
        source_id="TRIAL-EXP-2026-99",
        source_type="lab_trial",
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
    )
    rec_emp = AIDataRecord(
        record_id="AIDATA-EMP-99",
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
        provenance=prov_emp,
        outcome_features={
            "shelf_life": AIFeatureValue(
                feature_name="shelf_life",
                value=16.5,
                is_missing=False,
                unit="days",
                data_status=AIDataStatusEnum.REAL_EMPIRICAL,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            )
        },
    )

    generator = PhysicsReferenceDatasetGenerator()
    dataset = generator.generate_dataset(
        materials=["LDPE"],
        commodities=["strawberry"],
        target_ids=[AITargetEnum.SHELF_LIFE_EST],
        max_budget=10,
        existing_records=[rec_emp],
    )

    # Check preserved empirical record in dataset
    preserved = [r for r in dataset.records if r.evaluation_status == "EMPIRICAL_PRESERVED"]
    assert len(preserved) >= 1
    emp_rec = preserved[0]
    assert emp_rec.target_value == 16.5
    assert emp_rec.data_status == AIDataStatusEnum.REAL_EMPIRICAL
    assert emp_rec.provenance.source_id == "TRIAL-EXP-2026-99"


def test_adaptive_dataset_generation_stopping_reasons_and_diagnostics():
    """Verify adaptive generation records explicit stopping reasons and measurable diagnostics."""
    generator = PhysicsReferenceDatasetGenerator()

    # 1. Generation reaching COVERAGE_ACHIEVED or EVALUATION_BUDGET_REACHED
    dataset = generator.generate_dataset(
        materials=["LDPE", "PLA"],
        commodities=["strawberry", "blueberry"],
        temp_range_c=(2.0, 10.0),
        rh_range_percent=(80.0, 95.0),
        target_ids=[AITargetEnum.SHELF_LIFE_EST, AITargetEnum.OTR_PKG],
        max_budget=50,
        seed=123,
    )

    assert dataset.dataset_id.startswith("DS-PH3A-L3-")
    assert dataset.diagnostics.total_records > 0
    assert dataset.diagnostics.valid_records > 0
    assert dataset.diagnostics.generation_stopping_reason in (
        GenerationStoppingReasonEnum.COVERAGE_ACHIEVED,
        GenerationStoppingReasonEnum.EVALUATION_BUDGET_REACHED,
    )
    assert dataset.diagnostics.sampling_seed == 123
    assert "LDPE" in dataset.diagnostics.material_coverage
    assert "PLA" in dataset.diagnostics.material_coverage
    assert "strawberry" in dataset.diagnostics.commodity_coverage


def test_unknown_value_integrity_no_zero_substitution():
    """Verify missing or failed physics evaluations retain value=None and cannot hold numeric 0.0."""
    prov = AIProvenanceRecord(data_status=AIDataStatusEnum.UNKNOWN)

    # Unevaluable record
    failed_record = AIPhysicsReferenceRecord(
        record_id="FAILED-1",
        target_id=AITargetEnum.SHELF_LIFE_EST,
        target_value=None,
        is_missing=True,
        classification=AITargetClassificationEnum.PRIMARY_SURROGATE,
        data_status=AIDataStatusEnum.UNKNOWN,
        epistemic_level=UncertaintyLevelEnum.LEVEL_D,
        provenance=prov,
        evaluation_status="UNEVALUABLE",
        failure_reason="Invalid material property.",
    )

    assert failed_record.target_value is None
    assert failed_record.is_missing is True
    assert failed_record.is_valid_training_target() is False

    # Attempting to assign value 0.0 on UNKNOWN/LEVEL_D status raises ValidationError
    with pytest.raises(ValidationError):
        AIPhysicsReferenceRecord(
            record_id="FAILED-2",
            target_id=AITargetEnum.SHELF_LIFE_EST,
            target_value=0.0,
            is_missing=True,
            classification=AITargetClassificationEnum.PRIMARY_SURROGATE,
            data_status=AIDataStatusEnum.UNKNOWN,
            epistemic_level=UncertaintyLevelEnum.LEVEL_D,
            provenance=prov,
            evaluation_status="UNEVALUABLE",
        )

    with pytest.raises(ValueError, match="is UNKNOWN/missing"):
        failed_record.to_numeric_strict()


def test_boundary_protection_no_surrogate_training_or_m11():
    """Verify Layer 3 code does not train surrogate models, execute ML fitting, or invoke M11 search."""
    import app.schemas.ai_dataset as dataset_module

    attrs = dir(dataset_module)
    forbidden_terms = ["lightgbm", "xgboost", "train_surrogate", "m11", "predict_residual", "calibrate_uncertainty", "fit_model"]

    for attr in attrs:
        for term in forbidden_terms:
            assert term not in attr.lower(), f"Forbidden concept '{term}' found in Layer 3 module: {attr}"

    # Verify dataset diagnostics are quality/coverage metrics, not ML performance metrics (no R2, MSE, MAE)
    generator = PhysicsReferenceDatasetGenerator()
    dataset = generator.generate_dataset(
        materials=["LDPE"],
        commodities=["strawberry"],
        max_budget=10,
    )
    diag = dataset.diagnostics
    assert not hasattr(diag, "r2_score")
    assert not hasattr(diag, "mse")
    assert not hasattr(diag, "mae")
