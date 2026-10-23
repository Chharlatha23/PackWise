from sqlalchemy import Column, String, Float, Boolean, ForeignKey, Date, Enum, JSON, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base

# SQLAlchemy JSONB fallback for sqlite testing
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(UUID, 'sqlite')
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"

# --- ENUMS ---
class EvidenceClassification(enum.Enum):
    EXPERIMENTAL_LITERATURE_DATA = "EXPERIMENTAL_LITERATURE_DATA"
    MODEL_PREDICTED = "MODEL_PREDICTED"
    SOURCE_MEASURED = "SOURCE_MEASURED"

class VerificationStatus(enum.Enum):
    VERIFIED_EXTRACT = "VERIFIED_EXTRACT"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    PREDICTIVE_ONLY = "PREDICTIVE_ONLY"

class ProcessingState(enum.Enum):
    RAW = "RAW"
    FRESH_CUT = "FRESH_CUT"
    PROCESSED = "PROCESSED"

class GasSpecies(enum.Enum):
    O2 = "O2"
    CO2 = "CO2"

class StructureType(enum.Enum):
    MONOLAYER = "MONOLAYER"
    MULTILAYER = "MULTILAYER"
    COATED = "COATED"

class PropertyType(enum.Enum):
    OTR = "OTR"
    CO2TR = "CO2TR"
    WVTR = "WVTR"

class MissingnessStatus(enum.Enum):
    NOT_REPORTED = "NOT_REPORTED"
    UNKNOWN = "UNKNOWN"
    BELOW_DETECTION_LIMIT = "BELOW_DETECTION_LIMIT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# --- MODELS ---

class Source(Base):
    __tablename__ = 'source'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String, nullable=False, index=True)
    institution = Column(String)
    url = Column(String, unique=True)
    snapshot_date = Column(Date)
    dataset_type = Column(String)
    license = Column(String)
    governance_rule = Column(String)

    evidence_records = relationship("EvidenceRecord", back_populates="source")


class EvidenceRecord(Base):
    __tablename__ = 'evidence_record'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey('source.id'), nullable=False, index=True)
    record_identifier_in_source = Column(String, index=True)
    evidence_classification = Column(Enum(EvidenceClassification), index=True)
    verification_status = Column(Enum(VerificationStatus), index=True)
    literature_references = Column(JSONB)
    outlier_annotation = Column(JSONB)
    synthetic_prediction_warning = Column(String)
    raw_json_payload = Column(JSONB)

    source = relationship("Source", back_populates="evidence_records")
    validations = relationship("ValidationResult", back_populates="evidence_record")
    transformations = relationship("DataTransformation", back_populates="evidence_record")


class ValidationResult(Base):
    __tablename__ = 'validation_result'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    dataset = Column(String)
    field = Column(String)
    rule = Column(String)
    status = Column(String)
    severity = Column(String)
    message = Column(String)
    original_value = Column(String)
    normalized_value = Column(String)

    evidence_record = relationship("EvidenceRecord", back_populates="validations")


class FoodCommodity(Base):
    __tablename__ = 'food_commodity'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity_name = Column(String, nullable=False, index=True)
    scientific_name = Column(String)
    vernacular_name = Column(String)
    food_category = Column(String)
    origin_region = Column(String)
    processing_state = Column(Enum(ProcessingState))


class FoodObservation(Base):
    __tablename__ = 'food_observation'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey('food_commodity.id'), nullable=False, index=True)
    property_name = Column(String, nullable=False, index=True)
    original_value = Column(String)
    value = Column(Float)
    value_min = Column(Float)
    value_max = Column(Float)
    operator = Column(String)
    is_range = Column(Boolean)
    missingness_status = Column(Enum(MissingnessStatus))
    original_unit = Column(String)
    canonical_unit = Column(String)
    measurement_method = Column(String)


