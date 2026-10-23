"""
M11: Explainability & Counterfactual Analysis Engine.

Generates deterministic explanations and counterfactual threshold analysis for
evaluated candidate packaging designs without altering underlying scientific logic.

Explains:
1. Overall feasibility status (FEASIBLE, INFEASIBLE, UNKNOWN)
2. Constraint evaluations (OTR, CO2TR, WVTR - required vs candidate, relationship, evidence IDs, UNKNOWN reasons)
3. Objective values & trade-off comparisons (all 4 M6-B3 objectives, interval preservation, descriptive Pareto trade-offs, NO scalar ranking)
4. Evidence & provenance references (evidence ID, source ID, measured vs predicted, QSAR warnings)
5. Deterministic counterfactual threshold analysis ("What boundary change flips constraint feasibility?")
"""

from typing import List, Dict, Optional, Tuple, Any
from app.schemas.optimization import (
    PackagingCandidate,
    ParetoCandidate,
    ParetoFront,
    ObjectiveValue,
    ObjectiveDirection
)
from app.schemas.packaging_requirements import PackagingRequirementEnvelope
from app.schemas.constraints import ConstraintEvaluation, ConstraintStatus
from scientific_engine.optimization.candidate_evaluator import CandidateScientificEvaluationResult
from app.schemas.explainability import (
    ConstraintExplanation,
    ObjectiveExplanation,
    CounterfactualExplanation,
    EvidenceProvenanceReference,
    CandidateExplainabilityReport,
    PipelineExplainabilitySummary
)


