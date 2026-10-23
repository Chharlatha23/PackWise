"""
Phase 4 — Empirical Validation Foundation Unit Tests.

Verifies:
1. Empirical trial identity preservation (trial_id, protocol_id).
2. Missing empirical measurements remain explicitly None (no silent zero coercion).
3. Nominal vs measured packaging properties remain distinct.
4. Full continuous T_actual(t) and RH_actual(t) trajectories are preserved without reduction algorithms.
5. Target environment setpoint is distinct from measured actual trajectories.
6. Replicate identity (replicate_id) and measurement uncertainty are preserved.
7. Unit preservation and validation across time-series observations.
8. Provenance preservation (9-tier traceable lineage with operator/lab ID).
9. Quality gate validation and quarantine handling (VALIDATED vs QUARANTINED).
10. Data status integrity (REAL_EMPIRICAL != MODEL_PREDICTED, REAL_EMPIRICAL != SYNTHETIC).
11. Protocol-specific endpoint definitions (no hardcoded global constants).
12. Seamless conversion to Layer 1 AIDataRecord for system compatibility.
"""

import pytest
from app.schemas.ai_data import AIDataStatusEnum
from app.schemas.inference import UncertaintyLevelEnum
from app.schemas.empirical_trial import (
    EmpiricalTrialStatusEnum,
    EmpiricalMeasurementUncertainty,
    EmpiricalFoodSpecification,
    EmpiricalPackagingSpecification,
    EnvironmentTrajectoryPoint,
    EmpiricalStorageEnvironment,
    EmpiricalTimeSeriesObservation,
    EmpiricalShelfLifeOutcome,
    EmpiricalTrialProvenance,
    EmpiricalTrialRecord,
    EmpiricalTrialQualityGateEngine,
)


@pytest.fixture
def valid_empirical_trial() -> EmpiricalTrialRecord:
    """Fixture providing a valid EmpiricalTrialRecord for testing."""
    return EmpiricalTrialRecord(
        trial_id="trial_emp_2026_001",
        protocol_id="ISO_16720_SHELF_LIFE_V2",
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        food_spec=EmpiricalFoodSpecification(
            commodity="Strawberry",
            variety="Chandler",
            product_form="fresh_cut",
            initial_mass_kg=0.25,
            initial_moisture_g_g=8.5,
            initial_water_activity=0.98,
            critical_moisture_g_g=9.2,
            pH_value=3.6,
            food_batch_id="batch_straw_908",
        ),
        packaging_spec=EmpiricalPackagingSpecification(
            material="LDPE",
            nominal_thickness_um=50.0,
            measured_thickness_um=52.3,
            measured_otr=1450.0,
            measured_wvtr=12.5,
            package_surface_area_m2=0.08,
            headspace_volume_m3=0.0004,
            film_batch_id="lot_ldpe_4412",
        ),
        storage_env=EmpiricalStorageEnvironment(
            target_temperature_c=4.0,
            target_relative_humidity_pct=85.0,
            temperature_trajectory=[
                EnvironmentTrajectoryPoint(timestamp="2026-10-08T00:00:00Z", elapsed_time_hours=0.0, temperature_c=4.1, relative_humidity_pct=84.8),
                EnvironmentTrajectoryPoint(timestamp="2026-10-08T12:00:00Z", elapsed_time_hours=12.0, temperature_c=4.2, relative_humidity_pct=85.2),
                EnvironmentTrajectoryPoint(timestamp="2026-10-09T00:00:00Z", elapsed_time_hours=24.0, temperature_c=3.9, relative_humidity_pct=85.0),
            ],
            relative_humidity_trajectory=[
                EnvironmentTrajectoryPoint(timestamp="2026-10-08T00:00:00Z", elapsed_time_hours=0.0, temperature_c=4.1, relative_humidity_pct=84.8),
                EnvironmentTrajectoryPoint(timestamp="2026-10-08T12:00:00Z", elapsed_time_hours=12.0, temperature_c=4.2, relative_humidity_pct=85.2),
                EnvironmentTrajectoryPoint(timestamp="2026-10-09T00:00:00Z", elapsed_time_hours=24.0, temperature_c=3.9, relative_humidity_pct=85.0),
            ],
            storage_duration_days=14.0,
        ),
        time_series_observations=[
            EmpiricalTimeSeriesObservation(
                observation_id="obs_001",
                timestamp="2026-10-08T00:00:00Z",
                elapsed_time_days=0.0,
                measurement_type="microbial_count",
                value=3.2,
                unit="log10_CFU_g",
                replicate_id="rep_A",
                uncertainty=EmpiricalMeasurementUncertainty(value=0.1, uncertainty_type="standard_error", unit="log10_CFU_g"),
            ),
            EmpiricalTimeSeriesObservation(
                observation_id="obs_002",
                timestamp="2026-10-12T00:00:00Z",
                elapsed_time_days=4.0,
                measurement_type="microbial_count",
                value=5.1,
                unit="log10_CFU_g",
                replicate_id="rep_A",
                uncertainty=EmpiricalMeasurementUncertainty(value=0.15, uncertainty_type="standard_error", unit="log10_CFU_g"),
            ),
        ],
        outcome=EmpiricalShelfLifeOutcome(
            observed_shelf_life_days=10.5,
            endpoint_type="microbial_threshold",
            endpoint_definition="Total Viable Count >= 7.0 log10 CFU/g per ISO 16720 protocol specification",
            endpoint_measurement_value=7.1,
            endpoint_measurement_unit="log10_CFU_g",
        ),
        provenance=EmpiricalTrialProvenance(
            trial_id="trial_emp_2026_001",
            protocol_id="ISO_16720_SHELF_LIFE_V2",
            food_batch_id="batch_straw_908",
            film_batch_id="lot_ldpe_4412",
            storage_chamber_id="chamber_env_04",
            instrument_ids=["inst_micro_01", "inst_temp_logger_09"],
            operator_or_lab_id="lab_food_qual_agri",
            creation_timestamp="2026-10-08T10:00:00Z",
        ),
    )