class RespirationObservation(Base):
    __tablename__ = 'respiration_observation'
    __table_args__ = (
        CheckConstraint("rate_value >= 0 OR rate_value IS NULL", name="ck_respiration_rate_nonneg"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey('food_commodity.id'), nullable=False, index=True)
    gas_species = Column(Enum(GasSpecies), nullable=False, index=True)
    temperature_c_value = Column(Float)
    temperature_c_min = Column(Float)
    temperature_c_max = Column(Float)
    temperature_c_operator = Column(String)
    original_rate_value = Column(String)
    rate_value = Column(Float)
    rate_min = Column(Float)
    rate_max = Column(Float)
    operator = Column(String)
    is_range = Column(Boolean)
    missingness_status = Column(Enum(MissingnessStatus))
    original_unit = Column(String)
    canonical_unit = Column(String)
    respiratory_quotient = Column(Float)


class PostharvestStorageLimits(Base):
    __tablename__ = 'postharvest_storage_limits'
    __table_args__ = (
        CheckConstraint("optimum_rh_percent >= 0 AND optimum_rh_percent <= 100 OR optimum_rh_percent IS NULL", name="ck_psl_rh_pct"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey('food_commodity.id'), nullable=False, index=True)
    optimum_temperature_c = Column(Float)
    optimum_rh_percent = Column(Float)
    chilling_injury_threshold_c = Column(Float)
    ambient_shelf_life_days = Column(Float)
    map_shelf_life_days = Column(Float)


class PostharvestGasTolerances(Base):
    __tablename__ = 'postharvest_gas_tolerances'
    __table_args__ = (
        CheckConstraint("target_o2_min_percent >= 0 OR target_o2_min_percent IS NULL", name="ck_pgt_o2_min_nonneg"),
        CheckConstraint("target_co2_max_percent >= 0 OR target_co2_max_percent IS NULL", name="ck_pgt_co2_max_nonneg"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    commodity_id = Column(UUID(as_uuid=True), ForeignKey('food_commodity.id'), nullable=False, index=True)
    target_o2_min_percent = Column(Float)
    target_o2_max_percent = Column(Float)
    target_co2_min_percent = Column(Float)
    target_co2_max_percent = Column(Float)
    min_o2_fermentation_limit_percent = Column(Float)
    max_co2_injury_limit_percent = Column(Float)


class PackagingMaterial(Base):
    __tablename__ = 'packaging_material'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_name = Column(String, nullable=False, index=True)
    brand_grade = Column(String)
    structure_type = Column(Enum(StructureType))
    layer_sequence = Column(JSONB)


class MaterialBarrierObservation(Base):
    __tablename__ = 'material_barrier_observation'
    __table_args__ = (
        CheckConstraint("value >= 0 OR value IS NULL", name="ck_mbo_value_nonneg"),
        CheckConstraint("thickness_value >= 0 OR thickness_value IS NULL", name="ck_mbo_thickness_nonneg"),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    material_id = Column(UUID(as_uuid=True), ForeignKey('packaging_material.id'), nullable=False, index=True)
    property_type = Column(Enum(PropertyType), nullable=False, index=True)
    original_value = Column(String)
    value = Column(Float)
    value_min = Column(Float)
    value_max = Column(Float)
    operator = Column(String)
    is_range = Column(Boolean)
    missingness_status = Column(Enum(MissingnessStatus))
    original_unit = Column(String)
    canonical_unit = Column(String)
    test_temperature_c_value = Column(Float)
    test_temperature_c_operator = Column(String)
    test_rh_percent_value = Column(Float)
    test_rh_percent_operator = Column(String)
    thickness_value = Column(Float)
    thickness_unit = Column(String)
    test_method = Column(String)


class MicrobialOrganism(Base):
    __tablename__ = 'microbial_organism'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organism_name = Column(String, nullable=False, index=True)
    organism_type = Column(String)
    strain = Column(String)


class MicrobialCardinalParameters(Base):
    __tablename__ = 'microbial_cardinal_parameters'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    organism_id = Column(UUID(as_uuid=True), ForeignKey('microbial_organism.id'), nullable=False, index=True)
    temperature_min_c = Column(Float)
    temperature_opt_c = Column(Float)
    temperature_max_c = Column(Float)
    water_activity_aw_min = Column(Float)
    ph_min = Column(Float)
    ph_opt = Column(Float)
    ph_max = Column(Float)


class MicrobialGrowthKinetics(Base):
    __tablename__ = 'microbial_growth_kinetics'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    organism_id = Column(UUID(as_uuid=True), ForeignKey('microbial_organism.id'), nullable=False, index=True)
    temperature_c_value = Column(Float)
    temperature_c_operator = Column(String)
    ph_value = Column(Float)
    ph_operator = Column(String)
    water_activity_aw_value = Column(Float)
    water_activity_aw_operator = Column(String)
    specific_growth_rate_mu_max_1_h = Column(Float)
    lag_time_lambda_h = Column(Float)
    atmosphere_condition = Column(String)
    missingness_status = Column(Enum(MissingnessStatus))


class MicrobialGasInhibitionResponse(Base):
    __tablename__ = 'microbial_gas_inhibition_response'
    __table_args__ = (
        CheckConstraint(
            "minimum_co2_inhibition_percent >= 0 AND minimum_co2_inhibition_percent <= 100 OR minimum_co2_inhibition_percent IS NULL",
            name="ck_mgir_co2_pct"
        ),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    organism_id = Column(UUID(as_uuid=True), ForeignKey('microbial_organism.id'), nullable=False, index=True)
    co2_sensitivity = Column(String)
    minimum_co2_inhibition_percent = Column(Float)
    notes = Column(String)


class DataTransformation(Base):
    __tablename__ = 'data_transformation'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey('evidence_record.id'), nullable=False, index=True)
    field = Column(String)
    original_value = Column(String)
    transformed_value = Column(String)
    transformation_type = Column(String)
    rule_id = Column(String)

    evidence_record = relationship("EvidenceRecord", back_populates="transformations")
