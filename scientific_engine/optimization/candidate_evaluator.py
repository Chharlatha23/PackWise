"""
M6-B2B Candidate Scientific Evaluator.

Takes a constructed PackagingCandidate, re-evaluates candidate-specific Phase 4
scientific properties (like moisture-limited shelf life based on candidate WVTR),
and executes deterministic Phase 5 hard constraints.

Does NOT calculate objectives or perform Pareto optimization.
"""

from typing import List, Optional, Tuple, Dict, Any

from app.schemas.optimization import (
    CandidateScientificEvaluationRequest,
    CandidateScientificEvaluationResult,
    CandidateConstraintStatus,
    UncertaintyProfile,
    UncertaintyType,
    CandidateBarrierProperties,
    BarrierPropertyMetric
)
from app.schemas.material_evidence import PackagingMaterialSpec, MaterialPropertyEvidence
from app.schemas.packaging_requirements import (
    PackagingRequirementEnvelope,
    MoistureRequirement,
    GasExchangeRequirement,
    MicrobialRequirement,
    ShelfLifeRequirement
)
from app.schemas.physics import CalculationStatus, ScientificTraceability, ScientificResult
from app.schemas.constraints import ConstraintStatus, ConstraintEvaluation, ConditionMatchLevel

from scientific_engine.physics.requirements import PackagingRequirementEngine
from scientific_engine.physics.moisture import MoistureTransferModel
from scientific_engine.constraints.evaluator import HardConstraintEvaluator

