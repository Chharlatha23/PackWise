"""
Unit tests for Phase 3A - Implementation Layer 1: AI Data & Provenance Foundation.

Verifies:
- All 8 approved data statuses can be represented and round-tripped.
- Provenance, status, epistemic level, and context survive serialization.
- Unknown integrity rule: UNKNOWN / LEVEL_D / missing features cannot silently become numeric zero.
- Real vs. model-generated data separation.
- Food-only vs. packaging-only vs. joint-observation distinction.
- Phase 2 epistemic compatibility (Level D/A/B semantics intact).
"""

import pytest
import json
from pydantic import ValidationError

from app.schemas.ai_data import (
    AIDataStatusEnum,
    AIProvenanceRecord,
    AIFeatureValue,
    AIDataRecord,
    from_food_evidence,
    from_material_evidence,
    from_inferred_profile,
)
from app.schemas.inference import UncertaintyLevelEnum, PropertyInferenceProfile, InferredProperty, PropertyStatusEnum
from app.schemas.food_evidence import FoodEvidenceRecord
from app.schemas.material_evidence import MaterialPropertyEvidence
from app.schemas.vocabularies import FoodProperty, PackagingProperty, SourceType, ProductForm


def test_status_taxonomy_all_eight_supported():
    """Verify all 8 locked data statuses are present in AIDataStatusEnum and round-trip cleanly."""
    expected_statuses = [
        "REAL_EMPIRICAL",
        "REAL_LITERATURE",
        "FOOD_ONLY",
        "PACKAGING_ONLY",
        "MODEL_PREDICTED",
        "SYNTHETIC",
        "REAL_PLUS_MODEL",
        "UNKNOWN",
    ]
    assert len(AIDataStatusEnum) == 8
    for status_str in expected_statuses:
        status_enum = AIDataStatusEnum(status_str)
        assert status_enum.value == status_str

        # Serialization test
        prov = AIProvenanceRecord(
            source_id="TEST-001",
            data_status=status_enum,
            epistemic_level=UncertaintyLevelEnum.LEVEL_A,
        )
        json_data = json.loads(prov.json())
        assert json_data["data_status"] == status_str

        # Deserialization test
        reconstructed = AIProvenanceRecord.parse_raw(prov.json())
        assert reconstructed.data_status == status_enum


def test_provenance_preservation_and_serialization():
    """Verify provenance metadata survives serialization and context transformations."""
    prov = AIProvenanceRecord(
        source_id="DOI-10.1016/j.foodchem.2025.1001",
        source_type="journal_paper",
        data_status=AIDataStatusEnum.REAL_LITERATURE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_B,
        citation_or_doi="Smith et al., 2025. Food Chem 400:1001",
        food_context={"commodity": "strawberry", "temperature_c": 4.0},
        packaging_context={"material_name": "PLA_MONOLAYER", "thickness_um": 30.0},
        storage_context={"temperature_c": 4.0, "rh_percent": 90.0, "duration_days": 14},
    )

    rec = AIDataRecord(
        record_id="REC-2026-001",
        data_status=AIDataStatusEnum.REAL_LITERATURE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_B,
        provenance=prov,
        food_features={
            "respiration_rate": AIFeatureValue(
                feature_name="respiration_rate",
                value=25.4,
                is_missing=False,
                unit="mg CO2/kg/hr",
                data_status=AIDataStatusEnum.REAL_LITERATURE,
                epistemic_level=UncertaintyLevelEnum.LEVEL_B,
                evidence_interval=(20.0, 30.0),
            )
        },
    )

    serialized = rec.json()
    deserialized = AIDataRecord.parse_raw(serialized)

    assert deserialized.provenance.source_id == "DOI-10.1016/j.foodchem.2025.1001"
    assert deserialized.provenance.data_status == AIDataStatusEnum.REAL_LITERATURE
    assert deserialized.provenance.food_context["commodity"] == "strawberry"
    assert deserialized.food_features["respiration_rate"].evidence_interval == (20.0, 30.0)


