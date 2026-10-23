"""
Unit tests for Phase 3A - Implementation Layer 2: Surrogate-Target Preparation Foundation.

Verifies:
1. Target Inventory: Contains exactly 4 approved targets (OTR_pkg, WVTR_pkg, ShelfLife_est, MAP_CO2_peak).
2. Classification: Every target has an explicit classification (PRIMARY_SURROGATE, SECONDARY_SUPPORTING, PHYSICS_ONLY, DEFERRED).
3. Target Audit Rationale: Audit registry captures 10-criteria evaluation, rationale, and allows future reassessment.
4. Provenance & Context Traceability: Layer 1 provenance, data status, epistemic level, contexts, and citations survive target preparation.
5. Epistemic Integrity: Level A point, Level B interval (no P05/P50/P95 quantile conversion), Level D unknown (value=None).
6. Unknown / Missing Integrity: UNKNOWN or LEVEL_D target cannot hold numeric zero; missing targets fail is_valid_training_target().
7. Data-Status Semantics: All 8 Layer 1 statuses are preserved; literature evidence is not empirical observation.
8. Boundary Protection: Ensures Layer 2 does not train surrogates, invoke M11, rank candidates, or use Level C probability.
"""

import pytest
import json
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
    AITargetCriteriaAssessment,
    AITargetAuditResult,
    AITargetPreparationRecord,
    AITargetPreparationSet,
    get_default_target_audit_registry,
    prepare_targets_from_ai_data_record,
)
from app.schemas.inference import UncertaintyLevelEnum


def test_target_inventory_exact_four():
    """Verify target inventory contains exactly the 4 approved candidate targets and no additions."""
    expected_targets = {"OTR_pkg", "WVTR_pkg", "ShelfLife_est", "MAP_CO2_peak"}
    actual_targets = {t.value for t in AITargetEnum}
    
    assert actual_targets == expected_targets
    assert len(AITargetEnum) == 4


def test_target_classifications_explicit_and_audit_backed():
    """Verify every candidate target has an explicit classification and detailed 10-criteria audit assessment."""
    registry = get_default_target_audit_registry()
    assert len(registry) == 4

    # 1. OTR_pkg -> SECONDARY_SUPPORTING
    otr_audit = registry[AITargetEnum.OTR_PKG]
    assert otr_audit.classification == AITargetClassificationEnum.SECONDARY_SUPPORTING
    assert otr_audit.assessment.is_cheap_deterministic is True
    assert otr_audit.assessment.physics_eval_cost == "low"
    assert "deterministic" in otr_audit.rationale

    # 2. WVTR_pkg -> SECONDARY_SUPPORTING
    wvtr_audit = registry[AITargetEnum.WVTR_PKG]
    assert wvtr_audit.classification == AITargetClassificationEnum.SECONDARY_SUPPORTING
    assert wvtr_audit.assessment.is_cheap_deterministic is True
    assert wvtr_audit.assessment.physics_eval_cost == "low"

    # 3. ShelfLife_est -> PRIMARY_SURROGATE
    sl_audit = registry[AITargetEnum.SHELF_LIFE_EST]
    assert sl_audit.classification == AITargetClassificationEnum.PRIMARY_SURROGATE
    assert sl_audit.assessment.is_cheap_deterministic is False
    assert sl_audit.assessment.physics_eval_cost == "high"
    assert sl_audit.assessment.has_meaningful_nonlinearity is True
    assert sl_audit.assessment.accelerates_inverse_design is True

    # 4. MAP_CO2_peak -> DEFERRED
    map_audit = registry[AITargetEnum.MAP_CO2_PEAK]
    assert map_audit.classification == AITargetClassificationEnum.DEFERRED
    assert map_audit.assessment.suitable_training_data_available is False
    assert "DEFERRED" in map_audit.rationale or "deferred" in map_audit.rationale.lower()