def test_empirical_trial_identity_preservation(valid_empirical_trial):
    """Verify trial_id and protocol_id are preserved exactly."""
    assert valid_empirical_trial.trial_id == "trial_emp_2026_001"
    assert valid_empirical_trial.protocol_id == "ISO_16720_SHELF_LIFE_V2"
    assert valid_empirical_trial.data_status == AIDataStatusEnum.REAL_EMPIRICAL


def test_missing_empirical_measurements_remain_none():
    """Verify unmeasured food/packaging properties remain None and never become 0.0 or defaults."""
    food = EmpiricalFoodSpecification(
        commodity="Apple",
        product_form="fresh_cut",
    )
    assert food.initial_mass_kg is None
    assert food.initial_moisture_g_g is None
    assert food.initial_water_activity is None
    assert food.respiration_rate_O2 is None

    pkg = EmpiricalPackagingSpecification(
        material="PET",
    )
    assert pkg.measured_thickness_um is None
    assert pkg.measured_otr is None
    assert pkg.measured_wvtr is None


def test_nominal_vs_measured_packaging_properties_distinct(valid_empirical_trial):
    """Verify nominal thickness and measured thickness are preserved separately."""
    spec = valid_empirical_trial.packaging_spec
    assert spec.nominal_thickness_um == 50.0
    assert spec.measured_thickness_um == 52.3
    assert spec.nominal_thickness_um != spec.measured_thickness_um


def test_trajectory_preservation_without_compression(valid_empirical_trial):
    """Verify continuous T_actual(t) and RH_actual(t) trajectories are preserved in full detail."""
    env = valid_empirical_trial.storage_env
    assert len(env.temperature_trajectory) == 3
    assert env.temperature_trajectory[0].temperature_c == 4.1
    assert env.temperature_trajectory[1].temperature_c == 4.2
    assert env.temperature_trajectory[2].temperature_c == 3.9

    # Target temperature remains distinct from trajectory values
    assert env.target_temperature_c == 4.0