def test_unknown_integrity_prevents_numeric_zero_coercion():
    """Verify UNKNOWN / LEVEL_D / missing features cannot hold a numeric value or be converted to zero silently."""
    # 1. Default UNKNOWN feature has value=None and is_missing=True
    unknown_feat = AIFeatureValue(
        feature_name="oxygen_sensitivity",
        data_status=AIDataStatusEnum.UNKNOWN,
        epistemic_level=UncertaintyLevelEnum.LEVEL_D,
    )
    assert unknown_feat.value is None
    assert unknown_feat.is_missing is True

    # 2. Attempting to assign numeric 0.0 when status is UNKNOWN must raise ValueError
    with pytest.raises(ValidationError):
        AIFeatureValue(
            feature_name="oxygen_sensitivity",
            value=0.0,
            is_missing=True,
            data_status=AIDataStatusEnum.UNKNOWN,
            epistemic_level=UncertaintyLevelEnum.LEVEL_D,
        )

    with pytest.raises(ValidationError):
        AIFeatureValue(
            feature_name="oxygen_sensitivity",
            value=0.0,
            is_missing=False,
            data_status=AIDataStatusEnum.UNKNOWN,
            epistemic_level=UncertaintyLevelEnum.LEVEL_D,
        )

    # 3. to_numeric_strict() must raise ValueError for missing feature
    with pytest.raises(ValueError, match="Cannot convert to numeric"):
        unknown_feat.to_numeric_strict()

    # 4. to_numeric_with_mask() returns explicit boolean mask (False, None)
    has_mask, val = unknown_feat.to_numeric_with_mask()
    assert has_mask is False
    assert val is None


def test_real_vs_model_generated_data_separation():
    """Verify distinction between real empirical evidence, literature evidence, and model/synthetic data."""
    real_rec = AIDataRecord(
        record_id="REAL-1",
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
        provenance=AIProvenanceRecord(data_status=AIDataStatusEnum.REAL_EMPIRICAL),
    )
    assert real_rec.is_real_empirical is True
    assert real_rec.is_real_literature is False
    assert real_rec.is_real_evidence is True
    assert real_rec.is_model_generated is False

    lit_rec = AIDataRecord(
        record_id="LIT-1",
        data_status=AIDataStatusEnum.REAL_LITERATURE,
        epistemic_level=UncertaintyLevelEnum.LEVEL_B,
        provenance=AIProvenanceRecord(data_status=AIDataStatusEnum.REAL_LITERATURE),
    )
    assert lit_rec.is_real_empirical is False
    assert lit_rec.is_real_literature is True
    assert lit_rec.is_real_evidence is True
    assert lit_rec.is_model_generated is False

    synth_rec = AIDataRecord(
        record_id="SYNTH-1",
        data_status=AIDataStatusEnum.SYNTHETIC,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
        provenance=AIProvenanceRecord(data_status=AIDataStatusEnum.SYNTHETIC, physics_model_version="v1.4"),
    )
    assert synth_rec.is_real_empirical is False
    assert synth_rec.is_real_literature is False
    assert synth_rec.is_real_evidence is False
    assert synth_rec.is_model_generated is True

    model_rec = AIDataRecord(
        record_id="MODEL-1",
        data_status=AIDataStatusEnum.MODEL_PREDICTED,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
        provenance=AIProvenanceRecord(data_status=AIDataStatusEnum.MODEL_PREDICTED),
    )
    assert model_rec.is_real_empirical is False
    assert model_rec.is_real_literature is False
    assert model_rec.is_real_evidence is False
    assert model_rec.is_model_generated is True


