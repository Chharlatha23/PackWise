"""
Phase 4 Step 2 — Empirical Trial Ingestion & Validation Service Boundary Unit Tests.

Verifies:
1. Valid trial ingestion yields status=VALIDATED, empty quarantine_reasons, and retrievable record.
2. Invalid trial ingestion yields status=QUARANTINED with machine-readable quarantine reasons, saved in repo.
3. Missing scientific values remain explicitly None (never coerced to 0.0 or defaults).
4. Target environment setpoint vs actual measured continuous trajectories remain distinct.
5. Continuous trajectories are preserved without reduction algorithms (no MKT, no averaging).
6. 9-tier traceable provenance is fully preserved.
7. REAL_EMPIRICAL status enforcement (rejection of SYNTHETIC or MODEL_PREDICTED).
8. Repository CRUD operations (get_by_id, list_validated, list_quarantined, filter_by_commodity, clear).
9. Strict duplicate trial_id rejection with explicit ValueError.
10. Zero scientific model execution (physics ODE, surrogate inference, M11 search un-invoked).
"""

import pytest
from unittest.mock import MagicMock, patch

from app.schemas.ai_data import AIDataStatusEnum
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
    EmpiricalTrialIngestionResult,
)
from app.services.empirical_trial_service import (
    EmpiricalTrialRepository,
    EmpiricalTrialIngestionService,
)


def create_valid_empirical_trial_record(trial_id: str = "TRIAL-2026-EXP-001") -> EmpiricalTrialRecord:
    """Helper to build a valid EmpiricalTrialRecord for testing."""
    return EmpiricalTrialRecord(
        trial_id=trial_id,
        protocol_id="PROTO-MAP-001",
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        food_spec=EmpiricalFoodSpecification(
            commodity="Fresh Cut Apples",
            variety="Fuji",
            product_form="fresh_cut",
            initial_mass_kg=0.25,
            initial_moisture_g_g=5.66,
            initial_water_activity=0.98,
        ),
        packaging_spec=EmpiricalPackagingSpecification(
            material="LDPE",
            nominal_thickness_um=50.0,
            measured_thickness_um=51.2,
            measured_otr=1500.0,
            measured_wvtr=12.5,
        ),
        storage_env=EmpiricalStorageEnvironment(
            target_temperature_c=4.0,
            target_relative_humidity_pct=85.0,
            temperature_trajectory=[
                EnvironmentTrajectoryPoint(
                    timestamp="2026-10-08T10:00:00Z",
                    elapsed_time_hours=0.0,
                    temperature_c=4.1,
                    relative_humidity_pct=84.8,
                ),
                EnvironmentTrajectoryPoint(
                    timestamp="2026-10-08T12:00:00Z",
                    elapsed_time_hours=2.0,
                    temperature_c=4.0,
                    relative_humidity_pct=85.2,
                ),
            ],
            relative_humidity_trajectory=[
                EnvironmentTrajectoryPoint(
                    timestamp="2026-10-08T10:00:00Z",
                    elapsed_time_hours=0.0,
                    temperature_c=4.1,
                    relative_humidity_pct=84.8,
                ),
                EnvironmentTrajectoryPoint(
                    timestamp="2026-10-08T12:00:00Z",
                    elapsed_time_hours=2.0,
                    temperature_c=4.0,
                    relative_humidity_pct=85.2,
                ),
            ],
            storage_duration_days=10.0,
        ),
        time_series_observations=[
            EmpiricalTimeSeriesObservation(
                observation_id="OBS-001",
                timestamp="2026-10-08T10:00:00Z",
                elapsed_time_days=0.0,
                measurement_type="moisture_content",
                value=5.66,
                unit="g_g",
                replicate_id="rep_1",
            ),
            EmpiricalTimeSeriesObservation(
                observation_id="OBS-002",
                timestamp="2026-10-10T10:00:00Z",
                elapsed_time_days=2.0,
                measurement_type="moisture_content",
                value=5.50,
                unit="g_g",
                replicate_id="rep_1",
            ),
        ],
        outcome=EmpiricalShelfLifeOutcome(
            observed_shelf_life_days=9.5,
            endpoint_type="moisture_limit",
            endpoint_definition="Moisture content drops below critical threshold 4.0 g_g",
        ),
        provenance=EmpiricalTrialProvenance(
            trial_id=trial_id,
            protocol_id="PROTO-MAP-001",
            operator_or_lab_id="AgriFood_Lab_Alpha",
            creation_timestamp="2026-10-08T09:00:00Z",
            instrument_ids=["INST-TEMP-01", "INST-BAL-02"],
        ),
    )


