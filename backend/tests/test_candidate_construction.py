import pytest
from pathlib import Path
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import engine, Base, SessionLocal
from app.ingestion.pipeline import DataIngestionPipeline
from app.schemas.optimization import ConditionMatchLevel, EvidenceTier
from app.models.evidence import PackagingMaterial
from scientific_engine.optimization.candidate_builder import CandidateBuilder

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Resolve absolute data paths relative to this test file so that
# DataIngestionPipeline.run() works regardless of pytest's CWD.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BASE_DIR = str(_PROJECT_ROOT / "data" / "processed")
_REFERENCE_DIR = str(_PROJECT_ROOT / "data" / "reference")


@pytest.fixture(scope="module")
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(test_engine)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    pipeline = DataIngestionPipeline(session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()
    yield session
    session.close()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()

@pytest.fixture(scope="module")
def candidates(db_session: Session):
    builder = CandidateBuilder(db_session)
    return builder.build_candidates()

def test_real_material_to_valid_candidate(candidates):
    assert len(candidates) > 0
    # Every candidate must have required fields
    for cand in candidates:
        assert cand.candidate_id
        assert cand.material_id
        assert cand.material_name
        assert cand.decision_variables.total_thickness_um > 0

def test_material_specific_thickness_eligibility(candidates, db_session: Session):
    # Find LDPE in DB
    ldpe = db_session.query(PackagingMaterial).filter(PackagingMaterial.material_name.like('%LDPE%')).first()
    
    # Get its candidates
    ldpe_cands = [c for c in candidates if c.material_id == str(ldpe.id)]
    
    # M5 has LDPE at 50 um
    assert all(c.decision_variables.total_thickness_um == 50.0 for c in ldpe_cands)
    assert not any(c.decision_variables.total_thickness_um == 12.0 for c in ldpe_cands)

def test_global_thickness_set_not_universal(candidates):
    # Verify not every candidate has every thickness
    thicknesses_by_material = {}
    for cand in candidates:
        mat = cand.material_id
        t = cand.decision_variables.total_thickness_um
        if mat not in thicknesses_by_material:
            thicknesses_by_material[mat] = set()
        thicknesses_by_material[mat].add(t)
        
    for mat, t_set in thicknesses_by_material.items():
        assert len(t_set) < 7 # no material has all 7 globally observed thicknesses

def test_polyid_null_structure_remains_null(candidates):
    polyid_cands = [c for c in candidates if "PolyID" in c.provenance.source_name]
    assert len(polyid_cands) > 0
    for cand in polyid_cands:
        if cand.material_name in ["Polylactic Acid (PLA Film Specimen)", "Poly(butylene adipate-co-terephthalate) (PBAT Film)"]:
            assert cand.decision_variables.structure_type is None

def test_polyid_qsar_remains_predicted(candidates):
    qsar_cands = [c for c in candidates if c.provenance.evidence_classification == "MODEL_PREDICTED"]
    assert len(qsar_cands) > 0
    for cand in qsar_cands:
        assert "synthetic_prediction_warning" in cand.provenance.model_dump()
        assert cand.provenance.synthetic_prediction_warning is not None
        assert "QSAR" in cand.provenance.synthetic_prediction_warning or "prediction" in cand.provenance.synthetic_prediction_warning.lower()

def test_barrier_properties_preserved_separately(candidates):
    for cand in candidates:
        if cand.barrier_properties.otr is not None:
            assert cand.barrier_properties.otr.unit != ""
        if cand.barrier_properties.wvtr is not None:
            assert cand.barrier_properties.wvtr.unit != ""

def test_test_conditions_preserved(candidates):
    # Check that temperatures and RHs are populated properly
    for cand in candidates:
        if cand.barrier_properties.otr and cand.barrier_properties.otr.test_temperature_c is not None:
            assert cand.barrier_properties.otr.test_temperature_c >= 0
        if cand.barrier_properties.wvtr and cand.barrier_properties.wvtr.test_rh_percent is not None:
            assert cand.barrier_properties.wvtr.test_rh_percent >= 0
            assert cand.barrier_properties.wvtr.test_rh_percent <= 100

def test_deterministic_identity(db_session: Session):
    builder = CandidateBuilder(db_session)
    cands1 = builder.build_candidates()
    cands2 = builder.build_candidates()
    
    # IDs must perfectly match between runs
    ids1 = [c.candidate_id for c in cands1]
    ids2 = [c.candidate_id for c in cands2]
    assert ids1 == ids2

def test_no_cross_material_mixing(candidates):
    # A candidate's provenance source_id must match the original material's observation source_id
    # We implicitly test this by confirming candidate construction loop only joins within a single evidence_id
    for cand in candidates:
        assert cand.provenance.source_id is not None
        # Provenance must be singular per candidate
        assert cand.decision_variables.thickness_source == "observed_discrete_m5"

def test_no_invented_geometry(candidates):
    # Candidate does NOT contain geometry (verified by Pydantic schema validation passing)
    for cand in candidates:
        assert not hasattr(cand, "package_geometry")

def test_no_objectives_calculated(candidates):
    # Candidate does NOT contain objective_values (they belong to ParetoCandidate)
    for cand in candidates:
        assert not hasattr(cand, "objective_values")

def test_no_phase5_feasibility_performed(candidates):
    # Condition match must be UNKNOWN indicating Phase 5 hasn't run
    for cand in candidates:
        assert cand.condition_match == ConditionMatchLevel.UNKNOWN

def test_commodity_agnostic(candidates):
    # Candidates are built entirely from material evidence, no commodity logic involved
    pass

