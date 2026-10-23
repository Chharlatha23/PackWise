"""
Phase 2 Conservative Uncertainty Model Integration Tests.

Validates explicit D/A/B uncertainty level classifications, evidence-interval semantics,
quantile protection invariants, physics propagation semantics, and zero-regression safeguards.
"""

import pytest
from app.schemas.food_evidence import FoodEvidenceDataset, FoodEvidenceRecord
from app.schemas.inference import (
    InferenceResolutionLevel,
    InferredProperty,
    PropertyInferenceProfile,
    UncertaintyLevelEnum,
)
from app.schemas.packaging_request import PackagingRequest
from app.schemas.physics import CalculationStatus
from app.schemas.property_status import PropertyStatusEnum
from scientific_engine.inference.engine import (
    PropertyInferenceEngine,
    infer_commodity_properties,
)
from scientific_engine.physics.respiration import RespirationKineticsModel


# ---------------------------------------------------------------------------
# Level D Tests (UNKNOWN)
# ---------------------------------------------------------------------------

def test_level_d_no_evidence_handling() -> None:
    """Verifies that an unrecorded commodity resolves to Level D (UNKNOWN) without synthetic fallbacks."""
    req = PackagingRequest(
        commodity="dragonfruit",  # Absent from dataset
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=10,
        storage_type="ambient",
    )
    profile = infer_commodity_properties(req)

    for prop_name in ["moisture_percent", "fat_percent", "ph", "respiration_rate"]:
        p = profile.properties[prop_name]
        assert p.uncertainty_level == UncertaintyLevelEnum.LEVEL_D
        assert p.value is None
        assert p.status == PropertyStatusEnum.unknown
        assert p.resolution_level == InferenceResolutionLevel.UNKNOWN
        assert p.confidence is None
        assert p.uncertainty_range is None
        assert p.evidence_interval is None
        assert p.quantile_envelope is None
        assert p.parametric_distribution is None
        assert any(w.code == "NO_EVIDENCE" for w in p.warnings)


def test_level_d_propagation_to_physics() -> None:
    """Verifies Level D (UNKNOWN) respiration rate propagates to physics as UNKNOWN without numeric defaults."""
    req = PackagingRequest(
        commodity="dragonfruit",
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=10,
        storage_type="ambient",
    )
    profile = infer_commodity_properties(req)
    resp_prop = profile.properties["respiration_rate"]

    model = RespirationKineticsModel()
    res = model.calculate_respiration(inferred_respiration=resp_prop, temperature_c=20.0)

    assert res.status == CalculationStatus.UNKNOWN
    assert res.value is None
    assert res.uncertainty_range is None


# ---------------------------------------------------------------------------
# Level A Tests (Deterministic Estimate)
# ---------------------------------------------------------------------------

def test_level_a_user_supplied_precedence() -> None:
    """Verifies explicit user-supplied properties resolve to Level A (Deterministic)."""
    req = PackagingRequest(
        commodity="apple",
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=14,
        storage_type="chilled",
        moisture_percent=78.5,  # Explicit user input
    )
    profile = infer_commodity_properties(req)
    moisture = profile.properties["moisture_percent"]

    assert moisture.uncertainty_level == UncertaintyLevelEnum.LEVEL_A
    assert moisture.value == 78.5
    assert moisture.status == PropertyStatusEnum.measured
    assert moisture.resolution_level == InferenceResolutionLevel.USER_SUPPLIED
    assert moisture.confidence == 1.0
    assert moisture.uncertainty_range == (78.5, 78.5)
    assert moisture.evidence_interval is None  # Level A does not carry an evidence interval
    assert moisture.quantile_envelope is None
    assert moisture.parametric_distribution is None


def test_level_b_single_point_observation() -> None:
    """Verifies single literature point observation resolves to Level B (empirical), not deterministic Level A."""
    custom_records = [
        FoodEvidenceRecord(
            commodity="starfruit",
            product_form="whole",
            property="ph",
            value=3.8,
            unit="pH",
            source_title="Single Test (2022)",
        )
    ]
    dataset = FoodEvidenceDataset(records=custom_records)
    engine = PropertyInferenceEngine(dataset=dataset)

    req = PackagingRequest(
        commodity="starfruit",
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=7,
        storage_type="ambient",
    )
    profile = engine.infer_profile(req)
    ph = profile.properties["ph"]

    assert ph.uncertainty_level == UncertaintyLevelEnum.LEVEL_B
    assert ph.value == 3.8
    assert ph.evidence_interval == (3.8, 3.8)
    assert ph.quantile_envelope is None
    assert ph.parametric_distribution is None


# ---------------------------------------------------------------------------
# Level B Tests (Evidence Interval)
# ---------------------------------------------------------------------------