# 1. Valid trial ingestion test
def test_valid_trial_ingestion():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record = create_valid_empirical_trial_record("TRIAL-VALID-01")

    result = service.ingest_record(record)

    assert result.trial_id == "TRIAL-VALID-01"
    assert result.status == EmpiricalTrialStatusEnum.VALIDATED
    assert result.quarantine_reasons == []
    assert result.record.data_status == AIDataStatusEnum.REAL_EMPIRICAL

    # Verify retrievable in repository
    retrieved = repo.get_by_id("TRIAL-VALID-01")
    assert retrieved is not None
    assert retrieved.trial_id == "TRIAL-VALID-01"
    assert retrieved.status == EmpiricalTrialStatusEnum.VALIDATED
    assert len(repo.list_validated()) == 1
    assert len(repo.list_quarantined()) == 0


# 2. Invalid trial quarantine test
def test_invalid_trial_quarantine_ingestion():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record = create_valid_empirical_trial_record("TRIAL-INVALID-01")

    # Invalidate Gate G by wiping operator_or_lab_id
    record.provenance.operator_or_lab_id = ""

    result = service.ingest_record(record)

    assert result.trial_id == "TRIAL-INVALID-01"
    assert result.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert len(result.quarantine_reasons) >= 1
    assert any("GATE_G_FAIL" in reason for reason in result.quarantine_reasons)

    # Quarantined trial MUST still be saved in repository for audit
    retrieved = repo.get_by_id("TRIAL-INVALID-01")
    assert retrieved is not None
    assert retrieved.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert len(repo.list_quarantined()) == 1
    assert len(repo.list_validated()) == 0


# 3. Missing scientific values remain None
def test_missing_scientific_values_remain_none():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)

    # Create minimal record with optional fields omitted
    record = EmpiricalTrialRecord(
        trial_id="TRIAL-MINIMAL-01",
        protocol_id="PROTO-MIN-01",
        data_status=AIDataStatusEnum.REAL_EMPIRICAL,
        food_spec=EmpiricalFoodSpecification(
            commodity="Strawberry",
            product_form="whole",
            # variety, initial_mass_kg, pH_value, etc. omitted
        ),
        packaging_spec=EmpiricalPackagingSpecification(
            material="PLA",
            # nominal_thickness_um, measured_wvtr, etc. omitted
        ),
        storage_env=EmpiricalStorageEnvironment(
            target_temperature_c=5.0,
            target_relative_humidity_pct=90.0,
            storage_duration_days=7.0,
        ),
        provenance=EmpiricalTrialProvenance(
            trial_id="TRIAL-MINIMAL-01",
            protocol_id="PROTO-MIN-01",
            operator_or_lab_id="Lab_Beta",
            creation_timestamp="2026-10-08T11:00:00Z",
        ),
    )

    result = service.ingest_record(record)
    assert result.status == EmpiricalTrialStatusEnum.VALIDATED

    saved = repo.get_by_id("TRIAL-MINIMAL-01")
    assert saved.food_spec.variety is None
    assert saved.food_spec.initial_mass_kg is None
    assert saved.food_spec.pH_value is None
    assert saved.packaging_spec.nominal_thickness_um is None
    assert saved.packaging_spec.measured_wvtr is None
    assert saved.outcome is None


# 4. Target vs actual trajectory separation
def test_target_vs_actual_trajectory_separation():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record = create_valid_empirical_trial_record("TRIAL-TRAJ-01")

    # Set target temperature to 4.0 but continuous measurements vary (4.1, 4.5)
    record.storage_env.target_temperature_c = 4.0
    record.storage_env.temperature_trajectory = [
        EnvironmentTrajectoryPoint(
            timestamp="2026-10-08T10:00:00Z",
            elapsed_time_hours=0.0,
            temperature_c=4.1,
            relative_humidity_pct=84.5,
        ),
        EnvironmentTrajectoryPoint(
            timestamp="2026-10-08T11:00:00Z",
            elapsed_time_hours=1.0,
            temperature_c=4.5,
            relative_humidity_pct=83.0,
        ),
    ]

    service.ingest_record(record)
    saved = repo.get_by_id("TRIAL-TRAJ-01")

    assert saved.storage_env.target_temperature_c == 4.0
    assert len(saved.storage_env.temperature_trajectory) == 2
    assert saved.storage_env.temperature_trajectory[0].temperature_c == 4.1
    assert saved.storage_env.temperature_trajectory[1].temperature_c == 4.5