class ExplainabilityEngine:
    """
    Deterministic explainability & counterfactual engine for evaluated packaging candidates.
    """

    def generate_candidate_report(
        self,
        candidate: PackagingCandidate,
        eval_result: CandidateScientificEvaluationResult,
        objectives: Dict[str, ObjectiveValue],
        envelope: PackagingRequirementEnvelope,
        pareto_front: Optional[ParetoFront] = None,
        m11_context: Optional[Dict[str, Any]] = None,
    ) -> CandidateExplainabilityReport:
        """
        Generate a complete CandidateExplainabilityReport for a single candidate.
        """
        feasibility_status = eval_result.constraint_profile.overall_status.value
        
        # 1. Constraint Explanations
        constraint_explanations = self._explain_constraints(candidate, eval_result, envelope)

        # 2. Objective Explanations & Pareto Trade-offs
        objective_explanations = self._explain_objectives(candidate, objectives, pareto_front)

        # 3. Evidence Provenance Reference
        provenance = self._extract_provenance(candidate)

        # 4. Counterfactual Threshold Explanations
        counterfactuals = self._generate_counterfactuals(candidate, eval_result, envelope)

        # 5. Pareto Membership Explanation
        pareto_explanation = self._explain_pareto_membership(candidate, feasibility_status, pareto_front)

        # 6. Separate Physics-Derived Limiting Factors vs AI Search Behavior
        infeasible_constraints = [c for c in constraint_explanations if c.status == "INFEASIBLE"]
        if infeasible_constraints:
            reasons = [f"{c.constraint_type} limit violated ({c.explanation_text})" for c in infeasible_constraints]
            physics_limiting = f"Physics-Derived Limiting Factor: Candidate is INFEASIBLE because {'; '.join(reasons)}."
        elif feasibility_status == "FEASIBLE":
            physics_limiting = "Physics-Derived Limiting Factor: Candidate satisfies all physical barrier constraints (OTR, CO2TR, WVTR)."
        else:
            physics_limiting = "Physics-Derived Limiting Factor: Constraint feasibility could not be determined due to missing parameters."

        app_state = m11_context.get("app_state") if m11_context else None
        pred_status = m11_context.get("pred_status") if m11_context else None
        eval_state = m11_context.get("issue5_state") if m11_context else None
        pred_sl = m11_context.get("predicted_shelf_life") if m11_context else None
        lineage = m11_context.get("surrogate_lineage") if m11_context else None

        if pred_status == "PREDICTED" and pred_sl is not None:
            ai_explanation = f"AI Search Prioritization: Surrogate predicted shelf life of {pred_sl:.1f} days (Applicability: {app_state}). DISCLAIMER: AI feature influence describes surrogate model prioritization behavior and does not establish physical causality."
        elif pred_status == "BYPASSED_OOD":
            ai_explanation = "AI Search Prioritization: Candidate is OUT_OF_DOMAIN. Surrogate inference was intentionally bypassed; candidate was routed directly to exact-physics evaluation."
        elif pred_status == "DISABLED_UNEVALUABLE":
            ai_explanation = "AI Search Prioritization: Surrogate evaluation disabled due to missing candidate features."
        elif pred_status == "FAILED_COMPATIBILITY":
            ai_explanation = "AI Search Prioritization: Registered model manifest compatibility failed."
        else:
            ai_explanation = "Exact-Physics Baseline: Candidate evaluated under exact physics pathway without surrogate prioritization."

        # Aggregate warnings
        candidate_warnings = list(dict.fromkeys(eval_result.warnings + eval_result.failure_reasons))

        return CandidateExplainabilityReport(
            candidate_id=candidate.candidate_id,
            material_id=candidate.material_id,
            material_name=candidate.material_name,
            total_thickness_um=candidate.decision_variables.total_thickness_um or 0.0,
            overall_feasibility_status=feasibility_status,
            applicability_state=app_state,
            prediction_status=pred_status,
            evaluation_state=eval_state,
            ai_search_explanation=ai_explanation,
            physics_limiting_explanation=physics_limiting,
            surrogate_lineage=lineage,
            constraint_explanations=constraint_explanations,
            objective_explanations=objective_explanations,
            provenance_reference=provenance,
            counterfactual_explanations=counterfactuals,
            pareto_explanation=pareto_explanation,
            warnings=candidate_warnings
        )

    def generate_pipeline_summary(
        self,
        reports: List[CandidateExplainabilityReport]
    ) -> PipelineExplainabilitySummary:
        """
        Summarize pipeline-wide explainability reports.
        """
        report_dict = {r.candidate_id: r for r in reports}
        feasible_cnt = sum(1 for r in reports if r.overall_feasibility_status == "FEASIBLE")
        infeasible_cnt = sum(1 for r in reports if r.overall_feasibility_status == "INFEASIBLE")
        unknown_cnt = sum(1 for r in reports if r.overall_feasibility_status == "UNKNOWN")

        return PipelineExplainabilitySummary(
            total_candidates_explained=len(reports),
            feasible_candidates_explained=feasible_cnt,
            infeasible_candidates_explained=infeasible_cnt,
            unknown_candidates_explained=unknown_cnt,
            candidate_reports=report_dict
        )

    # ------------------------------------------------------------------
    # Helper methods for detailed explanations
    # ------------------------------------------------------------------

    def _explain_constraints(
        self,
        candidate: PackagingCandidate,
        eval_result: CandidateScientificEvaluationResult,
        envelope: PackagingRequirementEnvelope
    ) -> List[ConstraintExplanation]:
        explanations: List[ConstraintExplanation] = []
        c_profile = eval_result.constraint_profile
        evidence_ids = [candidate.provenance.source_id] if candidate.provenance and candidate.provenance.source_id else []

        eval_map = {e.constraint_type: e for e in c_profile.evaluations}

        # 1. Moisture WVTR Constraint Explanation
        wvtr_metric = candidate.barrier_properties.wvtr
        allowable_wvtr_metric = envelope.moisture_requirements.required_wvtr_per_area
        
        wvtr_status = ConstraintStatus.UNKNOWN.value
        wvtr_req_val = allowable_wvtr_metric.value if (allowable_wvtr_metric and allowable_wvtr_metric.value is not None) else None
        wvtr_cand_val = wvtr_metric.value if wvtr_metric else None
        wvtr_unit = wvtr_metric.unit if wvtr_metric else (allowable_wvtr_metric.unit if allowable_wvtr_metric else "g/(m2*day)")

        if "water_vapor_transmission_rate" in eval_map:
            wvtr_status = eval_map["water_vapor_transmission_rate"].status.value
        elif eval_result.updated_moisture_requirement and eval_result.updated_moisture_requirement.status == "CALCULATED":
            if wvtr_cand_val is not None and wvtr_req_val is not None:
                wvtr_status = "FEASIBLE" if wvtr_cand_val <= wvtr_req_val else "INFEASIBLE"

        if wvtr_status == "FEASIBLE":
            wvtr_text = f"Candidate WVTR ({wvtr_cand_val} {wvtr_unit}) satisfies allowable moisture barrier threshold (<= {wvtr_req_val} {wvtr_unit})."
        elif wvtr_status == "INFEASIBLE":
            wvtr_text = f"Candidate WVTR ({wvtr_cand_val} {wvtr_unit}) exceeds maximum allowable moisture permeability (<= {wvtr_req_val} {wvtr_unit})."
        else:
            wvtr_text = "Moisture barrier WVTR constraint status could not be determined due to missing sorption isotherm parameters or moisture targets."

        explanations.append(ConstraintExplanation(
            constraint_type="moisture_wvtr",
            required_relationship="<=",
            required_value=wvtr_req_val,
            required_unit=wvtr_unit,
            candidate_value=wvtr_cand_val,
            candidate_value_min=wvtr_metric.value_min if wvtr_metric else None,
            candidate_value_max=wvtr_metric.value_max if wvtr_metric else None,
            candidate_unit=wvtr_unit,
            status=wvtr_status,
            explanation_text=wvtr_text,
            evidence_reference_ids=evidence_ids
        ))

        # 2. OTR Constraint Explanation
        otr_metric = candidate.barrier_properties.otr
        otr_status = eval_map["gas_exchange_otr"].status.value if "gas_exchange_otr" in eval_map else "UNKNOWN"
        otr_cand_val = otr_metric.value if otr_metric else None
        otr_unit = otr_metric.unit if otr_metric else "cm3/(m2*day*atm)"
        
        target_o2_range = envelope.gas_requirements.target_o2_range if envelope.gas_requirements else None
        target_o2_min = target_o2_range[0] if target_o2_range else (envelope.gas_requirements.target_o2_percent if envelope.gas_requirements else None)
        otr_req_text = "target O2 range" if target_o2_range else "respiration gas balance"

        if otr_status == "FEASIBLE":
            otr_text = f"Candidate OTR ({otr_cand_val} {otr_unit}) satisfies oxygen permeability requirement for {otr_req_text}."
        elif otr_status == "INFEASIBLE":
            otr_text = f"Candidate OTR ({otr_cand_val} {otr_unit}) fails oxygen permeability requirement for {otr_req_text}."
        else:
            otr_text = "Gas exchange OTR constraint status could not be determined due to missing respiration observations or target O2 range."

        explanations.append(ConstraintExplanation(
            constraint_type="gas_exchange_otr",
            required_relationship=">=",
            required_value=target_o2_min,
            required_unit=otr_unit,
            candidate_value=otr_cand_val,
            candidate_value_min=otr_metric.value_min if otr_metric else None,
            candidate_value_max=otr_metric.value_max if otr_metric else None,
            candidate_unit=otr_unit,
            status=otr_status,
            explanation_text=otr_text,
            evidence_reference_ids=evidence_ids
        ))

        # 3. CO2TR Constraint Explanation
        co2tr_metric = candidate.barrier_properties.co2tr
        co2tr_status = eval_map["gas_exchange_co2tr"].status.value if "gas_exchange_co2tr" in eval_map else "UNKNOWN"
        co2tr_cand_val = co2tr_metric.value if co2tr_metric else None
        co2tr_unit = co2tr_metric.unit if co2tr_metric else "cm3/(m2*day*atm)"

        target_co2_range = envelope.gas_requirements.target_co2_range if envelope.gas_requirements else None
        target_co2_min = target_co2_range[0] if target_co2_range else (envelope.gas_requirements.target_co2_percent if envelope.gas_requirements else None)

        if co2tr_status == "FEASIBLE":
            co2tr_text = f"Candidate CO2TR ({co2tr_cand_val} {co2tr_unit}) satisfies carbon dioxide transmission requirement."
        elif co2tr_status == "INFEASIBLE":
            co2tr_text = f"Candidate CO2TR ({co2tr_cand_val} {co2tr_unit}) fails carbon dioxide transmission requirement."
        else:
            co2tr_text = "Gas exchange CO2TR constraint status could not be determined due to missing respiration observations or target CO2 range."

        explanations.append(ConstraintExplanation(
            constraint_type="gas_exchange_co2tr",
            required_relationship=">=",
            required_value=target_co2_min,
            required_unit=co2tr_unit,
            candidate_value=co2tr_cand_val,
            candidate_value_min=co2tr_metric.value_min if co2tr_metric else None,
            candidate_value_max=co2tr_metric.value_max if co2tr_metric else None,
            candidate_unit=co2tr_unit,
            status=co2tr_status,
            explanation_text=co2tr_text,
            evidence_reference_ids=evidence_ids
        ))

        return explanations

    def _explain_objectives(
        self,
        candidate: PackagingCandidate,
        objectives: Dict[str, ObjectiveValue],
        pareto_front: Optional[ParetoFront]
    ) -> List[ObjectiveExplanation]:
        explanations: List[ObjectiveExplanation] = []
        
        other_pareto_cands = []
        if pareto_front and pareto_front.candidates:
            other_pareto_cands = [p for p in pareto_front.candidates if p.pareto_candidate_id != candidate.candidate_id]

        for obj_name in ["f_thickness", "f_moisture_margin", "f_gas_alignment", "f_shelf_life_margin"]:
            obj_val = objectives.get(obj_name)
            if not obj_val:
                continue

            direction = obj_val.direction.value if hasattr(obj_val.direction, 'value') else str(obj_val.direction)
            status = obj_val.status.value if hasattr(obj_val.status, 'value') else str(obj_val.status)

            trade_offs: List[str] = []

            if status == "CALCULATED":
                if obj_val.is_interval and obj_val.value_min is not None and obj_val.value_max is not None:
                    val_str = f"interval [{obj_val.value_min:.4f}, {obj_val.value_max:.4f}] {obj_val.unit}"
                else:
                    val_str = f"{obj_val.value:.4f} {obj_val.unit}" if obj_val.value is not None else "N/A"

                text = f"Objective {obj_name} ({direction}): evaluated to {val_str}."

                if other_pareto_cands and obj_name == "f_thickness":
                    cand_thick = candidate.decision_variables.total_thickness_um
                    if cand_thick is not None:
                        for other in other_pareto_cands[:2]:
                            other_thick = other.candidate_design.decision_variables.total_thickness_um
                            if other_thick is not None:
                                diff = cand_thick - other_thick
                                if diff < 0:
                                    trade_offs.append(f"Compared to Pareto candidate '{other.candidate_design.material_name}' ({other_thick} µm), this design reduces total thickness by {abs(diff):.1f} µm.")
                                elif diff > 0:
                                    trade_offs.append(f"Compared to Pareto candidate '{other.candidate_design.material_name}' ({other_thick} µm), this design has {diff:.1f} µm greater thickness.")
                elif other_pareto_cands and obj_name == "f_moisture_margin":
                    for other in other_pareto_cands[:2]:
                        other_obj = other.objective_values.get("f_moisture_margin")
                        if other_obj and other_obj.value is not None and obj_val.value is not None:
                            diff_m = obj_val.value - other_obj.value
                            if diff_m > 0:
                                trade_offs.append(f"Compared to Pareto candidate '{other.candidate_design.material_name}', this design provides a larger moisture safety margin (+{diff_m:.3f}).")
                            elif diff_m < 0:
                                trade_offs.append(f"Compared to Pareto candidate '{other.candidate_design.material_name}', this design has a smaller moisture safety margin ({diff_m:.3f}).")
            else:
                text = f"Objective {obj_name} ({direction}) is UNKNOWN because candidate constraint status is not FEASIBLE."

            explanations.append(ObjectiveExplanation(
                objective_name=obj_name,
                direction=direction,
                value=obj_val.value,
                value_min=obj_val.value_min,
                value_max=obj_val.value_max,
                is_interval=obj_val.is_interval,
                unit=obj_val.unit,
                status=status,
                explanation_text=text,
                trade_off_comparisons=trade_offs
            ))

        return explanations

    def _extract_provenance(self, candidate: PackagingCandidate) -> EvidenceProvenanceReference:
        prov = candidate.provenance
        if not prov:
            return EvidenceProvenanceReference(
                material_id=candidate.material_id,
                evidence_classification="EXPERIMENTAL_LITERATURE_DATA",
                verification_status="VERIFIED_EXTRACT",
                is_model_predicted=False
            )

        is_pred = (prov.evidence_classification == "MODEL_PREDICTED") or (prov.synthetic_prediction_warning is not None)

        return EvidenceProvenanceReference(
            evidence_id=prov.record_identifier_in_source,
            source_id=prov.source_id,
            source_name=prov.source_name,
            material_id=candidate.material_id,
            record_identifier_in_source=prov.record_identifier_in_source,
            evidence_classification=prov.evidence_classification,
            verification_status=prov.verification_status,
            synthetic_prediction_warning=prov.synthetic_prediction_warning,
            is_model_predicted=is_pred
        )

    def _generate_counterfactuals(
        self,
        candidate: PackagingCandidate,
        eval_result: CandidateScientificEvaluationResult,
        envelope: PackagingRequirementEnvelope
    ) -> List[CounterfactualExplanation]:
        counterfactuals: List[CounterfactualExplanation] = []
        overall_status = eval_result.constraint_profile.overall_status.value

        # 1. Moisture WVTR Counterfactual
        wvtr_metric = candidate.barrier_properties.wvtr
        allowable_wvtr_metric = envelope.moisture_requirements.required_wvtr_per_area
        
        wvtr_cand_val = wvtr_metric.value if wvtr_metric else None
        wvtr_req_val = allowable_wvtr_metric.value if (allowable_wvtr_metric and allowable_wvtr_metric.value is not None) else None
        wvtr_unit = wvtr_metric.unit if wvtr_metric else "g/(m2*day)"

        if wvtr_metric and wvtr_metric.is_range and wvtr_metric.value_min is not None and wvtr_metric.value_max is not None:
            is_interval = True
            cand_min = wvtr_metric.value_min
            cand_max = wvtr_metric.value_max
        else:
            is_interval = False
            cand_min = cand_max = None

        if wvtr_cand_val is not None and wvtr_req_val is not None:
            is_wvtr_feasible = (wvtr_cand_val <= wvtr_req_val)
            if is_wvtr_feasible:
                text = (
                    f"Candidate WVTR ({wvtr_cand_val} {wvtr_unit}) currently satisfies allowable threshold (<= {wvtr_req_val} {wvtr_unit}). "
                    f"It would become INFEASIBLE if maximum allowable WVTR were reduced below {wvtr_cand_val} {wvtr_unit}."
                )
                counterfactuals.append(CounterfactualExplanation(
                    counterfactual_type="feasibility_threshold",
                    target_property="allowable_wvtr",
                    current_status="FEASIBLE",
                    current_candidate_value=wvtr_cand_val,
                    current_threshold_value=wvtr_req_val,
                    counterfactual_threshold_value=wvtr_cand_val,
                    counterfactual_threshold_min=cand_min,
                    counterfactual_threshold_max=cand_max,
                    is_interval_threshold=is_interval,
                    unit=wvtr_unit,
                    status_flip_condition="BECOMES_INFEASIBLE_IF",
                    explanation_text=text,
                    is_resolved=True
                ))
            else: # INFEASIBLE
                diff = wvtr_cand_val - wvtr_req_val
                text = (
                    f"Candidate WVTR ({wvtr_cand_val} {wvtr_unit}) exceeds allowable threshold (<= {wvtr_req_val} {wvtr_unit}). "
                    f"It would become FEASIBLE if maximum allowable WVTR were increased to at least {wvtr_cand_val} {wvtr_unit} "
                    f"(or candidate WVTR were reduced by {diff:.4f} {wvtr_unit})."
                )
                counterfactuals.append(CounterfactualExplanation(
                    counterfactual_type="feasibility_threshold",
                    target_property="allowable_wvtr",
                    current_status="INFEASIBLE",
                    current_candidate_value=wvtr_cand_val,
                    current_threshold_value=wvtr_req_val,
                    counterfactual_threshold_value=wvtr_cand_val,
                    counterfactual_threshold_min=cand_min,
                    counterfactual_threshold_max=cand_max,
                    is_interval_threshold=is_interval,
                    unit=wvtr_unit,
                    status_flip_condition="BECOMES_FEASIBLE_IF",
                    explanation_text=text,
                    is_resolved=True
                ))
        else: # UNKNOWN missing data
            text = "Counterfactual threshold for moisture WVTR cannot be determined because candidate or allowable WVTR is UNKNOWN."
            counterfactuals.append(CounterfactualExplanation(
                counterfactual_type="feasibility_threshold",
                target_property="allowable_wvtr",
                current_status="UNKNOWN",
                current_candidate_value=wvtr_cand_val,
                current_threshold_value=wvtr_req_val,
                counterfactual_threshold_value=None,
                unit=wvtr_unit,
                status_flip_condition="UNRESOLVED_DUE_TO_UNKNOWN",
                explanation_text=text,
                is_resolved=False
            ))

        # 2. Gas Exchange OTR Counterfactual
        otr_metric = candidate.barrier_properties.otr
        otr_cand_val = otr_metric.value if otr_metric else None
        otr_unit = otr_metric.unit if otr_metric else "cm3/(m2*day*atm)"

        if otr_cand_val is not None:
            eval_map = {e.constraint_type: e for e in eval_result.constraint_profile.evaluations}
            otr_status = eval_map["gas_exchange_otr"].status.value if "gas_exchange_otr" in eval_map else "UNKNOWN"
            
            if otr_status == "FEASIBLE":
                text = (
                    f"Candidate OTR ({otr_cand_val} {otr_unit}) currently satisfies gas exchange requirement. "
                    f"It would become INFEASIBLE if required minimum OTR were increased above {otr_cand_val} {otr_unit}."
                )
                counterfactuals.append(CounterfactualExplanation(
                    counterfactual_type="feasibility_threshold",
                    target_property="required_otr",
                    current_status="FEASIBLE",
                    current_candidate_value=otr_cand_val,
                    current_threshold_value=None,
                    counterfactual_threshold_value=otr_cand_val,
                    unit=otr_unit,
                    status_flip_condition="BECOMES_INFEASIBLE_IF",
                    explanation_text=text,
                    is_resolved=True
                ))
            elif otr_status == "INFEASIBLE":
                text = (
                    f"Candidate OTR ({otr_cand_val} {otr_unit}) fails gas exchange requirement. "
                    f"It would become FEASIBLE if required target OTR were lowered to at most {otr_cand_val} {otr_unit}."
                )
                counterfactuals.append(CounterfactualExplanation(
                    counterfactual_type="feasibility_threshold",
                    target_property="required_otr",
                    current_status="INFEASIBLE",
                    current_candidate_value=otr_cand_val,
                    current_threshold_value=None,
                    counterfactual_threshold_value=otr_cand_val,
                    unit=otr_unit,
                    status_flip_condition="BECOMES_FEASIBLE_IF",
                    explanation_text=text,
                    is_resolved=True
                ))
            else:
                text = "Counterfactual threshold for gas OTR cannot be determined because required OTR target is UNKNOWN."
                counterfactuals.append(CounterfactualExplanation(
                    counterfactual_type="feasibility_threshold",
                    target_property="required_otr",
                    current_status="UNKNOWN",
                    current_candidate_value=otr_cand_val,
                    current_threshold_value=None,
                    counterfactual_threshold_value=None,
                    unit=otr_unit,
                    status_flip_condition="UNRESOLVED_DUE_TO_UNKNOWN",
                    explanation_text=text,
                    is_resolved=False
                ))

        return counterfactuals

    def _explain_pareto_membership(
        self,
        candidate: PackagingCandidate,
        status: str,
        pareto_front: Optional[ParetoFront]
    ) -> str:
        if status == "FEASIBLE":
            if pareto_front and any(p.pareto_candidate_id == candidate.candidate_id for p in pareto_front.candidates):
                return "This candidate is non-dominated under the four M6-B3 objectives. No other evaluated candidate simultaneously improves all objectives."
            else:
                return "This candidate satisfies all hard constraints, but is dominated by another candidate on the Pareto front that achieves superior objective trade-offs."
        elif status == "INFEASIBLE":
            return "This candidate is excluded from the Pareto front because it fails one or more Phase 5 hard constraints."
        else:
            return "This candidate is excluded from the Pareto front because its constraint compliance status is UNKNOWN."