def test_level_b_literature_range() -> None:
    """Verifies literature evidence with reported min/max range resolves to Level B (Evidence Interval)."""
    req = PackagingRequest(
        commodity="durian",
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=10,
        storage_type="chilled",
        storage_temperature_c=20.0,
    )
    profile = infer_commodity_properties(req)
    resp = profile.properties["respiration_rate"]

    assert resp.uncertainty_level == UncertaintyLevelEnum.LEVEL_B
    assert resp.value == 375.0
    assert resp.uncertainty_range == (300.0, 450.0)
    assert resp.evidence_interval == (300.0, 450.0)
    assert resp.status == PropertyStatusEnum.literature


def test_level_b_context_fallback_envelope() -> None:
    """Verifies context fallbacks assign Level B, attach warnings, and apply confidence discounts."""
    req = PackagingRequest(
        commodity="apple",
        variety="UnknownCultivar",
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=14,
        storage_type="chilled",
    )
    profile = infer_commodity_properties(req)
    moisture = profile.properties["moisture_percent"]

    assert moisture.uncertainty_level == UncertaintyLevelEnum.LEVEL_B
    assert moisture.evidence_interval is not None
    assert moisture.resolution_level == InferenceResolutionLevel.VARIETY_FALLBACK
    assert any(w.code == "VARIETY_FALLBACK" for w in moisture.warnings)
    assert moisture.confidence is not None and moisture.confidence < 0.95


# ---------------------------------------------------------------------------
# Quantile Protection & Semantic Invariant Tests
# ---------------------------------------------------------------------------

def test_evidence_interval_is_not_quantile() -> None:
    """CRITICAL INVARIANT: Evidence interval MUST NOT populate statistical quantile fields."""
    req = PackagingRequest(
        commodity="apple",
        variety="Gala",
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=14,
        storage_type="ambient",
        storage_temperature_c=20.0,
    )
    profile = infer_commodity_properties(req)
    resp = profile.properties["respiration_rate"]

    # Must be Level B Evidence Interval
    assert resp.uncertainty_level == UncertaintyLevelEnum.LEVEL_B
    assert resp.evidence_interval == (25.0, 50.0)

    # Quantile fields MUST remain strictly None in Phase 2
    assert resp.quantile_envelope is None
    assert resp.parametric_distribution is None


def test_no_tln_or_log_normal_generation() -> None:
    """Verifies positive properties (respiration, moisture) NEVER generate log-normal or TLN distributions."""
    req = PackagingRequest(
        commodity="strawberry",
        product_form="whole",
        ripeness_stage="ripe",
        target_shelf_life_days=7,
        storage_type="chilled",
        storage_temperature_c=0.0,
    )
    profile = infer_commodity_properties(req)
    for prop in profile.properties.values():
        assert prop.parametric_distribution is None


def test_confidence_is_heuristic_quality_score_not_probability() -> None:
    """Verifies confidence score is a heuristic quality score [0.1, 1.0], NOT a probability."""
    req = PackagingRequest(
        commodity="apple",
        variety="Gala",
        product_form="sliced",  # Form fallback
        ripeness_stage="ripe",
        target_shelf_life_days=14,
        storage_type="chilled",
        storage_temperature_c=10.0,  # Temp fallback
    )
    profile = infer_commodity_properties(req)
    resp = profile.properties["respiration_rate"]

    assert resp.confidence is not None
    assert 0.1 <= resp.confidence <= 1.0
    # Confirm it reflects heuristic context discounts
    assert resp.resolution_level in [InferenceResolutionLevel.FORM_FALLBACK, InferenceResolutionLevel.CLOSEST_TEMPERATURE_BOUND]


# ---------------------------------------------------------------------------
# Physics Propagation & Scenario Tests
# ---------------------------------------------------------------------------

def test_physics_scenario_evaluation_preserves_semantics() -> None:
    """Verifies lower and upper evidence bounds are evaluated by physics as scenarios, not statistical quantiles."""
    resp_prop = InferredProperty(
        property_name="respiration_rate",
        value=35.0,
        unit="mg CO2/kg/hr",
        status=PropertyStatusEnum.literature,
        resolution_level=InferenceResolutionLevel.EXACT_CONTEXT_MATCH,
        uncertainty_level=UncertaintyLevelEnum.LEVEL_B,
        confidence=0.9,
        uncertainty_range=(25.0, 50.0),
        evidence_interval=(25.0, 50.0),
        minimum_value=25.0,
        maximum_value=50.0,
    )

    model = RespirationKineticsModel()
    res = model.calculate_respiration(inferred_respiration=resp_prop, temperature_c=20.0, rq=1.0)

    assert res.status == CalculationStatus.CALCULATED
    assert res.value is not None
    assert res.uncertainty_range is not None
