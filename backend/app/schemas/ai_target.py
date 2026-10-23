"""
Phase 3A — Implementation Layer 2: Surrogate-Target Preparation Foundation.

Provides structured schemas, classifications, target-value audit mechanisms, and
preparation functions connecting Layer 1 AIDataRecord objects to candidate AI target representations.

Key Components:
- AITargetEnum: Inventory of exactly 4 candidate AI targets (OTR_pkg, WVTR_pkg, ShelfLife_est, MAP_CO2_peak).
- AITargetClassificationEnum: Target classifications (PRIMARY_SURROGATE, SECONDARY_SUPPORTING, PHYSICS_ONLY, DEFERRED).
- AITargetCriteriaAssessment: 10-criteria audit assessment structure.
- AITargetAuditResult: Audit rationale record for target classification.
- AITargetPreparationRecord: Prepared candidate target representation preserving full Layer 1 provenance.
- AITargetPreparationSet: Prepared candidate target set for an AIDataRecord.
- get_default_target_audit_registry: Target audit registry capturing rationale across all 4 targets.
- prepare_targets_from_ai_data_record: Data flow transformer from AIDataRecord to AITargetPreparationSet.

STRICT SCIENTIFIC BOUNDARIES:
- Does NOT build or train surrogate models (No LightGBM, XGBoost, GPR, MLP).
- Does NOT implement Level C probability calibration or quantile estimations (No P05/P50/P95).
- Does NOT convert missing/UNKNOWN targets to numeric 0.0 or defaults.
- Does NOT alter Layer 1 provenance or data-status semantics.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, root_validator

from app.schemas.inference import UncertaintyLevelEnum
from app.schemas.ai_data import (
    AIDataStatusEnum,
    AIProvenanceRecord,
    AIFeatureValue,
    AIDataRecord,
)


class AITargetEnum(str, Enum):
    """
    Candidate Target Inventory for Phase 3A Layer 2.
    Contains EXACTLY the 4 approved candidate AI targets.
    """
    OTR_PKG = "OTR_pkg"
    WVTR_PKG = "WVTR_pkg"
    SHELF_LIFE_EST = "ShelfLife_est"
    MAP_CO2_PEAK = "MAP_CO2_peak"


class AITargetClassificationEnum(str, Enum):
    """
    Explicit classification categories for candidate AI targets (Phase 3A Layer 2).
    """
    PRIMARY_SURROGATE = "PRIMARY_SURROGATE"
    SECONDARY_SUPPORTING = "SECONDARY_SUPPORTING"
    PHYSICS_ONLY = "PHYSICS_ONLY"
    DEFERRED = "DEFERRED"


class AITargetCriteriaAssessment(BaseModel):
    """
    Evaluation of a candidate AI target against the 10 approved scientific & computational audit criteria.
    """
    is_cheap_deterministic: bool = Field(..., description="1. Is the quantity cheap to calculate deterministically?")
    physics_eval_cost: str = Field(..., description="2. Computational cost of exact physics evaluation (low/medium/high).")
    has_meaningful_nonlinearity: bool = Field(..., description="3. Does the quantity contain meaningful nonlinearity?")
    accelerates_inverse_design: bool = Field(..., description="4. Does surrogate approximation materially accelerate inverse design?")
    contributes_to_candidate_ranking: bool = Field(..., description="5. Does it contribute meaningfully to candidate ranking?")
    is_redundant: bool = Field(..., description="6. Is it redundant with other targets?")
    suitable_training_data_available: bool = Field(..., description="7. Is suitable training/development data available?")
    independent_validation_possible: bool = Field(..., description="8. Is independent validation possible?")
    surrogate_error_impacts_decisions: bool = Field(..., description="9. Would surrogate error materially affect search decisions?")
    meaningful_search_acceleration: bool = Field(..., description="10. Does approximating it provide meaningful search acceleration?")


class AITargetAuditResult(BaseModel):
    """
    Target-value audit record capturing explicit scientific rationale and 10-criteria assessment.
    """
    target_id: AITargetEnum = Field(..., description="Target identifier.")
    classification: AITargetClassificationEnum = Field(..., description="Explicit target classification.")
    assessment: AITargetCriteriaAssessment = Field(..., description="10-criteria audit assessment.")
    rationale: str = Field(..., description="Explicit scientific and computational justification.")
    limitations_or_data_gaps: Optional[str] = Field(default=None, description="Explicit record of data or model limitations.")
    reassessment_allowed: bool = Field(default=True, description="Indicates if target classification can be reassessed in future layers.")


def get_default_target_audit_registry() -> Dict[AITargetEnum, AITargetAuditResult]:
    """
    Returns the explicit, audit-backed target classification registry for all 4 candidate targets.
    Evaluated against the 10 approved Phase 3A audit criteria.
    """
    return {
        AITargetEnum.OTR_PKG: AITargetAuditResult(
            target_id=AITargetEnum.OTR_PKG,
            classification=AITargetClassificationEnum.SECONDARY_SUPPORTING,
            assessment=AITargetCriteriaAssessment(
                is_cheap_deterministic=True,
                physics_eval_cost="low",
                has_meaningful_nonlinearity=False,
                accelerates_inverse_design=False,
                contributes_to_candidate_ranking=True,
                is_redundant=False,
                suitable_training_data_available=True,
                independent_validation_possible=True,
                surrogate_error_impacts_decisions=False,
                meaningful_search_acceleration=False,
            ),
            rationale=(
                "Package OTR (OTR_pkg) is calculated deterministically from film thickness and material permeability "
                "with trivial CPU cost O(1). Surrogate modeling does not accelerate search over exact physics, "
                "so it is classified as a SECONDARY_SUPPORTING target for barrier property tracking."
            ),
            limitations_or_data_gaps="Layering effects are computed deterministically via series barrier equations.",
            reassessment_allowed=True,
        ),
        AITargetEnum.WVTR_PKG: AITargetAuditResult(
            target_id=AITargetEnum.WVTR_PKG,
            classification=AITargetClassificationEnum.SECONDARY_SUPPORTING,
            assessment=AITargetCriteriaAssessment(
                is_cheap_deterministic=True,
                physics_eval_cost="low",
                has_meaningful_nonlinearity=False,
                accelerates_inverse_design=False,
                contributes_to_candidate_ranking=True,
                is_redundant=False,
                suitable_training_data_available=True,
                independent_validation_possible=True,
                surrogate_error_impacts_decisions=False,
                meaningful_search_acceleration=False,
            ),
            rationale=(
                "Package WVTR (WVTR_pkg) is calculated deterministically via exact water vapor permeation equations. "
                "Microsecond evaluation cost means surrogate approximation provides negligible speedup; "
                "retained as SECONDARY_SUPPORTING target."
            ),
            limitations_or_data_gaps="Relative humidity dependence curves require tabular interpolation.",
            reassessment_allowed=True,
        ),
        AITargetEnum.SHELF_LIFE_EST: AITargetAuditResult(
            target_id=AITargetEnum.SHELF_LIFE_EST,
            classification=AITargetClassificationEnum.PRIMARY_SURROGATE,
            assessment=AITargetCriteriaAssessment(
                is_cheap_deterministic=False,
                physics_eval_cost="high",
                has_meaningful_nonlinearity=True,
                accelerates_inverse_design=True,
                contributes_to_candidate_ranking=True,
                is_redundant=False,
                suitable_training_data_available=True,
                independent_validation_possible=True,
                surrogate_error_impacts_decisions=True,
                meaningful_search_acceleration=True,
            ),
            rationale=(
                "Coupled multi-mechanism shelf-life evaluation (ShelfLife_est) requires iterative ODE numerical integration "
                "across storage time. High non-linearity (Gompertz kinetics, Arrhenius temperature dependence) and non-trivial "
                "computational cost make ShelfLife_est the PRIMARY_SURROGATE target to accelerate inverse design optimization loops."
            ),
            limitations_or_data_gaps="Requires comprehensive coverage across temperature and RH storage scenarios.",
            reassessment_allowed=True,
        ),
        AITargetEnum.MAP_CO2_PEAK: AITargetAuditResult(
            target_id=AITargetEnum.MAP_CO2_PEAK,
            classification=AITargetClassificationEnum.DEFERRED,
            assessment=AITargetCriteriaAssessment(
                is_cheap_deterministic=False,
                physics_eval_cost="medium",
                has_meaningful_nonlinearity=True,
                accelerates_inverse_design=True,
                contributes_to_candidate_ranking=True,
                is_redundant=False,
                suitable_training_data_available=False,
                independent_validation_possible=True,
                surrogate_error_impacts_decisions=True,
                meaningful_search_acceleration=True,
            ),
            rationale=(
                "Dynamic MAP headspace CO2 peak estimation (MAP_CO2_peak) requires transient gas balance integration. "
                "While non-linear and computationally non-trivial, current open-access datasets lack sufficient dynamic "
                "headspace CO2 profile measurements across varied commodities. DEFERRED pending dedicated dynamic MAP experimental dataset collection."
            ),
            limitations_or_data_gaps="Empirical headspace gas trial data is sparse in current dataset.",
            reassessment_allowed=True,
        ),
    }


class AITargetPreparationRecord(BaseModel):
    """
    Prepared candidate target representation for Phase 3A Layer 2.
    
    Preserves complete scientific traceability and provenance from Layer 1 AIDataRecord
    to downstream surrogate target dataset preparation.
    
    STRICT SCIENTIFIC INVARIANTS:
    - UNKNOWN / missing target values MUST NEVER silently become numeric 0.0.
    - If is_missing is True, epistemic_level is LEVEL_D, or status is UNKNOWN, value MUST be None.
    - Level B targets preserve interval/scenario data WITHOUT quantile conversion (no P05/P50/P95).
    - Level C (probability calibration) is strictly forbidden.
    """
    target_id: AITargetEnum = Field(..., description="Target identifier (OTR_pkg, WVTR_pkg, ShelfLife_est, MAP_CO2_peak).")
    value: Optional[float] = Field(default=None, description="Numeric target value. None if missing/unknown.")
    is_missing: bool = Field(default=True, description="Explicit boolean missingness indicator.")
    unit: Optional[str] = Field(default=None, description="Physical unit of measurement.")
    classification: AITargetClassificationEnum = Field(..., description="Target classification.")
    epistemic_level: UncertaintyLevelEnum = Field(
        default=UncertaintyLevelEnum.LEVEL_D,
        description="Phase 2 uncertainty level (LEVEL_A, LEVEL_B, LEVEL_D)."
    )
    data_status: AIDataStatusEnum = Field(default=AIDataStatusEnum.UNKNOWN, description="Locked 8-status taxonomy value.")
    provenance: AIProvenanceRecord = Field(..., description="Full Layer 1 AIProvenanceRecord.")
    
    # Preserved Layer 1 context inputs
    food_context: Optional[Dict[str, Any]] = Field(default=None, description="Food commodity context.")
    packaging_context: Optional[Dict[str, Any]] = Field(default=None, description="Packaging material context.")
    storage_context: Optional[Dict[str, Any]] = Field(default=None, description="Storage conditions context.")
    citation_or_doi: Optional[str] = Field(default=None, description="Citation or DOI reference.")
    physics_model_version: Optional[str] = Field(default=None, description="Physics engine version.")
    applicability_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Applicability or scenario metadata.")
    
    # Epistemic Level B preserved structure
    evidence_interval: Optional[Tuple[float, float]] = Field(default=None, description="Level B evidence interval (lower, upper bounds). NOT quantiles.")
    scenario_parameters: Optional[Dict[str, Any]] = Field(default=None, description="Level B scenario parameters.")
    
    # Target-Value Audit rationale
    audit_rationale: Optional[str] = Field(default=None, description="Target audit rationale for assigned classification.")

    @root_validator(pre=True)
    def handle_missingness_pre(cls, values):
        val = values.get("value")
        status = values.get("data_status")
        epistemic = values.get("epistemic_level")
        is_missing = values.get("is_missing")

        if val is None:
            values["is_missing"] = True
            if status is None:
                values["data_status"] = AIDataStatusEnum.UNKNOWN
            if epistemic is None:
                values["epistemic_level"] = UncertaintyLevelEnum.LEVEL_D
        else:
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
                    f"UNKNOWN/missing target '{values.get('target_id')}' cannot contain numeric value {val}. "
                    "Missing targets must be None to prevent silent zero conversion."
                )
        return values

    def is_valid_training_target(self) -> bool:
        """
        Returns True if target is eligible and valid as a surrogate training target.
        Must be PRIMARY_SURROGATE, non-missing, non-UNKNOWN, and non-LEVEL_D.
        """
        if self.is_missing or self.value is None:
            return False
        if self.data_status == AIDataStatusEnum.UNKNOWN or self.epistemic_level == UncertaintyLevelEnum.LEVEL_D:
            return False
        if self.classification != AITargetClassificationEnum.PRIMARY_SURROGATE:
            return False
        return True

    def to_numeric_with_mask(self) -> Tuple[bool, Optional[float]]:
        """Safely returns (is_present_mask, numeric_value). If missing, returns (False, None)."""
        if self.is_missing or self.value is None:
            return (False, None)
        return (True, self.value)

    def to_numeric_strict(self) -> float:
        """
        Returns numeric target value if valid.
        Raises ValueError if missing/UNKNOWN to prevent silent zero substitution.
        """
        if self.is_missing or self.value is None:
            target_name = self.target_id.value if hasattr(self.target_id, "value") else str(self.target_id)
            status_name = self.data_status.value if hasattr(self.data_status, "value") else str(self.data_status)
            epistemic_name = self.epistemic_level.value if hasattr(self.epistemic_level, "value") else str(self.epistemic_level)
            raise ValueError(
                f"Target '{target_name}' is UNKNOWN/missing (data_status={status_name}, "
                f"epistemic={epistemic_name}). Cannot convert to numeric without explicit missingness mask."
            )
        return self.value


class AITargetPreparationSet(BaseModel):
    """
    Complete collection of candidate targets prepared from a Layer 1 AIDataRecord.
    Maintains 1-to-1 provenance link to parent record.
    """
    record_id: str = Field(..., description="Parent AIDataRecord identifier.")
    parent_data_status: AIDataStatusEnum = Field(..., description="Parent record status.")
    parent_epistemic_level: UncertaintyLevelEnum = Field(..., description="Parent record epistemic level.")
    provenance: AIProvenanceRecord = Field(..., description="Parent provenance record.")
    targets: Dict[AITargetEnum, AITargetPreparationRecord] = Field(..., description="Prepared candidate targets indexed by AITargetEnum.")

    def get_primary_surrogate_targets(self) -> Dict[AITargetEnum, AITargetPreparationRecord]:
        """Filters set to only PRIMARY_SURROGATE targets."""
        return {tid: target for tid, target in self.targets.items() if target.classification == AITargetClassificationEnum.PRIMARY_SURROGATE}

    def get_trainable_targets(self) -> Dict[AITargetEnum, AITargetPreparationRecord]:
        """Returns targets eligible for valid surrogate training (PRIMARY_SURROGATE, present, non-UNKNOWN)."""
        return {tid: target for tid, target in self.targets.items() if target.is_valid_training_target()}


def prepare_targets_from_ai_data_record(
    record: AIDataRecord,
    audit_registry: Optional[Dict[AITargetEnum, AITargetAuditResult]] = None,
) -> AITargetPreparationSet:
    """
    Transforms a Layer 1 AIDataRecord into a structured Layer 2 AITargetPreparationSet.
    Preserves all Layer 1 provenance, data status, epistemic uncertainty, and context metadata.
    """
    registry = audit_registry or get_default_target_audit_registry()
    prepared_targets: Dict[AITargetEnum, AITargetPreparationRecord] = {}

    target_feature_keys = {
        AITargetEnum.OTR_PKG: ["otr", "OTR_pkg", "oxygen_transmission_rate", "otr_pkg"],
        AITargetEnum.WVTR_PKG: ["wvtr", "WVTR_pkg", "water_vapor_transmission_rate", "wvtr_pkg"],
        AITargetEnum.SHELF_LIFE_EST: ["observed_shelf_life", "shelf_life", "ShelfLife_est", "shelf_life_days", "estimated_shelf_life"],
        AITargetEnum.MAP_CO2_PEAK: ["map_co2_peak", "MAP_CO2_peak", "co2_peak", "peak_co2"],
    }

    default_units = {
        AITargetEnum.OTR_PKG: "cm3/(m2*day*atm)",
        AITargetEnum.WVTR_PKG: "g/(m2*day)",
        AITargetEnum.SHELF_LIFE_EST: "days",
        AITargetEnum.MAP_CO2_PEAK: "kPa",
    }

    all_features = {}
    all_features.update(record.food_features)
    all_features.update(record.packaging_features)
    all_features.update(record.outcome_features)

    for target_id in AITargetEnum:
        audit_info = registry.get(target_id)
        classification = audit_info.classification if audit_info else AITargetClassificationEnum.DEFERRED
        rationale = audit_info.rationale if audit_info else None

        matched_feature: Optional[AIFeatureValue] = None
        search_keys = target_feature_keys.get(target_id, [])
        for k in search_keys:
            if k in all_features:
                matched_feature = all_features[k]
                break

        if matched_feature is not None and not matched_feature.is_missing and matched_feature.value is not None:
            val = matched_feature.value
            is_missing = False
            unit = matched_feature.unit or default_units.get(target_id)
            epistemic = matched_feature.epistemic_level
            target_status = matched_feature.data_status if matched_feature.data_status != AIDataStatusEnum.UNKNOWN else record.data_status
            evidence_interval = matched_feature.evidence_interval
        else:
            val = None
            is_missing = True
            unit = default_units.get(target_id)
            epistemic = UncertaintyLevelEnum.LEVEL_D
            target_status = AIDataStatusEnum.UNKNOWN
            evidence_interval = None

        target_rec = AITargetPreparationRecord(
            target_id=target_id,
            value=val,
            is_missing=is_missing,
            unit=unit,
            classification=classification,
            epistemic_level=epistemic,
            data_status=target_status,
            provenance=record.provenance,
            food_context=record.provenance.food_context,
            packaging_context=record.provenance.packaging_context,
            storage_context=record.provenance.storage_context,
            citation_or_doi=record.provenance.citation_or_doi,
            physics_model_version=record.provenance.physics_model_version,
            applicability_metadata=record.provenance.scenario_parameters,
            evidence_interval=evidence_interval,
            audit_rationale=rationale,
        )
        prepared_targets[target_id] = target_rec

    return AITargetPreparationSet(
        record_id=record.record_id,
        parent_data_status=record.data_status,
        parent_epistemic_level=record.epistemic_level,
        provenance=record.provenance,
        targets=prepared_targets,
    )
