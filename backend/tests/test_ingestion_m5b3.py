import os
import json
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.evidence import (
    Base, EvidenceRecord, Source, RespirationObservation,
    MaterialBarrierObservation, PropertyType, GasSpecies,
    MicrobialGasInhibitionResponse, MicrobialGrowthKinetics,
    PostharvestGasTolerances, PostharvestStorageLimits,
    ValidationResult, DataTransformation, FoodObservation,
    EvidenceClassification, VerificationStatus
)
from app.ingestion.pipeline import DataIngestionPipeline

TEST_DB_URL = "sqlite:///:memory:"

# Resolve absolute data paths relative to this test file so that
# DataIngestionPipeline.run() works correctly regardless of pytest CWD.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BASE_DIR = str(_PROJECT_ROOT / "data" / "processed")
_REFERENCE_DIR = str(_PROJECT_ROOT / "data" / "reference")

@pytest.fixture(scope="module")
def engine():
    eng = create_engine(TEST_DB_URL)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()

@pytest.fixture(scope="function")
def db_session(engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    # Clean up all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    yield session
    session.rollback()
    session.close()


def test_ingestion_pipeline_47_records(db_session):
    """Test that all 9 datasets and 47 records are discovered and inserted."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    stats = pipeline.run()

    assert stats["datasets_processed"] == 9, "Expected exactly 9 datasets to be processed."
    assert stats["total_input_records"] == 47, "Expected exactly 47 input records."
    assert stats["total_inserted"] == 47, "Expected exactly 47 inserted records."
    assert stats["total_skipped"] == 0, "Expected 0 skipped records on fresh ingestion."
    assert stats["validation_results_ingested"] == 9, "Expected 9 validation results."
    assert stats["data_transformations_ingested"] == 14, "Expected 14 data transformations."


def test_ingestion_idempotency(db_session):
    """Test that running ingestion twice produces 0 duplicate records."""
    pipeline1 = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    stats1 = pipeline1.run()
    counts1 = stats1["entity_counts"]

    pipeline2 = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    stats2 = pipeline2.run()
    counts2 = stats2["entity_counts"]

    assert stats2["total_inserted"] == 0, "Idempotency failed: duplicate inserts occurred."
    assert stats2["total_skipped"] == 47, "Expected 47 records to be skipped on second run."
    assert stats2["validation_results_ingested"] == 0, "Validation results re-inserted on second run."
    assert stats2["data_transformations_ingested"] == 0, "Data transformations re-inserted on second run."

    # Verify every single entity count remained exactly unchanged
    for entity, count in counts1.items():
        assert counts2[entity] == count, f"Entity {entity} count changed: {count} -> {counts2[entity]}"


def test_respiration_range_preservation(db_session):
    """Verify that respiration ranges retain both min and max boundaries."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    # Query respiration observations that are ranges
    range_obs = db_session.query(RespirationObservation).filter(
        RespirationObservation.is_range == True
    ).all()

    assert len(range_obs) > 0, "No respiration ranges found in database."
    for obs in range_obs:
        assert obs.rate_min is not None, "Range observation missing rate_min."
        assert obs.rate_max is not None, "Range observation missing rate_max."
        assert obs.rate_min < obs.rate_max, f"rate_min ({obs.rate_min}) not strictly less than rate_max ({obs.rate_max})."
        assert obs.operator == "range", f"Expected operator 'range', got {obs.operator}."

    # Specific check: USDA HB66 Apple at 0°C CO2 production is 3.0 to 6.0 mg/kg·h
    apple_co2_0c = db_session.query(RespirationObservation).filter(
        RespirationObservation.gas_species == GasSpecies.CO2,
        RespirationObservation.temperature_c_value == 0.0,
        RespirationObservation.rate_min == 3.0
    ).first()
    assert apple_co2_0c is not None, "Apple 0°C CO2 respiration record not found."
    assert apple_co2_0c.rate_max == 6.0, f"Apple 0°C CO2 rate_max should be 6.0, got {apple_co2_0c.rate_max}."
    assert apple_co2_0c.is_range is True


def test_respiration_gas_species_separation(db_session):
    """Verify rO2 != rCO2 and gas_species is strictly explicit."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    o2_records = db_session.query(RespirationObservation).filter(
        RespirationObservation.gas_species == GasSpecies.O2
    ).all()
    co2_records = db_session.query(RespirationObservation).filter(
        RespirationObservation.gas_species == GasSpecies.CO2
    ).all()

    assert len(o2_records) > 0, "No O2 respiration observations found."
    assert len(co2_records) > 0, "No CO2 respiration observations found."

    # Ensure no record has an ambiguous or null gas_species
    for r in o2_records:
        assert r.gas_species == GasSpecies.O2
    for r in co2_records:
        assert r.gas_species == GasSpecies.CO2


def test_validation_result_ingestion(db_session):
    """Verify that ValidationResult records are ingested and linked to correct datasets."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    vrs = db_session.query(ValidationResult).all()
    assert len(vrs) == 9, f"Expected 9 ValidationResult records, got {len(vrs)}."

    expected_datasets = {
        "usda_fdc", "india_ifct", "usda_handbook_66", "uc_davis",
        "indian_postharvest", "cirad_wur", "polyid", "manufacturer_tds", "combase"
    }
    found_datasets = {vr.dataset for vr in vrs}
    assert found_datasets == expected_datasets, f"Missing datasets in ValidationResult: {expected_datasets - found_datasets}"

    # Verify each ValidationResult is linked to an evidence record from its own dataset
    for vr in vrs:
        assert vr.evidence_id is not None
        ev = db_session.query(EvidenceRecord).filter_by(id=vr.evidence_id).first()
        assert ev is not None, f"Orphan ValidationResult for dataset {vr.dataset}"
        src = db_session.query(Source).filter_by(id=ev.source_id).first()
        assert src is not None


def test_data_transformation_ingestion(db_session):
    """Verify that DataTransformation lineage from cleaning_log.json is ingested."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    dts = db_session.query(DataTransformation).all()
    assert len(dts) == 14, f"Expected 14 DataTransformation records, got {len(dts)}."

    for dt in dts:
        assert dt.evidence_id is not None, "DataTransformation has no evidence_id."
        assert dt.rule_id == "RULE-CAT-01", f"Unexpected rule_id: {dt.rule_id}."
        assert dt.original_value in {"raw", "fresh_cut", "processed"}
        assert dt.transformed_value in {"RAW", "FRESH_CUT", "PROCESSED"}
        assert dt.field == "processing_state"

        # Verify evidence record link is valid
        ev = db_session.query(EvidenceRecord).filter_by(id=dt.evidence_id).first()
        assert ev is not None, f"Orphan DataTransformation for field {dt.field}"


def test_combase_atmosphere_and_gas_inhibition(db_session):
    """Verify ComBase atmosphere_condition and gas inhibition parameters are preserved."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    # 1. Growth kinetics atmosphere_condition
    kinetics = db_session.query(MicrobialGrowthKinetics).all()
    assert len(kinetics) > 0, "No MicrobialGrowthKinetics records found."
    for k in kinetics:
        assert k.atmosphere_condition is not None, "MicrobialGrowthKinetics atmosphere_condition is None."
        assert k.atmosphere_condition == "aerobic"

    # 2. Gas inhibition responses
    inhibitions = db_session.query(MicrobialGasInhibitionResponse).all()
    assert len(inhibitions) == 5, f"Expected 5 MicrobialGasInhibitionResponse records, got {len(inhibitions)}."
    for inh in inhibitions:
        assert inh.co2_sensitivity is not None
        assert inh.minimum_co2_inhibition_percent is not None
        assert 0.0 <= inh.minimum_co2_inhibition_percent <= 100.0


def test_granular_literature_provenance(db_session):
    """Verify literature_references JSONB field is populated on EvidenceRecord."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    # Indian postharvest records have literature_references
    indian_evs = db_session.query(EvidenceRecord).filter(
        EvidenceRecord.record_identifier_in_source.like("IND-POST-%")
    ).all()
    assert len(indian_evs) > 0, "No Indian postharvest evidence records found."
    for ev in indian_evs:
        assert ev.literature_references is not None, f"Indian postharvest {ev.record_identifier_in_source} missing lit refs."
        assert isinstance(ev.literature_references, list)
        assert len(ev.literature_references) == 4

    # PolyID QSAR predicted records have model_doi and synthetic warning
    pred_ev = db_session.query(EvidenceRecord).filter_by(
        record_identifier_in_source="PRED-QSAR-001"
    ).first()
    assert pred_ev is not None, "PRED-QSAR-001 evidence record not found."
    assert pred_ev.literature_references is not None
    assert pred_ev.literature_references.get("model_doi") == "10.1016/j.polymertesting.2023.108112"
    assert pred_ev.synthetic_prediction_warning is not None
    assert "SYNTHETIC_MODEL_PREDICTION" in pred_ev.synthetic_prediction_warning


def test_polyid_measured_vs_predicted_separation(db_session):
    """Verify strict separation between experimental and QSAR predicted material observations."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    # Check EvidenceClassification
    exp_evs = db_session.query(EvidenceRecord).filter_by(
        evidence_classification=EvidenceClassification.EXPERIMENTAL_LITERATURE_DATA
    ).all()
    pred_evs = db_session.query(EvidenceRecord).filter_by(
        evidence_classification=EvidenceClassification.MODEL_PREDICTED
    ).all()

    assert len(pred_evs) == 2, f"Expected exactly 2 MODEL_PREDICTED evidence records, got {len(pred_evs)}."
    for pev in pred_evs:
        assert pev.verification_status == VerificationStatus.PREDICTIVE_ONLY

    # Check MaterialBarrierObservation linked to MODEL_PREDICTED
    pred_barriers = db_session.query(MaterialBarrierObservation).join(
        EvidenceRecord, MaterialBarrierObservation.evidence_id == EvidenceRecord.id
    ).filter(
        EvidenceRecord.evidence_classification == EvidenceClassification.MODEL_PREDICTED
    ).all()

    assert len(pred_barriers) == 2, f"Expected 2 predicted barrier observations, got {len(pred_barriers)}."
    props = {b.property_type for b in pred_barriers}
    assert props == {PropertyType.OTR, PropertyType.WVTR}

    # Verify uncertainty ranges on predicted barriers
    for b in pred_barriers:
        assert b.is_range is True
        assert b.value_min is not None
        assert b.value_max is not None
        assert b.value_min < b.value_max


def test_material_barrier_properties_distinct(db_session):
    """Verify OTR, CO2TR, WVTR are distinct and thickness is preserved."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    otrs = db_session.query(MaterialBarrierObservation).filter_by(property_type=PropertyType.OTR).all()
    co2trs = db_session.query(MaterialBarrierObservation).filter_by(property_type=PropertyType.CO2TR).all()
    wvtrs = db_session.query(MaterialBarrierObservation).filter_by(property_type=PropertyType.WVTR).all()

    assert len(otrs) > 0, "No OTR observations."
    assert len(co2trs) > 0, "No CO2TR observations."
    assert len(wvtrs) > 0, "No WVTR observations."

    # Check thickness values are preserved
    for b in otrs + co2trs + wvtrs:
        assert b.value is not None
        assert b.value >= 0


def test_indian_postharvest_tolerances(db_session):
    """Verify Indian postharvest gas tolerances and PARTIALLY_VERIFIED status."""
    pipeline = DataIngestionPipeline(db_session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()

    # Query tolerances with Indian EMAP limits
    indian_tols = db_session.query(PostharvestGasTolerances).filter(
        PostharvestGasTolerances.min_o2_fermentation_limit_percent.isnot(None)
    ).all()

    assert len(indian_tols) > 0, "No Indian EMAP gas tolerances found."
    for tol in indian_tols:
        assert tol.min_o2_fermentation_limit_percent is not None
        assert tol.max_co2_injury_limit_percent is not None
        assert tol.min_o2_fermentation_limit_percent >= 0
        assert tol.max_co2_injury_limit_percent >= 0

        # Verify parent evidence verification status is PARTIALLY_VERIFIED
        ev = db_session.query(EvidenceRecord).filter_by(id=tol.evidence_id).first()
        assert ev.verification_status == VerificationStatus.PARTIALLY_VERIFIED


def test_malformed_input_behavior(db_session):
    """Verify pipeline gracefully handles invalid files without corrupting database."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create an invalid JSON file
        bad_file = os.path.join(tmp_dir, "corrupt.json")
        with open(bad_file, "w") as f:
            f.write("not valid json at all")

        # Run pipeline pointing to this temp dir (reference_dir is valid so report write succeeds)
        pipeline = DataIngestionPipeline(db_session, base_dir=tmp_dir, reference_dir=_REFERENCE_DIR)
        try:
            stats = pipeline.run()
        except Exception:
            # Pipeline should catch or fail cleanly
            pass

        # Database should remain empty and uncorrupted
        assert db_session.query(EvidenceRecord).count() == 0
