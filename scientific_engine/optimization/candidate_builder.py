import uuid
import itertools
from typing import List
from sqlalchemy.orm import Session

from app.models.evidence import PackagingMaterial, MaterialBarrierObservation, EvidenceRecord
from app.schemas.optimization import (
    PackagingCandidate,
    CandidateDecisionVariables,
    CandidateBarrierProperties,
    BarrierPropertyMetric,
    CandidateEvidenceReference,
    ConditionMatchLevel
)

class CandidateBuilder:
    """
    Deterministic candidate-construction layer.
    Converts canonical M5 packaging-material evidence into M6-B1 PackagingCandidate objects.
    """
    def __init__(self, session: Session):
        self.session = session

    def _map_barrier_metric(self, obs: MaterialBarrierObservation) -> BarrierPropertyMetric:
        # Use canonical_unit if available, otherwise original_unit
        unit = obs.canonical_unit if obs.canonical_unit else obs.original_unit
        if not unit:
            unit = "UNKNOWN"
            
        return BarrierPropertyMetric(
            value=obs.value,
            unit=unit,
            value_min=obs.value_min,
            value_max=obs.value_max,
            is_range=(obs.value_type == "range" if hasattr(obs, "value_type") else False) or (obs.value_min is not None or obs.value_max is not None),
            test_temperature_c=obs.test_temperature_c_value,
            test_rh_percent=obs.test_rh_percent_value
        )

    def build_candidates(self) -> List[PackagingCandidate]:
        """
        Query all PackagingMaterials from M5 database and construct PackagingCandidates.
        For materials with observed thicknesses, construct candidates per discrete thickness.
        For materials without explicit thickness, construct candidate with default or None.
        """
        materials = self.session.query(PackagingMaterial).all()
        candidates: List[PackagingCandidate] = []

        for mat in materials:
            # Query barrier observations for this material
            observations = self.session.query(MaterialBarrierObservation).filter_by(material_id=mat.id).all()
            
            # Find distinct observed thicknesses for this material
            thickness_map = {} # thickness_um -> list of obs
            for obs in observations:
                t = obs.thickness_value
                if t is not None:
                    if t not in thickness_map:
                        thickness_map[t] = []
                    thickness_map[t].append(obs)
                    
            # Extract evidence reference from first observation if available
            ev_ref = None
            if observations:
                first_obs = observations[0]
                ev_record = self.session.query(EvidenceRecord).filter_by(id=first_obs.evidence_id).first()
                if ev_record:
                    ev_ref = CandidateEvidenceReference(
                        source_id=str(ev_record.id),
                        source_name=ev_record.source.source_name if (ev_record and ev_record.source) else "M5 Database",
                        record_identifier_in_source=str(ev_record.id),
                        evidence_classification=ev_record.evidence_classification.value if hasattr(ev_record.evidence_classification, 'value') else str(ev_record.evidence_classification),
                        verification_status="VERIFIED_EXTRACT",
                        synthetic_prediction_warning=ev_record.synthetic_prediction_warning
                    )

            if not ev_ref:
                ev_ref = CandidateEvidenceReference(
                    source_id=str(mat.id),
                    source_name="M5 Database",
                    record_identifier_in_source=str(mat.id),
                    evidence_classification="EXPERIMENTAL_LITERATURE_DATA",
                    verification_status="VERIFIED_EXTRACT"
                )

            # If material has observed thicknesses, create candidate for each thickness
            if thickness_map:
                for t_um, t_obs_list in thickness_map.items():
                    otr_metric = None
                    wvtr_metric = None
                    co2tr_metric = None

                    for obs in t_obs_list:
                        prop_str = str(obs.property_type.value if hasattr(obs.property_type, 'value') else obs.property_type).lower()
                        metric = self._map_barrier_metric(obs)
                        if "oxygen" in prop_str or prop_str == "otr":
                            otr_metric = metric
                        elif "water" in prop_str or prop_str == "wvtr":
                            wvtr_metric = metric
                        elif "carbon" in prop_str or prop_str == "co2tr":
                            co2tr_metric = metric

                    barrier_props = CandidateBarrierProperties(
                        otr=otr_metric,
                        wvtr=wvtr_metric,
                        co2tr=co2tr_metric
                    )

                    decision_vars = CandidateDecisionVariables(
                        structure_type=mat.structure_type,
                        total_thickness_um=t_um,
                        thickness_source="observed_discrete_m5"
                    )

                    cand_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{mat.id}-{t_um}"))

                    candidate = PackagingCandidate(
                        candidate_id=cand_id,
                        material_id=str(mat.id),
                        material_name=mat.material_name,
                        brand_grade=mat.brand_grade,
                        decision_variables=decision_vars,
                        barrier_properties=barrier_props,
                        condition_match=ConditionMatchLevel.UNKNOWN,
                        provenance=ev_ref
                    )
                    candidates.append(candidate)
            else:
                # Material has no discrete thickness observations; create a baseline candidate
                otr_metric = None
                wvtr_metric = None
                co2tr_metric = None

                for obs in observations:
                    prop_str = str(obs.property_type.value if hasattr(obs.property_type, 'value') else obs.property_type).lower()
                    metric = self._map_barrier_metric(obs)
                    if "oxygen" in prop_str or prop_str == "otr":
                        otr_metric = metric
                    elif "water" in prop_str or prop_str == "wvtr":
                        wvtr_metric = metric
                    elif "carbon" in prop_str or prop_str == "co2tr":
                        co2tr_metric = metric

                barrier_props = CandidateBarrierProperties(
                    otr=otr_metric,
                    wvtr=wvtr_metric,
                    co2tr=co2tr_metric
                )

                decision_vars = CandidateDecisionVariables(
                    structure_type=mat.structure_type,
                    total_thickness_um=None,
                    thickness_source="unknown"
                )

                cand_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{mat.id}-default"))

                candidate = PackagingCandidate(
                    candidate_id=cand_id,
                    material_id=str(mat.id),
                    material_name=mat.material_name,
                    brand_grade=mat.brand_grade,
                    decision_variables=decision_vars,
                    barrier_properties=barrier_props,
                    condition_match=ConditionMatchLevel.UNKNOWN,
                    provenance=ev_ref
                )
                candidates.append(candidate)

        return candidates