# 5. Continuous trajectory preservation without reduction
def test_continuous_trajectory_preservation_no_reduction():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record = create_valid_empirical_trial_record("TRIAL-NO-REDUCE-01")

    trajectory_points = [
        EnvironmentTrajectoryPoint(
            timestamp=f"2026-10-08T{h:02d}:00:00Z",
            elapsed_time_hours=float(h),
            temperature_c=4.0 + (0.1 * h),
            relative_humidity_pct=85.0 - (0.2 * h),
        )
        for h in range(10)
    ]
    record.storage_env.temperature_trajectory = trajectory_points
    record.storage_env.relative_humidity_trajectory = trajectory_points

    service.ingest_record(record)
    saved = repo.get_by_id("TRIAL-NO-REDUCE-01")

    assert len(saved.storage_env.temperature_trajectory) == 10
    assert len(saved.storage_env.relative_humidity_trajectory) == 10
    assert saved.storage_env.temperature_trajectory[9].elapsed_time_hours == 9.0
    assert saved.storage_env.temperature_trajectory[9].temperature_c == pytest.approx(4.9)


# 6. Provenance preservation
def test_provenance_preservation():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record = create_valid_empirical_trial_record("TRIAL-PROV-01")

    record.provenance.food_batch_id = "BATCH-APPLE-2026-09"
    record.provenance.film_batch_id = "BATCH-LDPE-LOT-44"
    record.provenance.storage_chamber_id = "CHAMBER-WALK-IN-03"
    record.provenance.calibration_info = {"cert": "ISO-17025-2026", "calibrated_date": "2026-09-01"}

    service.ingest_record(record)
    saved = repo.get_by_id("TRIAL-PROV-01")

    assert saved.provenance.food_batch_id == "BATCH-APPLE-2026-09"
    assert saved.provenance.film_batch_id == "BATCH-LDPE-LOT-44"
    assert saved.provenance.storage_chamber_id == "CHAMBER-WALK-IN-03"
    assert saved.provenance.calibration_info["cert"] == "ISO-17025-2026"


# 7. REAL_EMPIRICAL status enforcement
def test_real_empirical_status_enforcement():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)

    # Direct instantiation with non-empirical status is blocked by Pydantic model validator
    with pytest.raises(ValueError, match="data_status=REAL_EMPIRICAL"):
        EmpiricalTrialRecord(
            trial_id="TRIAL-SYNTH-01",
            protocol_id="PROTO-01",
            data_status=AIDataStatusEnum.SYNTHETIC,  # Invalid for empirical trial
            food_spec=EmpiricalFoodSpecification(commodity="Banana", product_form="whole"),
            packaging_spec=EmpiricalPackagingSpecification(material="PET"),
            storage_env=EmpiricalStorageEnvironment(target_temperature_c=20.0, storage_duration_days=5.0),
            provenance=EmpiricalTrialProvenance(trial_id="TRIAL-SYNTH-01", protocol_id="PROTO-01", operator_or_lab_id="Lab", creation_timestamp="2026-10-08T00:00:00Z"),
        )


# 8. Repository retrieval and query methods
def test_repository_query_methods():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)

    r1 = create_valid_empirical_trial_record("TRIAL-COMM-01")
    r1.food_spec.commodity = "Strawberry"

    r2 = create_valid_empirical_trial_record("TRIAL-COMM-02")
    r2.food_spec.commodity = "fresh cut apples"

    r3 = create_valid_empirical_trial_record("TRIAL-COMM-03")
    r3.food_spec.commodity = "Strawberry"
    r3.provenance.operator_or_lab_id = ""  # Quarantined

    service.ingest_record(r1)
    service.ingest_record(r2)
    service.ingest_record(r3)

    assert repo.count() == 3
    assert len(repo.list_validated()) == 2
    assert len(repo.list_quarantined()) == 1

    strawberries = repo.filter_by_commodity("strawberry")
    assert len(strawberries) == 2
    strawberry_ids = {rec.trial_id for rec in strawberries}
    assert strawberry_ids == {"TRIAL-COMM-01", "TRIAL-COMM-03"}

    apples = repo.filter_by_commodity("Fresh Cut Apples")
    assert len(apples) == 1
    assert apples[0].trial_id == "TRIAL-COMM-02"

    repo.clear()
    assert repo.count() == 0


