"""
Generic Property Inference Engine (Phase 3).

Executes evidence-driven inference for food commodity properties with:
- Exact contextual filtering (variety, product form, maturity, temperature)
- Fallback resolution with explicit tracking (variety fallback, form fallback, temperature bounds)
- Strict non-destructive uncertainty quantification (min/max range over all supporting observations)
- Full citation and evidence traceability
- Strict unknown handling (never fabricates or guesses missing scientific properties)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.schemas.food_evidence import FoodEvidenceDataset, FoodEvidenceRecord
from app.schemas.inference import (
    InferenceResolutionLevel,
    InferenceWarning,
    InferredProperty,
    PropertyInferenceProfile,
    UncertaintyLevelEnum,
)
from app.schemas.packaging_request import PackagingRequest
from app.schemas.property_status import PropertyStatusEnum


# Standard mapping between PackagingRequest field names and scientific evidence property keys
REQUEST_PROPERTY_MAP: Dict[str, List[str]] = {
    "moisture_percent": ["moisture_content", "moisture_percent", "water_content"],
    "fat_percent": ["fat_content", "fat_percent", "lipid_content"],
    "ph": ["ph", "pH"],
    "respiration_rate": ["respiration_rate", "co2_production_rate"],
}

# Default units for standard properties
STANDARD_UNITS: Dict[str, str] = {
    "moisture_percent": "%",
    "fat_percent": "%",
    "ph": "pH",
    "respiration_rate": "mg CO2/kg/hr",
    "water_activity": "aw",
    "ethylene_production": "µL C2H4/kg/hr",
}


def load_default_reference_dataset() -> FoodEvidenceDataset:
    """Load the verified reference food evidence dataset from data/reference/food_evidence.json."""
    ref_path = Path(__file__).resolve().parent.parent.parent / "data" / "reference" / "food_evidence.json"
    if not ref_path.exists():
        return FoodEvidenceDataset()

    with open(ref_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    records = [FoodEvidenceRecord(**item) for item in raw_data]
    return FoodEvidenceDataset(records=records)


class PropertyInferenceEngine:
    """
    Core inference engine responsible for evaluating user input, searching
    scientific literature evidence, resolving context hierarchies, and producing
    an evidence-backed property profile with explicit Phase 2 uncertainty levels (D/A/B).
    """

    def __init__(self, dataset: Optional[FoodEvidenceDataset] = None) -> None:
        self.dataset = dataset if dataset is not None else load_default_reference_dataset()

    def infer_profile(self, request: PackagingRequest) -> PropertyInferenceProfile:
        """
        Infer a complete scientific property profile for the given packaging request.

        Preserves user-supplied values with highest precedence, queries scientific
        evidence for missing values, and strictly marks unobserved properties as UNKNOWN (Level D).
        """
        profile = PropertyInferenceProfile(
            commodity=request.commodity,
            variety=request.variety,
            product_form=request.product_form,
            ripeness_stage=request.ripeness_stage,
            storage_type=request.storage_type,
            storage_temperature_c=request.storage_temperature_c,
            relative_humidity_percent=request.relative_humidity_percent,
        )

        # 1. Process standard request properties
        for prop_field in ["moisture_percent", "fat_percent", "ph", "respiration_rate"]:
            user_val = getattr(request, prop_field, None)
            inferred_prop = self._resolve_property(
                prop_field=prop_field,
                user_value=user_val,
                request=request,
            )
            profile.properties[prop_field] = inferred_prop
            profile.all_warnings.extend(inferred_prop.warnings)

        # 2. Check for additional scientific properties present in the evidence dataset for this commodity
        commodity_records = [
            r for r in self.dataset.records
            if r.commodity.lower() == request.commodity.lower()
        ]
        additional_properties = {
            r.property for r in commodity_records
            if not any(r.property.lower() in aliases for aliases in REQUEST_PROPERTY_MAP.values())
        }

        for extra_prop in sorted(list(additional_properties)):
            inferred_prop = self._resolve_from_evidence(
                prop_field=extra_prop,
                property_aliases=[extra_prop],
                request=request,
            )
            profile.properties[extra_prop] = inferred_prop
            profile.all_warnings.extend(inferred_prop.warnings)

        # 3. Calculate overall confidence score across resolved properties
        confidences = [
            p.confidence for p in profile.properties.values()
            if p.confidence is not None
        ]
        profile.overall_confidence = (
            round(sum(confidences) / len(confidences), 3) if confidences else None
        )

        return profile

    def _resolve_property(
        self,
        prop_field: str,
        user_value: Optional[float],
        request: PackagingRequest,
    ) -> InferredProperty:
        """Resolve a property either from user input (precedence 1) or from evidence lookup."""
        # Case A: User explicitly supplied the value -> Level A (Deterministic estimate)
        if user_value is not None:
            unit = STANDARD_UNITS.get(prop_field, None)
            return InferredProperty(
                property_name=prop_field,
                value=user_value,
                unit=unit,
                status=PropertyStatusEnum.measured,
                resolution_level=InferenceResolutionLevel.USER_SUPPLIED,
                uncertainty_level=UncertaintyLevelEnum.LEVEL_A,
                confidence=1.0,
                uncertainty_range=(user_value, user_value),
                evidence_interval=None,
                minimum_value=user_value,
                maximum_value=user_value,
                acquisition_method="user_supplied_input",
                supporting_evidence=[],
                citations=["User-provided specification"],
                warnings=[],
            )

        # Case B: Property missing from user input -> Look up evidence
        aliases = REQUEST_PROPERTY_MAP.get(prop_field, [prop_field])
        return self._resolve_from_evidence(
            prop_field=prop_field,
            property_aliases=aliases,
            request=request,
        )

    def _resolve_from_evidence(
        self,
        prop_field: str,
        property_aliases: List[str],
        request: PackagingRequest,
    ) -> InferredProperty:
        """Search and synthesize evidence records for a missing property using context hierarchy."""
        # Step 1: Query all records matching commodity and property aliases
        candidates: List[FoodEvidenceRecord] = []
        for r in self.dataset.records:
            if r.commodity.lower() == request.commodity.lower():
                if any(r.property.lower() == alias.lower() for alias in property_aliases):
                    candidates.append(r)

        # If no records exist for this commodity and property at all -> Level D (UNKNOWN)
        if not candidates:
            return InferredProperty(
                property_name=prop_field,
                value=None,
                unit=STANDARD_UNITS.get(prop_field, None),
                status=PropertyStatusEnum.unknown,
                resolution_level=InferenceResolutionLevel.UNKNOWN,
                uncertainty_level=UncertaintyLevelEnum.LEVEL_D,
                confidence=None,
                uncertainty_range=None,
                evidence_interval=None,
                minimum_value=None,
                maximum_value=None,
                supporting_evidence=[],
                citations=[],
                acquisition_method=None,
                warnings=[
                    InferenceWarning(
                        code="NO_EVIDENCE",
                        message=f"No scientific evidence available for '{prop_field}' on commodity '{request.commodity}'.",
                        severity="warning",
                    )
                ],
            )

        # Step 2: Contextual filtering hierarchy
        warnings: List[InferenceWarning] = []
        resolution = InferenceResolutionLevel.EXACT_CONTEXT_MATCH

        # 2a. Variety filtering
        if request.variety:
            variety_matches = [
                r for r in candidates
                if r.variety and r.variety.lower() == request.variety.lower()
            ]
            if variety_matches:
                candidates = variety_matches
            else:
                resolution = InferenceResolutionLevel.VARIETY_FALLBACK
                warnings.append(
                    InferenceWarning(
                        code="VARIETY_FALLBACK",
                        message=f"No evidence for cultivar '{request.variety}'. Falling back to species-level evidence.",
                        severity="info",
                    )
                )

        # 2b. Product form filtering
        if request.product_form:
            form_matches = [
                r for r in candidates
                if r.product_form and r.product_form.lower() == request.product_form.lower()
            ]
            if form_matches:
                candidates = form_matches
            else:
                if resolution == InferenceResolutionLevel.EXACT_CONTEXT_MATCH:
                    resolution = InferenceResolutionLevel.FORM_FALLBACK
                warnings.append(
                    InferenceWarning(
                        code="FORM_FALLBACK",
                        message=f"No direct evidence for product form '{request.product_form}'. Using available form observations.",
                        severity="info",
                    )
                )

        # 2c. Ripeness / Maturity filtering
        if request.ripeness_stage:
            maturity_matches = [
                r for r in candidates
                if r.maturity_stage and r.maturity_stage.lower() == request.ripeness_stage.lower()
            ]
            if maturity_matches:
                candidates = maturity_matches

        # 2d. Temperature matching (crucial for temperature-dependent metrics like respiration)
        if request.storage_temperature_c is not None:
            temp_records = [r for r in candidates if r.temperature is not None]
            if temp_records:
                exact_temp = [
                    r for r in temp_records
                    if abs(r.temperature - request.storage_temperature_c) <= 2.0
                ]
                if exact_temp:
                    candidates = exact_temp
                    if resolution == InferenceResolutionLevel.EXACT_CONTEXT_MATCH:
                        resolution = InferenceResolutionLevel.TEMPERATURE_MATCH
                else:
                    # Find closest temperature observation
                    closest_temp_rec = min(
                        temp_records,
                        key=lambda r: abs(r.temperature - request.storage_temperature_c)  # type: ignore
                    )
                    closest_diff = abs(closest_temp_rec.temperature - request.storage_temperature_c)  # type: ignore
                    # Only keep records within closest cluster
                    candidates = [
                        r for r in temp_records
                        if abs(r.temperature - closest_temp_rec.temperature) <= 1.0  # type: ignore
                    ]
                    resolution = InferenceResolutionLevel.CLOSEST_TEMPERATURE_BOUND
                    warnings.append(
                        InferenceWarning(
                            code="TEMP_BOUND_DIFFERENCE",
                            message=(
                                f"Observed evidence at {closest_temp_rec.temperature}°C differs from target storage "
                                f"temperature of {request.storage_temperature_c}°C (ΔT = {closest_diff:.1f}°C). "
                                f"Uncertainty widened to reflect temperature gap."
                            ),
                            severity="warning",
                        )
                    )

        # Step 3: Extract and synthesize observed values without fabricating data
        observed_values: List[float] = []
        observed_mins: List[float] = []
        observed_maxs: List[float] = []
        citations: List[str] = []
        base_confidences: List[float] = []
        unit: Optional[str] = None

        for rec in candidates:
            if rec.value is not None:
                observed_values.append(rec.value)
            if rec.minimum_value is not None:
                observed_mins.append(rec.minimum_value)
            if rec.maximum_value is not None:
                observed_maxs.append(rec.maximum_value)
            if rec.unit and not unit:
                unit = rec.unit
            if rec.confidence is not None:
                base_confidences.append(rec.confidence)
            else:
                # Default strength mapping
                strength_map = {"high": 0.9, "medium": 0.75, "low": 0.5, "unverified": 0.3}
                base_confidences.append(strength_map.get(rec.evidence_strength or "", 0.8))

            # Format citation
            cit_parts = []
            if rec.source_title:
                cit_parts.append(rec.source_title)
            if rec.publication_year:
                cit_parts.append(f"({rec.publication_year})")
            if rec.DOI:
                cit_parts.append(f"DOI: {rec.DOI}")
            elif rec.URL:
                cit_parts.append(f"URL: {rec.URL}")
            citations.append(" ".join(cit_parts) if cit_parts else "Unpublished Reference")

        # If no numerical values could be gathered from matching records -> Level D (UNKNOWN)
        all_numeric = observed_values + observed_mins + observed_maxs
        if not all_numeric:
            return InferredProperty(
                property_name=prop_field,
                value=None,
                unit=unit or STANDARD_UNITS.get(prop_field, None),
                status=PropertyStatusEnum.unknown,
                resolution_level=resolution,
                uncertainty_level=UncertaintyLevelEnum.LEVEL_D,
                confidence=None,
                uncertainty_range=None,
                evidence_interval=None,
                minimum_value=None,
                maximum_value=None,
                supporting_evidence=candidates,
                citations=list(set(citations)),
                acquisition_method="literature_qualitative_only",
                warnings=warnings,
            )

        # Derive bounds and representative point estimate
        min_val = min(observed_mins) if observed_mins else min(observed_values)
        max_val = max(observed_maxs) if observed_maxs else max(observed_values)
        uncertainty_range = (min_val, max_val)

        if observed_values:
            point_estimate = round(sum(observed_values) / len(observed_values), 2)
        else:
            point_estimate = round((min_val + max_val) / 2.0, 2)

        # Determine scientific uncertainty classification (LEVEL_A vs LEVEL_B)
        # LEVEL_B applies if a range was reported, if multiple observations exist, or if contextual fallback widened the envelope.
        has_range = (
            min_val < max_val
            or len(observed_mins) > 0
            or len(observed_maxs) > 0
            or len(candidates) > 1
            or resolution in [
                InferenceResolutionLevel.VARIETY_FALLBACK,
                InferenceResolutionLevel.FORM_FALLBACK,
                InferenceResolutionLevel.CLOSEST_TEMPERATURE_BOUND,
            ]
        )

        is_all_literature = all(c.status == PropertyStatusEnum.literature for c in candidates)

        if has_range or is_all_literature:
            uncertainty_level = UncertaintyLevelEnum.LEVEL_B
            evidence_interval = (min_val, max_val)
        else:
            uncertainty_level = UncertaintyLevelEnum.LEVEL_A
            evidence_interval = None

        # Calculate adjusted confidence (Heuristic quality score, NOT a probability)
        raw_conf = sum(base_confidences) / len(base_confidences) if base_confidences else 0.8
        discount = 0.0
        if resolution == InferenceResolutionLevel.VARIETY_FALLBACK:
            discount += 0.1
        if resolution == InferenceResolutionLevel.FORM_FALLBACK:
            discount += 0.15
        if resolution == InferenceResolutionLevel.CLOSEST_TEMPERATURE_BOUND:
            discount += 0.2

        final_confidence = round(max(0.1, min(1.0, raw_conf - discount)), 3)

        # Epistemic status: literature if exact match, inferred if adjusted/fallback
        status = (
            PropertyStatusEnum.literature
            if resolution in [InferenceResolutionLevel.EXACT_CONTEXT_MATCH, InferenceResolutionLevel.TEMPERATURE_MATCH]
            else PropertyStatusEnum.inferred
        )

        return InferredProperty(
            property_name=prop_field,
            value=point_estimate,
            unit=unit or STANDARD_UNITS.get(prop_field, None),
            status=status,
            resolution_level=resolution,
            uncertainty_level=uncertainty_level,
            confidence=final_confidence,
            uncertainty_range=uncertainty_range,
            evidence_interval=evidence_interval,
            minimum_value=min_val,
            maximum_value=max_val,
            supporting_evidence=candidates,
            citations=sorted(list(set(citations))),
            acquisition_method="evidence_context_synthesis",
            warnings=warnings,
        )


def infer_commodity_properties(
    request: PackagingRequest,
    dataset: Optional[FoodEvidenceDataset] = None,
) -> PropertyInferenceProfile:
    """Convenience function to run property inference on a PackagingRequest."""
    engine = PropertyInferenceEngine(dataset=dataset)
    return engine.infer_profile(request)