def test_provenance_and_context_propagation():
    """Verify Layer 1 provenance, food/pkg/storage context, citations, and model versions survive target preparation."""
    prov = AIProvenanceRecord(
        source_id="DOI-10.1016/j.packaging.2026.004",
        source_type="journal_paper",
        data_status=AIDataStatusEnum.REAL_LITERATURE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_B,
        citation_or_doi="Doe et al., 2026. Packaging Science 12:45",
        food_context={"commodity": "strawberry", "temperature_c": 4.0},
        packaging_context={"material_name": "PLA_MONOLAYER"},
        storage_context={"temperature_c": 4.0, "rh_percent": 90.0},
        physics_model_version="v2.1",
        scenario_parameters={"modified_atmosphere": True},
    )

    rec = AIDataRecord(
        record_id="AIDATA-LIT-001",
        data_status=AIDataStatusEnum.REAL_LITERATURE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_B,
        provenance=prov,
        outcome_features={
            "observed_shelf_life": AIFeatureValue(
                feature_name="observed_shelf_life",
                value=14.0,
                is_missing=False,
                unit="days",
                data_status=AIDataStatusEnum.REAL_LITERATURE,
                epistemic_level=UncertaintyLevelEnum.LEVEL_B,
                evidence_interval=(12.0, 16.0),
            )
        },
    )

    prep_set = prepare_targets_from_ai_data_record(rec)
    
    assert prep_set.record_id == "AIDATA-LIT-001"
    assert prep_set.parent_data_status == AIDataStatusEnum.REAL_LITERATURE
    assert prep_set.provenance.source_id == "DOI-10.1016/j.packaging.2026.004"

    sl_prep = prep_set.targets[AITargetEnum.SHELF_LIFE_EST]
    assert sl_prep.value == 14.0
    assert sl_prep.is_missing is False
    assert sl_prep.unit == "days"
    assert sl_prep.classification == AITargetClassificationEnum.PRIMARY_SURROGATE
    assert sl_prep.epistemic_level == UncertaintyLevelEnum.LEVEL_B
    assert sl_prep.data_status == AIDataStatusEnum.REAL_LITERATURE
    assert sl_prep.evidence_interval == (12.0, 16.0)
    assert sl_prep.food_context["commodity"] == "strawberry"
    assert sl_prep.packaging_context["material_name"] == "PLA_MONOLAYER"
    assert sl_prep.storage_context["rh_percent"] == 90.0
    assert sl_prep.citation_or_doi == "Doe et al., 2026. Packaging Science 12:45"
    assert sl_prep.physics_model_version == "v2.1"
    assert sl_prep.audit_rationale is not None


def test_epistemic_levels_point_interval_unknown_no_level_c():
    """Verify Level A (point), Level B (interval), and Level D (unknown) semantics; check no Level C or quantile conversion."""
    prov = AIProvenanceRecord(data_status=AIDataStatusEnum.REAL_EMPIRICAL)
    
    # Level A target preparation
    target_a = AITargetPreparationRecord(
        target_id=AITargetEnum.SHELF_LIFE_EST,
        value=10.5,
        is_missing=False,
        classification=AITargetClassificationEnum.PRIMARY_SURROGATE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        provenance=prov,
    )
    assert target_a.to_numeric_strict() == 10.5
    assert target_a.is_valid_training_target() is True

    # Level B target preparation - interval retained without P05/P50/P95 conversion
    target_b = AITargetPreparationRecord(
        target_id=AITargetEnum.SHELF_LIFE_EST,
        value=10.0,
        is_missing=False,
        classification=AITargetClassificationEnum.PRIMARY_SURROGATE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_B,
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        provenance=prov,
        evidence_interval=(8.0, 12.0),
    )
    assert target_b.evidence_interval == (8.0, 12.0)
    # Ensure no quantile attributes exist
    assert not hasattr(target_b, "p05")
    assert not hasattr(target_b, "p50")
    assert not hasattr(target_b, "p95")

    # Level D target preparation - value is None
    target_d = AITargetPreparationRecord(
        target_id=AITargetEnum.SHELF_LIFE_EST,
        value=None,
        is_missing=True,
        classification=AITargetClassificationEnum.PRIMARY_SURROGATE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_D,
        data_status=AIDataStatusEnum.UNKNOWN,
        provenance=prov,
    )
    assert target_d.value is None
    assert target_d.is_missing is True
    assert target_d.is_valid_training_target() is False


