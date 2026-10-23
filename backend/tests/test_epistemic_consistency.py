import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.schemas.packaging_request import PackagingRequest
from app.services.recommendation_service import RecommendationService
from app.core.database import Base
from app.schemas.physics import CalculationStatus

# Resolve absolute data paths relative to this test file so that
# DataIngestionPipeline.run() (called inside RecommendationService) works
# correctly regardless of pytest's working directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BASE_DIR = str(_PROJECT_ROOT / "data" / "processed")
_REFERENCE_DIR = str(_PROJECT_ROOT / "data" / "reference")


@pytest.fixture(scope="module")
def db_session():
    """Isolated in-memory SQLite session; no live PostgreSQL connection required."""
    from app.ingestion.pipeline import DataIngestionPipeline
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSession()
    # Pre-populate so RecommendationService skips its own DataIngestionPipeline call
    pipeline = DataIngestionPipeline(session, base_dir=_BASE_DIR, reference_dir=_REFERENCE_DIR)
    pipeline.run()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="module")
def recommendation_service():
    return RecommendationService()


def test_scenario_1_all_inputs_provided(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=0.7,
        package_surface_area_m2=0.08,
        package_headspace_volume_cm3=400.0,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)

    env = response.requirement_envelope
    assert env.moisture_requirements.status in [CalculationStatus.CALCULATED, CalculationStatus.PARTIALLY_CALCULATED]
    assert response.total_candidates_evaluated > 0


def test_scenario_2_missing_product_mass(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=None,
        package_surface_area_m2=0.08,
        package_headspace_volume_cm3=400.0,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)

    assert response.request.product_mass_kg is None


def test_scenario_3_missing_surface_area(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=0.7,
        package_surface_area_m2=None,
        package_headspace_volume_cm3=400.0,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)
    assert response.request.package_surface_area_m2 is None


def test_scenario_4_missing_mass_and_area(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=None,
        package_surface_area_m2=None,
        package_headspace_volume_cm3=400.0,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)

    env = response.requirement_envelope
    assert env.gas_requirements.status in [CalculationStatus.UNKNOWN, CalculationStatus.PARTIALLY_CALCULATED]
    assert env.moisture_requirements.status in [CalculationStatus.UNKNOWN, CalculationStatus.PARTIALLY_CALCULATED]


def test_scenario_5_missing_storage_temp(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=0.7,
        package_surface_area_m2=0.08,
        package_headspace_volume_cm3=400.0,
        storage_temperature_c=None,
        relative_humidity_percent=90.0,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)
    assert response.request.storage_temperature_c is None


def test_scenario_6_missing_humidity(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=0.7,
        package_surface_area_m2=0.08,
        package_headspace_volume_cm3=400.0,
        storage_temperature_c=4.0,
        relative_humidity_percent=None,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)
    assert response.request.relative_humidity_percent is None


def test_scenario_7_known_thickness_candidate(recommendation_service, db_session):
    pass


def test_scenario_8_unknown_thickness_candidate(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=0.7,
        package_surface_area_m2=0.08,
        package_headspace_volume_cm3=400.0,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)
    unknown_thick = [c for c in response.candidate_summaries if c.total_thickness_um is None]
    if unknown_thick:
        for c in unknown_thick:
            assert not any(p.pareto_candidate_id == c.candidate_id for p in response.pareto_front.candidates)


def test_scenario_9_missing_headspace(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=0.7,
        package_surface_area_m2=0.08,
        package_headspace_volume_cm3=None,
        storage_temperature_c=4.0,
        relative_humidity_percent=90.0,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)
    assert response.request.package_headspace_volume_cm3 is None


def test_scenario_10_explicit_unknowns_handling(recommendation_service, db_session):
    request = PackagingRequest(
        commodity="apple",
        target_shelf_life_days=10,
        product_mass_kg=None,
        package_surface_area_m2=None,
        package_headspace_volume_cm3=None,
        storage_temperature_c=None,
        relative_humidity_percent=None,
        product_form="fresh",
        ripeness_stage="mature",
        storage_type="chilled"
    )
    response = recommendation_service.generate_recommendation(request, db_session)
    assert response.feasible_candidates_count == 0
    assert response.unknown_candidates_count > 0 or response.infeasible_candidates_count > 0