class CandidateScientificEvaluator:
    """
    Evaluates a single PackagingCandidate against a food context,
    recalculating Phase 4 physics where candidate-specific inputs are required,
    and running Phase 5 constraints.
    """

    def __init__(self) -> None:
        self.moisture_model = MoistureTransferModel()
        self.constraint_evaluator = HardConstraintEvaluator()
        self.requirement_engine = PackagingRequirementEngine()

    def _candidate_to_material_spec(self, candidate) -> PackagingMaterialSpec:
        """
        Translates M6-B2A PackagingCandidate to M5/Phase 5 PackagingMaterialSpec 
        for constraint engine compatibility.
        """
        properties: Dict[str, List[MaterialPropertyEvidence]] = {}
        bp = candidate.barrier_properties
        
        def add_prop(metric: Optional[BarrierPropertyMetric], prop_name: str) -> None:
            if metric is not None:
                properties[prop_name] = [MaterialPropertyEvidence(
                    property=prop_name,
                    value=metric.value,
                    unit=metric.unit,
                    minimum_value=metric.value_min,
                    maximum_value=metric.value_max,
                    test_temperature_c=metric.test_temperature_c,
                    test_relative_humidity_percent=metric.test_rh_percent,
                    test_standard=metric.test_standard
                )]
                
        add_prop(bp.otr, "oxygen_transmission_rate")
        add_prop(bp.co2tr, "carbon_dioxide_transmission_rate")
        add_prop(bp.wvtr, "water_vapor_transmission_rate")
        
        return PackagingMaterialSpec(
            material_id=candidate.material_id,
            material_name=candidate.material_name,
            material_category="unknown",
            structure_type=candidate.decision_variables.structure_type or "monolayer_film",
            properties=properties
        )

    def validate_pre_execution_evaluability(
        self, request: CandidateScientificEvaluationRequest
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluates pre-execution scientific evaluability derived from the physics contract.
        Answers: Can exact physics be meaningfully attempted for this candidate request given available required inputs?
        Does NOT execute exact physics calculations or hard constraint evaluation.
        """
        candidate = request.candidate
        base_env = request.base_requirement_envelope
        geometry = request.package_geometry

        if not candidate.material_name and not candidate.material_id:
            return False, "Missing required material identity"

        if not candidate.decision_variables or candidate.decision_variables.total_thickness_um is None or candidate.decision_variables.total_thickness_um <= 0.0:
            return False, "Missing required material thickness"

        if base_env.storage_temperature_c is None:
            return False, "Missing required storage temperature"

        if base_env.relative_humidity_percent is None:
            return False, "Missing required storage relative humidity"

        # Conditional requirement: Package area geometry required if candidate package-level barrier calculation is required
        if candidate.barrier_properties and (candidate.barrier_properties.wvtr or candidate.barrier_properties.otr or candidate.barrier_properties.co2tr):
            if geometry is None or geometry.surface_area_m2 is None or geometry.surface_area_m2 <= 0.0:
                return False, "Missing required package area geometry for candidate barrier recalculation"

        return True, None

    def evaluate_candidate(self, request: CandidateScientificEvaluationRequest) -> CandidateScientificEvaluationResult:
        candidate = request.candidate
        base_env = request.base_requirement_envelope
        geometry = request.package_geometry
        
        warnings: List[str] = []
        failure_reasons: List[str] = []
        
        # ---------------------------------------------------------
        # 1. Candidate-Specific Phase 4 Recalculation
        # ---------------------------------------------------------
        
        # 1A. Recalculate Moisture Transfer & Moisture Shelf Life
        updated_moisture = base_env.moisture_requirements
        
        if updated_moisture.status != CalculationStatus.UNKNOWN:
            # Attempt to extract inputs used in base calculation
            t_trace = updated_moisture.traceability
            if t_trace:
                inputs = t_trace.inputs_used
                m_init = inputs.get("m_init_%")
                m_crit = inputs.get("m_crit_%")
                dry_mass_g = inputs.get("dry_mass_g")
            else:
                m_init = m_crit = dry_mass_g = None
                
            # Candidate package WVTR
            candidate_pkg_wvtr = None
            if candidate.barrier_properties.wvtr and geometry and geometry.surface_area_m2:
                # assuming unit is normalized to m2
                candidate_pkg_wvtr = candidate.barrier_properties.wvtr.value * geometry.surface_area_m2
            else:
                warnings.append("Missing geometry or candidate WVTR to compute package-level WVTR.")
                
            updated_moisture = self.moisture_model.calculate_moisture_requirements(
                initial_water_activity=base_env.moisture_requirements.initial_water_activity,
                critical_water_activity=base_env.moisture_requirements.critical_water_activity,
                initial_moisture_percent=m_init,
                critical_moisture_percent=m_crit,
                storage_temperature_c=base_env.storage_temperature_c,
                relative_humidity_percent=base_env.relative_humidity_percent,
                target_shelf_life_days=base_env.target_shelf_life_days,
                dry_mass_g=dry_mass_g,
                package_area_m2=geometry.surface_area_m2 if geometry else None,
                package_wvtr_g_pkg_day=candidate_pkg_wvtr,
                sorption_model=None # We have extracted initial moisture percent if computable
            )

        # 1B. Updated Shelf Life (from recalculated mechanisms)
        updated_shelf_life = self.requirement_engine._assess_shelf_life_feasibility(
            target_days=base_env.target_shelf_life_days,
            gas_req=base_env.gas_requirements,
            moisture_req=updated_moisture,
            microbial_req=base_env.microbial_requirements,
            det_profile=base_env.deterioration_profile
        )

        # Overall Phase 4 status
        statuses = [
            updated_moisture.status,
            base_env.gas_requirements.status,
            base_env.microbial_requirements.status,
            updated_shelf_life.status
        ]
        
        # Count non-unknown status components
        valid_statuses = [s for s in statuses if s is not None]
        
        if all(s == CalculationStatus.CALCULATED for s in valid_statuses):
            phase4_status = CalculationStatus.CALCULATED
        elif all(s == CalculationStatus.UNKNOWN for s in valid_statuses):
            phase4_status = CalculationStatus.UNKNOWN
        else:
            phase4_status = CalculationStatus.PARTIALLY_CALCULATED

        traceability = ScientificTraceability(
            model_name="CandidateScientificEvaluator",
            equation_form="Phase4 + Phase5",
            inputs_used={"candidate_id": candidate.candidate_id},
            units_used={}
        )

        # ---------------------------------------------------------
        # 2. Phase 5 Deterministic Constraint Evaluation
        # ---------------------------------------------------------
        
        mat_spec = self._candidate_to_material_spec(candidate)
        
        # Invoke Phase 5 engine directly
        feasibility_res = self.constraint_evaluator.evaluate_candidate(
            material=mat_spec,
            envelope=base_env
        )
        
        phase5_status = feasibility_res.overall_status
        constraint_profile = CandidateConstraintStatus(
            all_hard_constraints_satisfied=(phase5_status == ConstraintStatus.FEASIBLE),
            overall_status=phase5_status,
            evaluations=feasibility_res.constraint_results,
            condition_match=candidate.condition_match
        )
        
        for eval_ in feasibility_res.constraint_results:
            if eval_.status == ConstraintStatus.INFEASIBLE:
                failure_reasons.append(f"Constraint {eval_.constraint_type} failed: {eval_.reason}")
            elif eval_.status == ConstraintStatus.UNKNOWN:
                failure_reasons.append(f"Constraint {eval_.constraint_type} unknown: {eval_.reason}")
                
        warnings.extend(feasibility_res.warnings)
        
        # ---------------------------------------------------------
        # 3. Uncertainty Profile
        # ---------------------------------------------------------
        
        unc_type = UncertaintyType.DETERMINISTIC_POINT
        if candidate.provenance.evidence_classification == "MODEL_PREDICTED":
            unc_type = UncertaintyType.QSAR_CONFIDENCE_INTERVAL
        elif any(bp and bp.is_range for bp in [candidate.barrier_properties.otr, candidate.barrier_properties.wvtr, candidate.barrier_properties.co2tr]):
            unc_type = UncertaintyType.BOUNDED_INTERVAL
            
        uncertainty_profile = UncertaintyProfile(
            uncertainty_type=unc_type,
            objective_intervals={}
        )

        return CandidateScientificEvaluationResult(
            candidate_id=candidate.candidate_id,
            updated_moisture_requirement=updated_moisture,
            updated_gas_exchange_requirement=base_env.gas_requirements,
            updated_microbial_requirement=base_env.microbial_requirements,
            candidate_shelf_life_requirement=updated_shelf_life,
            overall_status=phase4_status,
            traceability=traceability,
            constraint_profile=constraint_profile,
            uncertainty_profile=uncertainty_profile,
            warnings=warnings,
            failure_reasons=failure_reasons
        )