def test_food_packaging_and_joint_observation_distinction():
    """Verify single-domain records (FOOD_ONLY, PACKAGING_ONLY) are never confused with genuine joint observations."""
    food_feat = AIFeatureValue(
        feature_name="respiration_rate",
        value=12.0,
        is_missing=False,
        data_status=AIDataStatusEnum.FOOD_ONLY,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
    )
    pkg_feat = AIFeatureValue(
        feature_name="otr",
        value=500.0,
        is_missing=False,
        data_status=AIDataStatusEnum.PACKAGING_ONLY,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
    )
    outcome_feat = AIFeatureValue(
        feature_name="observed_shelf_life",
        value=14.0,
        is_missing=False,
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A,
    )

    # 1. Food-only record
    food_rec = AIDataRecord(
        record_id="FOOD-REC-1",
        data_status=AIDataStatusEnum.FOOD_ONLY,
        provenance=AIProvenanceRecord(data_status=AIDataStatusEnum.FOOD_ONLY),
        food_features={"respiration_rate": food_feat},
    )
    assert food_rec.is_food_only is True
    assert food_rec.is_packaging_only is False
    assert food_rec.is_joint_observation is False

    # 2. Packaging-only record
    pkg_rec = AIDataRecord(
        record_id="PKG-REC-1",
        data_status=AIDataStatusEnum.PACKAGING_ONLY,
        provenance=AIProvenanceRecord(data_status=AIDataStatusEnum.PACKAGING_ONLY),
        packaging_features={"otr": pkg_feat},
    )
    assert pkg_rec.is_food_only is False
    assert pkg_rec.is_packaging_only is True
    assert pkg_rec.is_joint_observation is False

    # 3. Genuine Joint Empirical Record
    joint_rec = AIDataRecord(
        record_id="JOINT-REC-1",
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        provenance=AIProvenanceRecord(data_status=AIDataStatusEnum.REAL_EMPIRICAL),
        food_features={"respiration_rate": food_feat},
        packaging_features={"otr": pkg_feat},
        outcome_features={"observed_shelf_life": outcome_feat},
    )
    assert joint_rec.is_food_only is False
    assert joint_rec.is_packaging_only is False
    assert joint_rec.is_joint_observation is True


def test_converter_utilities_preserve_provenance():
    """Verify helper converters create valid AIDataRecord objects with proper provenance and epistemic levels."""
    # 1. Food evidence conversion
    fe_record = FoodEvidenceRecord(
        commodity="blueberry",
        scientific_name="Vaccinium corymbosum",
        product_form="whole",
        property="respiration_rate",
        value=35.0,
        unit="mg CO2/kg/hr",
        temperature=5.0,
        source_type=SourceType.JOURNAL_ARTICLE.value,
        source_title="Test Citation 2026",
    )
    ai_food = from_food_evidence(fe_record)
    assert ai_food.data_status == AIDataStatusEnum.FOOD_ONLY
    assert ai_food.is_food_only is True
    assert ai_food.food_features["respiration_rate"].value == 35.0
    assert ai_food.provenance.citation_or_doi == "Test Citation 2026"

    # 2. Material evidence conversion
    me_record = MaterialPropertyEvidence(
        property="oxygen_transmission_rate",
        value=1500.0,
        minimum_value=1200.0,
        maximum_value=1800.0,
        unit="cm3/(m2*day*atm)",
        source_type=SourceType.LABORATORY_MEASUREMENT.value,
        source_title="Datasheet LDPE 2026",
    )
    ai_pkg = from_material_evidence(me_record)
    assert ai_pkg.data_status == AIDataStatusEnum.PACKAGING_ONLY
    assert ai_pkg.is_packaging_only is True
    assert ai_pkg.packaging_features["oxygen_transmission_rate"].epistemic_level == UncertaintyLevelEnum.LEVEL_B
    assert ai_pkg.packaging_features["oxygen_transmission_rate"].evidence_interval == (1200.0, 1800.0)

    # 3. Property inference profile conversion
    profile = PropertyInferenceProfile(
        commodity="apple",
        storage_temperature_c=2.0,
        properties={
            "respiration_rate": InferredProperty(
                property_name="respiration_rate",
                value=15.0,
                unit="mg CO2/kg/hr",
                status=PropertyStatusEnum.inferred,
                uncertainty_level=UncertaintyLevelEnum.LEVEL_B,
                evidence_interval=(10.0, 20.0),
                confidence=0.85,
            )
        },
    )
    ai_inferred = from_inferred_profile(profile)
    assert ai_inferred.data_status == AIDataStatusEnum.FOOD_ONLY
    assert ai_inferred.food_features["respiration_rate"].confidence_heuristic == 0.85
    assert ai_inferred.food_features["respiration_rate"].evidence_interval == (10.0, 20.0)
    assert ai_inferred.validate_unknown_integrity() is True