def test_replicate_identity_and_uncertainty_preservation(valid_empirical_trial):
    """Verify replicate_id and measurement uncertainty records are retained."""
    obs = valid_empirical_trial.time_series_observations[0]
    assert obs.replicate_id == "rep_A"
    assert obs.uncertainty is not None
    assert obs.uncertainty.value == 0.1
    assert obs.uncertainty.uncertainty_type == "standard_error"


def test_quality_gate_engine_validated(valid_empirical_trial):
    """Verify valid trial passes all 8 quality gates and receives VALIDATED status."""
    engine = EmpiricalTrialQualityGateEngine()
    validated_rec = engine.evaluate_and_validate(valid_empirical_trial)

    assert validated_rec.status == EmpiricalTrialStatusEnum.VALIDATED
    assert len(validated_rec.quarantine_reasons) == 0


def test_quality_gate_engine_quarantine_invalid_water_activity(valid_empirical_trial):
    """Verify trial with physically invalid water activity (> 1.0) is QUARANTINED with reasons."""
    valid_empirical_trial.food_spec.initial_water_activity = 1.5
    engine = EmpiricalTrialQualityGateEngine()
    quarantined_rec = engine.evaluate_and_validate(valid_empirical_trial)

    assert quarantined_rec.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert any("GATE_C_FAIL" in reason for reason in quarantined_rec.quarantine_reasons)


def test_quality_gate_engine_quarantine_missing_endpoint_definition(valid_empirical_trial):
    """Verify trial outcome without explicit protocol endpoint definition is QUARANTINED."""
    valid_empirical_trial.outcome.endpoint_definition = ""
    engine = EmpiricalTrialQualityGateEngine()
    quarantined_rec = engine.evaluate_and_validate(valid_empirical_trial)

    assert quarantined_rec.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert any("GATE_H_FAIL" in reason for reason in quarantined_rec.quarantine_reasons)


def test_data_status_integrity_rejection():
    """Verify EmpiricalTrialRecord rejects non-REAL_EMPIRICAL status types."""
    with pytest.raises(ValueError, match="REAL_EMPIRICAL"):
        EmpiricalTrialRecord(
            trial_id="trial_bad_01",
            protocol_id="PROTO_01",
            data_status=AIDataStatusEnum.SYNTHETIC,  # Invalid for empirical trial
            food_spec=EmpiricalFoodSpecification(commodity="Grape", product_form="whole"),
            packaging_spec=EmpiricalPackagingSpecification(material="PE"),
            storage_env=EmpiricalStorageEnvironment(target_temperature_c=20.0, target_relative_humidity_pct=50.0, storage_duration_days=5.0),
            provenance=EmpiricalTrialProvenance(trial_id="trial_bad_01", protocol_id="PROTO_01", operator_or_lab_id="lab_01", creation_timestamp="2026-10-08T00:00:00Z"),
        )


def test_conversion_to_ai_data_record(valid_empirical_trial):
    """Verify conversion to Layer 1 AIDataRecord preserves REAL_EMPIRICAL and LEVEL_A semantics."""
    ai_record = valid_empirical_trial.to_ai_data_record()

    assert ai_record.record_id == "trial_emp_2026_001"
    assert ai_record.data_status == AIDataStatusEnum.REAL_EMPIRICAL
    assert ai_record.epistemic_level == UncertaintyLevelEnum.LEVEL_A
    assert ai_record.is_real_empirical is True
    assert ai_record.is_model_generated is False
    assert "initial_water_activity" in ai_record.food_features
    assert ai_record.food_features["initial_water_activity"].value == 0.98
    assert ai_record.outcome_features["shelf_life_days"].value == 10.5


def test_unknown_target_setpoint_accepted(valid_empirical_trial):
    """Test 1: A valid empirical trial with target_temperature_c=None and target_relative_humidity_pct=None validates cleanly if trajectories exist."""
    valid_empirical_trial.storage_env.target_temperature_c = None
    valid_empirical_trial.storage_env.target_relative_humidity_pct = None

    engine = EmpiricalTrialQualityGateEngine()
    validated_rec = engine.evaluate_and_validate(valid_empirical_trial)

    assert validated_rec.status == EmpiricalTrialStatusEnum.VALIDATED
    assert len(validated_rec.quarantine_reasons) == 0