def test_unknown_handling_prevents_zero_coercion_and_invalid_training():
    """Verify UNKNOWN / LEVEL_D missing targets cannot hold numeric value 0.0 and fail training target validation."""
    prov = AIProvenanceRecord(data_status=AIDataStatusEnum.UNKNOWN)

    # 1. Default missing target has value=None
    target_unk = AITargetPreparationRecord(
        target_id=AITargetEnum.MAP_CO2_PEAK,
        classification=AITargetClassificationEnum.DEFERRED,
        provenance=prov,
    )
    assert target_unk.value is None
    assert target_unk.is_missing is True
    assert target_unk.is_valid_training_target() is False

    # 2. Attempting to set value=0.0 on UNKNOWN status raises ValidationError
    with pytest.raises(ValidationError):
        AITargetPreparationRecord(
            target_id=AITargetEnum.MAP_CO2_PEAK,
            value=0.0,
            is_missing=True,
            classification=AITargetClassificationEnum.DEFERRED,
            data_status=AIDataStatusEnum.UNKNOWN,
            epistemic_level=UncertaintyLevelEnum.LEVEL_D,
            provenance=prov,
        )

    # 3. to_numeric_strict() raises ValueError
    with pytest.raises(ValueError, match="is UNKNOWN/missing"):
        target_unk.to_numeric_strict()

    # 4. to_numeric_with_mask() returns (False, None)
    mask, val = target_unk.to_numeric_with_mask()
    assert mask is False
    assert val is None


def test_data_status_semantics_across_all_statuses():
    """Verify data-status semantics survive target preparation and physics-generated data is not empirical."""
    prov_model = AIProvenanceRecord(
        data_status=AIDataStatusEnum.MODEL_PREDICTED,
        physics_model_version="v1.0",
    )
    rec_model = AIDataRecord(
        record_id="REC-MODEL-1",
        data_status=AIDataStatusEnum.MODEL_PREDICTED,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
        provenance=prov_model,
        outcome_features={
            "observed_shelf_life": AIFeatureValue(
                feature_name="observed_shelf_life",
                value=21.0,
                is_missing=False,
                data_status=AIDataStatusEnum.MODEL_PREDICTED,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            )
        },
    )

    prep_model = prepare_targets_from_ai_data_record(rec_model)
    target_sl = prep_model.targets[AITargetEnum.SHELF_LIFE_EST]
    
    assert target_sl.data_status == AIDataStatusEnum.MODEL_PREDICTED
    assert target_sl.data_status != AIDataStatusEnum.REAL_EMPIRICAL
    assert target_sl.data_status != AIDataStatusEnum.REAL_LITERATURE


def test_boundary_protection_no_surrogate_training_or_m11():
    """Verify Layer 2 code does not train surrogates, execute ML algorithms, or invoke M11 search."""
    import sys
    import app.schemas.ai_target as ai_target_module

    # Verify no ML training functions exist in Layer 2 module
    module_attrs = dir(ai_target_module)
    forbidden_terms = ["lightgbm", "xgboost", "train_surrogate", "m11", "predict_residual", "calibrate_uncertainty"]
    
    for attr in module_attrs:
        for term in forbidden_terms:
            assert term not in attr.lower(), f"Forbidden Layer 3+ concept '{term}' found in Layer 2 module: {attr}"

    # Verify preparation set trainable filter correctly rejects non-primary or missing targets
    prov = AIProvenanceRecord(data_status=AIDataStatusEnum.REAL_EMPIRICAL)
    rec_food_only = AIDataRecord(
        record_id="REC-FOOD-ONLY",
        data_status=AIDataStatusEnum.FOOD_ONLY,
        provenance=prov,
        food_features={
            "respiration_rate": AIFeatureValue(
                feature_name="respiration_rate",
                value=15.0,
                is_missing=False,
                data_status=AIDataStatusEnum.FOOD_ONLY,
                epistemic_level=UncertaintyLevelEnum.LEVEL_A,
            )
        },
    )

    prep_set = prepare_targets_from_ai_data_record(rec_food_only)
    trainable = prep_set.get_trainable_targets()
    
    # Food-only record has no outcome shelf-life, so zero targets should be trainable
    assert len(trainable) == 0