from app.services.empirical_trial_service import (
    EmpiricalTrialRepository,
    EmpiricalTrialIngestionService,
    DuplicateTrialIDError,
)
from pydantic import ValidationError


# 9. Duplicate trial_id rejection with machine-readable error code
def test_duplicate_trial_id_rejection():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record1 = create_valid_empirical_trial_record("TRIAL-DUP-01")
    record2 = create_valid_empirical_trial_record("TRIAL-DUP-01")

    service.ingest_record(record1)

    with pytest.raises(DuplicateTrialIDError) as exc_info:
        service.ingest_record(record2)

    assert exc_info.value.error_code == "DUPLICATE_TRIAL_ID"
    assert exc_info.value.trial_id == "TRIAL-DUP-01"
    assert "Duplicate trial_id 'TRIAL-DUP-01'" in str(exc_info.value)

    # Ensure original record in repository is unchanged
    original = repo.get_by_id("TRIAL-DUP-01")
    assert original is not None
    assert repo.count() == 1


# 10. Ingest dict payload test
def test_ingest_dict_payload():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record = create_valid_empirical_trial_record("TRIAL-DICT-01")
    payload = record.model_dump() if hasattr(record, "model_dump") else record.dict()

    result = service.ingest_dict(payload)
    assert result.trial_id == "TRIAL-DICT-01"
    assert result.status == EmpiricalTrialStatusEnum.VALIDATED
    assert repo.get_by_id("TRIAL-DICT-01") is not None


# 11. Zero scientific model execution test
def test_zero_scientific_model_execution():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)
    record = create_valid_empirical_trial_record("TRIAL-NO-MODEL-01")

    # Patch scientific physics requirement and gas exchange engines to verify zero execution during trial ingestion
    with patch("scientific_engine.physics.requirements.PackagingRequirementEngine.evaluate_requirements", side_effect=AssertionError("Physics Requirement Engine must not be invoked during empirical trial ingestion!")):
        with patch("scientific_engine.physics.gas_exchange.GasExchangeModel.calculate_gas_requirements", side_effect=AssertionError("Gas Exchange Model must not be invoked during empirical trial ingestion!")):
            result = service.ingest_record(record)
            assert result.status == EmpiricalTrialStatusEnum.VALIDATED


# 12. Raw payload preservation and parse failure contract test
def test_raw_payload_preservation_and_parse_failure_behavior():
    repo = EmpiricalTrialRepository()
    service = EmpiricalTrialIngestionService(repository=repo)

    # Case A — Valid payload: raw payload -> VALIDATED record
    record_a = create_valid_empirical_trial_record("TRIAL-RAW-VALID-01")
    raw_dict_a = record_a.model_dump() if hasattr(record_a, "model_dump") else record_a.dict()
    raw_dict_a["custom_lab_tag"] = "LAB-REF-998"

    res_a = service.ingest_dict(raw_dict_a)
    assert res_a.status == EmpiricalTrialStatusEnum.VALIDATED
    saved_a = repo.get_by_id("TRIAL-RAW-VALID-01")
    assert saved_a is not None
    assert saved_a.raw_payload is not None
    assert saved_a.raw_payload["custom_lab_tag"] == "LAB-REF-998"

    # Case B — Invalid payload: raw payload -> QUARANTINED record
    record_b = create_valid_empirical_trial_record("TRIAL-RAW-QUAR-01")
    raw_dict_b = record_b.model_dump() if hasattr(record_b, "model_dump") else record_b.dict()
    raw_dict_b["provenance"]["operator_or_lab_id"] = ""  # Wipes operator to fail Gate G
    raw_dict_b["custom_notes"] = "Quarantined sample 42"

    res_b = service.ingest_dict(raw_dict_b)
    assert res_b.status == EmpiricalTrialStatusEnum.QUARANTINED
    saved_b = repo.get_by_id("TRIAL-RAW-QUAR-01")
    assert saved_b is not None
    assert saved_b.status == EmpiricalTrialStatusEnum.QUARANTINED
    assert saved_b.raw_payload is not None
    assert saved_b.raw_payload["custom_notes"] == "Quarantined sample 42"

    # Case C — Parse failure: rejected before repository entry
    malformed_payload = {
        "trial_id": "TRIAL-MALFORMED-01",
        "food_spec": "Not A Dict",  # Fails Pydantic model validation
    }
    with pytest.raises(ValidationError):
        service.ingest_dict(malformed_payload)

    # Rejected before repository entry
    assert repo.get_by_id("TRIAL-MALFORMED-01") is None