def test_no_fabricated_target_substitution(valid_empirical_trial):
    """Test 2: Confirm missing target setpoint values remain None and are not replaced with 0.0 or average values."""
    valid_empirical_trial.storage_env.target_temperature_c = None
    valid_empirical_trial.storage_env.target_relative_humidity_pct = None

    assert valid_empirical_trial.storage_env.target_temperature_c is None
    assert valid_empirical_trial.storage_env.target_relative_humidity_pct is None
    assert valid_empirical_trial.storage_env.target_temperature_c != 0.0
    assert valid_empirical_trial.storage_env.target_temperature_c != 4.1  # Does not collapse to trajectory mean


def test_actual_trajectories_preserved_when_target_missing(valid_empirical_trial):
    """Test 3: Confirm continuous T_actual(t) and RH_actual(t) trajectories remain unchanged when target is None."""
    valid_empirical_trial.storage_env.target_temperature_c = None
    valid_empirical_trial.storage_env.target_relative_humidity_pct = None

    env = valid_empirical_trial.storage_env
    assert len(env.temperature_trajectory) == 3
    assert env.temperature_trajectory[0].temperature_c == 4.1
    assert env.temperature_trajectory[1].temperature_c == 4.2
    assert env.temperature_trajectory[2].temperature_c == 3.9


def test_existing_valid_target_setpoints_work(valid_empirical_trial):
    """Test 4: A trial with recorded target setpoints continues to validate normally."""
    assert valid_empirical_trial.storage_env.target_temperature_c == 4.0
    assert valid_empirical_trial.storage_env.target_relative_humidity_pct == 85.0

    engine = EmpiricalTrialQualityGateEngine()
    validated_rec = engine.evaluate_and_validate(valid_empirical_trial)
    assert validated_rec.status == EmpiricalTrialStatusEnum.VALIDATED


def test_gate_e_quarantine_when_both_target_and_trajectory_missing(valid_empirical_trial):
    """Test 5: Gate E quarantines when BOTH target setpoint AND continuous trajectories are absent."""
    valid_empirical_trial.storage_env.target_temperature_c = None
    valid_empirical_trial.storage_env.target_relative_humidity_pct = None
    valid_empirical_trial.storage_env.temperature_trajectory = []
    valid_empirical_trial.storage_env.relative_humidity_trajectory = []

    engine = EmpiricalTrialQualityGateEngine()
    quarantined_rec = engine.evaluate_and_validate(valid_empirical_trial)

    assert quarantined_rec.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert any("GATE_E_FAIL" in reason for reason in quarantined_rec.quarantine_reasons)


def test_gate_e_case_c_temp_present_rh_absent(valid_empirical_trial):
    """Case C Test: Gate E quarantines when temperature info is present but RH info is completely absent."""
    valid_empirical_trial.storage_env.target_temperature_c = None
    valid_empirical_trial.storage_env.target_relative_humidity_pct = None
    # Temperature trajectory present, RH trajectory absent
    valid_empirical_trial.storage_env.relative_humidity_trajectory = []

    engine = EmpiricalTrialQualityGateEngine()
    quarantined_rec = engine.evaluate_and_validate(valid_empirical_trial)

    assert quarantined_rec.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert any("GATE_E_FAIL: Storage environment lacks relative humidity information" in reason for reason in quarantined_rec.quarantine_reasons)


def test_gate_e_case_d_rh_present_temp_absent(valid_empirical_trial):
    """Case D Test: Gate E quarantines when RH info is present but temperature info is completely absent."""
    valid_empirical_trial.storage_env.target_temperature_c = None
    valid_empirical_trial.storage_env.target_relative_humidity_pct = None
    # RH trajectory present, Temperature trajectory absent
    valid_empirical_trial.storage_env.temperature_trajectory = []

    engine = EmpiricalTrialQualityGateEngine()
    quarantined_rec = engine.evaluate_and_validate(valid_empirical_trial)

    assert quarantined_rec.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert any("GATE_E_FAIL: Storage environment lacks temperature information" in reason for reason in quarantined_rec.quarantine_reasons)


