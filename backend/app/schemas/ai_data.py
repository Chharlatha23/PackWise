"""
Phase 3A — Implementation Layer 1: AI Data & Provenance Foundation.

Provides structured schemas, taxonomies, and validation rules for:
- AIDataStatusEnum (locked 8-status taxonomy)
- AIProvenanceRecord (preserves provenance, evidence, and context)
- AIFeatureValue (epistemic feature representation with UNKNOWN protection)
- AIDataRecord (joint vs single-domain record classification)
- Helper transformation functions for food evidence, material evidence, and feedback.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, root_validator, validator

from app.schemas.inference import UncertaintyLevelEnum, PropertyInferenceProfile, InferredProperty
from app.schemas.food_evidence import FoodEvidenceRecord
from app.schemas.material_evidence import MaterialPropertyEvidence


class AIDataStatusEnum(str, Enum):
    """
    Locked taxonomy for AI data status classification (Phase 3A Layer 1).
    MUST support exactly these 8 statuses without silent renaming or merging.
    """
    REAL_EMPIRICAL = "REAL_EMPIRICAL"
    REAL_LITERATURE = "REAL_LITERATURE"
    FOOD_ONLY = "FOOD_ONLY"
    PACKAGING_ONLY = "PACKAGING_ONLY"
    MODEL_PREDICTED = "MODEL_PREDICTED"
    SYNTHETIC = "SYNTHETIC"
    REAL_PLUS_MODEL = "REAL_PLUS_MODEL"
    UNKNOWN = "UNKNOWN"


class AIProvenanceRecord(BaseModel):
    """
    Captures complete scientific provenance and generation metadata for AI data records.
    """
    source_id: Optional[str] = Field(default=None, description="Unique identifier of data source, DOI, or trial ID.")
    source_type: Optional[str] = Field(default=None, description="Type of source e.g. 'lab_trial', 'journal_paper', 'physics_emulator'.")
    data_status: AIDataStatusEnum = Field(..., description="Locked Phase 3A data status taxonomy value.")
    epistemic_level: UncertaintyLevelEnum = Field(
        default=UncertaintyLevelEnum.LEVEL_D,
        description="Phase 2 scientific uncertainty classification level (LEVEL_D, LEVEL_A, LEVEL_B)."
    )
    physics_model_version: Optional[str] = Field(default=None, description="Physics engine version if model-derived/synthetic.")
    generation_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of record generation.")
    citation_or_doi: Optional[str] = Field(default=None, description="Bibliographic reference or DOI if literature-derived.")
    scenario_parameters: Optional[Dict[str, Any]] = Field(default=None, description="Scenario parameters for simulation/model runs.")
    food_context: Optional[Dict[str, Any]] = Field(default=None, description="Associated food commodity metadata.")
    packaging_context: Optional[Dict[str, Any]] = Field(default=None, description="Associated packaging material metadata.")
    storage_context: Optional[Dict[str, Any]] = Field(default=None, description="Storage conditions (temperature, RH, duration).")
    parent_record_id: Optional[str] = Field(default=None, description="Parent or source record ID if derived/synthesized.")


class AIFeatureValue(BaseModel):
    """
    Single property or feature representation for AI pipelines with explicit
    missingness protection and epistemic uncertainty mapping.
    
    STRICT SCIENTIFIC INVARIANT (Phase 3A Layer 1):
    - UNKNOWN / missing feature values MUST NEVER silently become numeric 0.0.
    - If status is UNKNOWN, epistemic_level is LEVEL_D, or is_missing is True,
      value MUST be None. Attempting to set numeric 0.0 while missing raises ValueError.
    """
    feature_name: str = Field(..., description="Feature property identifier.")
    value: Optional[float] = Field(default=None, description="Numeric value. NULL if missing/unknown.")
    is_missing: bool = Field(default=True, description="Explicit boolean missingness indicator.")
    unit: Optional[str] = Field(default=None, description="Physical unit of measurement.")
    data_status: AIDataStatusEnum = Field(default=AIDataStatusEnum.UNKNOWN, description="Feature-level data status.")
    epistemic_level: UncertaintyLevelEnum = Field(
        default=UncertaintyLevelEnum.LEVEL_D,
        description="Epistemic uncertainty level (LEVEL_D, LEVEL_A, LEVEL_B)."
    )
    evidence_interval: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Level B evidence-supported interval bounds (lower, upper). NOT quantiles."
    )
    confidence_heuristic: Optional[float] = Field(
        default=None,
        description="Heuristic context confidence score [0.0 - 1.0] (NOT a probability)."
    )

    @root_validator(pre=True)
    def handle_missingness_pre(cls, values):
        val = values.get("value")
        status = values.get("data_status")
        epistemic = values.get("epistemic_level")
        is_missing = values.get("is_missing")

        # If value is None, force is_missing=True, data_status default UNKNOWN if not provided, epistemic LEVEL_D
        if val is None:
            values["is_missing"] = True
            if status is None:
                values["data_status"] = AIDataStatusEnum.UNKNOWN
            if epistemic is None:
                values["epistemic_level"] = UncertaintyLevelEnum.LEVEL_D
        else:
            # If value is provided, default is_missing to False unless explicitly passed True
            if is_missing is None:
                values["is_missing"] = False

        return values

    @root_validator(skip_on_failure=True)
    def enforce_unknown_integrity(cls, values):
        val = values.get("value")
        status = values.get("data_status")
        epistemic = values.get("epistemic_level")
        is_missing = values.get("is_missing")

        # Strict check: UNKNOWN or LEVEL_D or is_missing=True MUST have value=None
        if status == AIDataStatusEnum.UNKNOWN or epistemic == UncertaintyLevelEnum.LEVEL_D or is_missing:
            if val is not None:
                raise ValueError(
                    f"UNKNOWN/missing feature '{values.get('feature_name')}' cannot contain numeric value {val}. "
                    "Missing values must be None to prevent silent zero conversion."
                )
        return values

    def to_numeric_with_mask(self) -> Tuple[bool, Optional[float]]:
        """
        Safely returns (is_present_mask, numeric_value).
        If missing, returns (False, None). Downstream callers MUST handle the mask explicitly.
        """
        if self.is_missing or self.value is None:
            return (False, None)
        return (True, self.value)

    def to_numeric_strict(self) -> float:
        """
        Returns numeric value if present.
        Raises ValueError if feature is missing/UNKNOWN to prevent silent zero substitution.
        """
        if self.is_missing or self.value is None:
            raise ValueError(
                f"Feature '{self.feature_name}' is UNKNOWN/missing (data_status={self.data_status.value}, "
                f"epistemic={self.epistemic_level.value}). Cannot convert to numeric without explicit missingness mask."
            )
        return self.value


class AIDataRecord(BaseModel):
    """
    Complete AI Data Record representation for model training, dataset building,
    and audit tracking across food, packaging, and joint observations.
    """
    record_id: str = Field(..., description="Unique record identifier.")
    data_status: AIDataStatusEnum = Field(..., description="Locked status taxonomy.")
    epistemic_level: UncertaintyLevelEnum = Field(
        default=UncertaintyLevelEnum.LEVEL_D,
        description="Overall record epistemic classification."
    )
    provenance: AIProvenanceRecord = Field(..., description="Provenance metadata.")
    
    food_features: Dict[str, AIFeatureValue] = Field(
        default_factory=dict,
        description="Food-side features."
    )
    packaging_features: Dict[str, AIFeatureValue] = Field(
        default_factory=dict,
        description="Packaging-side features."
    )
    outcome_features: Dict[str, AIFeatureValue] = Field(
        default_factory=dict,
        description="Observed or predicted trial outcomes (shelf_life, barrier rates, etc.)."
    )

    @property
    def is_real_empirical(self) -> bool:
        """True if record originates from real empirical lab observation."""
        return self.data_status == AIDataStatusEnum.REAL_EMPIRICAL

    @property
    def is_real_literature(self) -> bool:
        """True if record originates from published literature."""
        return self.data_status == AIDataStatusEnum.REAL_LITERATURE

    @property
    def is_real_evidence(self) -> bool:
        """True if record originates from real empirical observation or published literature."""
        return self.data_status in (AIDataStatusEnum.REAL_EMPIRICAL, AIDataStatusEnum.REAL_LITERATURE)

    @property
    def is_model_generated(self) -> bool:
        """True if record is generated by model simulation or synthetic coverage sampler."""
        return self.data_status in (
            AIDataStatusEnum.MODEL_PREDICTED,
            AIDataStatusEnum.SYNTHETIC,
            AIDataStatusEnum.REAL_PLUS_MODEL,
        )

    @property
    def is_joint_observation(self) -> bool:
        """
        True if record represents a genuine joint observation containing food, packaging, AND outcome features,
        and is NOT explicitly single-domain (FOOD_ONLY, PACKAGING_ONLY, UNKNOWN).
        """
        if self.data_status in (AIDataStatusEnum.FOOD_ONLY, AIDataStatusEnum.PACKAGING_ONLY, AIDataStatusEnum.UNKNOWN):
            return False
        
        has_food = any(not f.is_missing for f in self.food_features.values())
        has_pkg = any(not f.is_missing for f in self.packaging_features.values())
        has_outcome = any(not f.is_missing for f in self.outcome_features.values())
        return has_food and has_pkg and has_outcome

    @property
    def is_food_only(self) -> bool:
        """True if record contains only food property information without joint packaging outcomes."""
        if self.data_status == AIDataStatusEnum.FOOD_ONLY:
            return True
        has_food = any(not f.is_missing for f in self.food_features.values())
        has_pkg = any(not f.is_missing for f in self.packaging_features.values())
        has_outcome = any(not f.is_missing for f in self.outcome_features.values())
        return has_food and not (has_pkg and has_outcome)

    @property
    def is_packaging_only(self) -> bool:
        """True if record contains only packaging property information without joint food outcomes."""
        if self.data_status == AIDataStatusEnum.PACKAGING_ONLY:
            return True
        has_food = any(not f.is_missing for f in self.food_features.values())
        has_pkg = any(not f.is_missing for f in self.packaging_features.values())
        has_outcome = any(not f.is_missing for f in self.outcome_features.values())
        return has_pkg and not (has_food and has_outcome)

    def validate_unknown_integrity(self) -> bool:
        """
        Audits all contained features to verify that no UNKNOWN / LEVEL_D value was silently
        coerced to a numeric 0.0 or non-None float. Returns True if valid.
        """
        all_features = [
            *self.food_features.values(),
            *self.packaging_features.values(),
            *self.outcome_features.values(),
        ]
        for feat in all_features:
            if feat.data_status == AIDataStatusEnum.UNKNOWN or feat.epistemic_level == UncertaintyLevelEnum.LEVEL_D or feat.is_missing:
                if feat.value is not None:
                    return False
        return True


# --- CONVERTER / HELPER UTILITIES ---

def from_food_evidence(record: FoodEvidenceRecord) -> AIDataRecord:
    """Converts a FoodEvidenceRecord to an AIDataRecord tagged as FOOD_ONLY."""
    rec_id = getattr(record, "id", None) or f"{record.commodity}_{record.property}"
    source_type_val = record.source_type.value if hasattr(record.source_type, "value") else str(record.source_type or "food_database")
    product_form_val = record.product_form.value if hasattr(record.product_form, "value") else str(record.product_form) if record.product_form else None
    
    prov = AIProvenanceRecord(
        source_id=str(rec_id),
        source_type=source_type_val,
        data_status=AIDataStatusEnum.FOOD_ONLY,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A if record.value is not None else UncertaintyLevelEnum.LEVEL_D,
        citation_or_doi=record.DOI or record.source_title,
        food_context={
            "commodity": record.commodity,
            "scientific_name": getattr(record, "scientific_name", None),
            "variety": record.variety,
            "product_form": product_form_val,
            "temperature_c": record.temperature,
        },
    )

    is_missing = record.value is None
    val = record.value if not is_missing else None
    epistemic = UncertaintyLevelEnum.LEVEL_A if not is_missing else UncertaintyLevelEnum.LEVEL_D
    
    # Check for evidence interval if minimum_value/maximum_value provided
    interval = None
    if record.minimum_value is not None and record.maximum_value is not None:
        interval = (record.minimum_value, record.maximum_value)
        epistemic = UncertaintyLevelEnum.LEVEL_B

    prop_name = record.property.value if hasattr(record.property, "value") else str(record.property or "unknown_property")

    food_feat = AIFeatureValue(
        feature_name=prop_name,
        value=val,
        is_missing=is_missing,
        unit=record.unit,
        data_status=AIDataStatusEnum.FOOD_ONLY,
        epistemic_level=epistemic,
        evidence_interval=interval,
    )

    return AIDataRecord(
        record_id=f"AIDATA-FOOD-{rec_id}",
        data_status=AIDataStatusEnum.FOOD_ONLY,
        epistemic_level=epistemic,
        provenance=prov,
        food_features={food_feat.feature_name: food_feat},
    )


def from_material_evidence(record: MaterialPropertyEvidence) -> AIDataRecord:
    """Converts a MaterialPropertyEvidence record to an AIDataRecord tagged as PACKAGING_ONLY."""
    rec_id = getattr(record, "id", None) or f"mat_{record.property}"
    source_type_val = record.source_type.value if hasattr(record.source_type, "value") else str(record.source_type or "material_database")
    mat_name = getattr(record, "material_name", None)
    poly_class = getattr(record, "polymer_class", None)

    prov = AIProvenanceRecord(
        source_id=str(rec_id),
        source_type=source_type_val,
        data_status=AIDataStatusEnum.PACKAGING_ONLY,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A if record.value is not None else UncertaintyLevelEnum.LEVEL_D,
        citation_or_doi=record.DOI or record.source_title,
        packaging_context={
            "material_name": mat_name,
            "polymer_class": poly_class,
        },
    )

    is_missing = record.value is None
    val = record.value if not is_missing else None
    epistemic = UncertaintyLevelEnum.LEVEL_A if not is_missing else UncertaintyLevelEnum.LEVEL_D
    
    interval = None
    if record.minimum_value is not None and record.maximum_value is not None:
        interval = (record.minimum_value, record.maximum_value)
        epistemic = UncertaintyLevelEnum.LEVEL_B

    prop_name = record.property.value if hasattr(record.property, "value") else str(record.property or "unknown_property")

    pkg_feat = AIFeatureValue(
        feature_name=prop_name,
        value=val,
        is_missing=is_missing,
        unit=record.unit,
        data_status=AIDataStatusEnum.PACKAGING_ONLY,
        epistemic_level=epistemic,
        evidence_interval=interval,
    )

    return AIDataRecord(
        record_id=f"AIDATA-PKG-{rec_id}",
        data_status=AIDataStatusEnum.PACKAGING_ONLY,
        epistemic_level=epistemic,
        provenance=prov,
        packaging_features={pkg_feat.feature_name: pkg_feat},
    )


def from_inferred_profile(profile: PropertyInferenceProfile) -> AIDataRecord:
    """Converts an InferredPropertyProfile into a structured AIDataRecord."""
    prov = AIProvenanceRecord(
        source_id=f"PROFILE-{profile.commodity}",
        source_type="property_inference_engine",
        data_status=AIDataStatusEnum.FOOD_ONLY,
        epistemic_level=UncertaintyLevelEnum.LEVEL_A if profile.properties else UncertaintyLevelEnum.LEVEL_D,
        food_context={
            "commodity": profile.commodity,
            "variety": profile.variety,
            "product_form": profile.product_form,
            "storage_temperature_c": profile.storage_temperature_c,
            "relative_humidity_percent": profile.relative_humidity_percent,
        },
    )

    food_features = {}
    for prop_name, prop in profile.properties.items():
        is_missing = prop.value is None or prop.uncertainty_level == UncertaintyLevelEnum.LEVEL_D
        val = prop.value if not is_missing else None
        
        feat = AIFeatureValue(
            feature_name=prop_name,
            value=val,
            is_missing=is_missing,
            unit=prop.unit,
            data_status=AIDataStatusEnum.FOOD_ONLY,
            epistemic_level=prop.uncertainty_level,
            evidence_interval=prop.evidence_interval,
            confidence_heuristic=prop.confidence,
        )
        food_features[prop_name] = feat

    overall_epistemic = UncertaintyLevelEnum.LEVEL_D
    if any(f.epistemic_level == UncertaintyLevelEnum.LEVEL_B for f in food_features.values()):
        overall_epistemic = UncertaintyLevelEnum.LEVEL_B
    elif any(f.epistemic_level == UncertaintyLevelEnum.LEVEL_A for f in food_features.values()):
        overall_epistemic = UncertaintyLevelEnum.LEVEL_A

    return AIDataRecord(
        record_id=f"AIDATA-INFERRED-{profile.commodity}",
        data_status=AIDataStatusEnum.FOOD_ONLY,
        epistemic_level=overall_epistemic,
        provenance=prov,
        food_features=food_features,
    )
