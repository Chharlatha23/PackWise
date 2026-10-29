export interface PackagingRequest {
  commodity: string;
  product_form: string;
  ripeness_stage: string;
  target_shelf_life_days: number;
  storage_type: string;
  
  variety?: string;
  transportation_type?: string;
  transportation_duration_days?: number;
  
  storage_temperature_c?: number;
  relative_humidity_percent?: number;
  
  moisture_percent?: number;
  fat_percent?: number;
  ph?: number;
  respiration_rate?: number;
  
  package_surface_area_m2?: number;
  package_headspace_volume_cm3?: number;
  product_mass_kg?: number;
}

export interface RecommendationResponse {
  recommendation_run_id: string;
  timestamp: string;
  request: PackagingRequest;
  inference_profile: any;
  requirement_envelope: any;
  total_candidates_evaluated: number;
  feasible_candidates_count: number;
  infeasible_candidates_count: number;
  unknown_candidates_count: number;
  pareto_front: ParetoFront;
  candidate_summaries: any[];
  all_warnings: string[];
  traceability_log: any[];
  pipeline_explainability?: any;
}

export interface ParetoFront {
  optimization_run_id: string;
  timestamp: string;
  candidate_count: number;
  candidates: ParetoCandidate[];
  hypervolume_indicator?: number;
  solver_metadata: any;
  constraint_policy_version: string;
}

export interface ParetoCandidate {
  pareto_candidate_id: string;
  candidate_design: PackagingCandidate;
  objective_values: Record<string, ObjectiveValue>;
  constraint_compliance_summary: any;
  uncertainty_profile: any;
  evidence_tier: string;
  traceability: any;
  explanation_payload: ExplanationPayload;
}

export interface PackagingCandidate {
  candidate_id: string;
  material_id: string;
  material_name: string;
  brand_grade?: string;
  decision_variables: any;
  barrier_properties: any;
  condition_match: string;
  provenance: any;
}

export interface ObjectiveValue {
  objective_name: string;
  direction: string;
  value?: number;
  value_min?: number;
  value_max?: number;
  is_interval: boolean;
  unit: string;
  status: string;
  explanation_metadata?: string;
}

export interface ExplanationPayload {
  trade_off_summary: string;
  limiting_barrier: string;
  primary_strength: string;
}

export interface ConstraintExplanation {
  constraint_name: string;
  status: string; // FEASIBLE, INFEASIBLE, UNKNOWN
  comparison_operator: string;
  material_value_min?: number;
  material_value_max?: number;
  material_is_interval: boolean;
  required_value?: number;
  unit: string;
  condition_match_level?: string;
  scientific_rationale: string;
}

export interface CounterfactualExplanation {
  constraint_name: string;
  current_status: string;
  direction_to_flip: string;
  threshold_min?: number;
  threshold_max?: number;
  unit: string;
  description: string;
  is_resolved: boolean;
}

export interface CandidateExplainabilityReport {
  candidate_id: string;
  material_name: string;
  overall_feasibility_status: string;
  constraints: ConstraintExplanation[];
  counterfactuals: CounterfactualExplanation[];
  trade_off_summary?: string;
  evidence_citations?: string[];
}

export interface FeedbackSubmission {
  recommendation_run_id?: string;
  candidate_id?: string;
  material_id?: string;
  trial_identifier: string;
  observation_origin: 'REAL_PRODUCTION' | 'REAL_PILOT' | 'SYNTHETIC_TEST' | 'DEMO';
  observed_shelf_life_days?: number;
  observed_otr?: number;
  observed_co2tr?: number;
  observed_wvtr?: number;
  observed_product_condition?: string;
  evidence_source_metadata?: Record<string, any>;
}

export interface MeasurementComparison {
  property_name: string;
  predicted_value?: number;
  predicted_min?: number;
  predicted_max?: number;
  is_predicted_interval: boolean;
  observed_value?: number;
  discrepancy_residual?: number;
  unit: string;
  comparison_status: 'MATCHED_WITHIN_INTERVAL' | 'OUTSIDE_PREDICTION_INTERVAL' | 'OBSERVED_ONLY' | 'PREDICTION_ONLY' | 'UNKNOWN';
  explanation: string;
}

export interface ModelUpdateCandidate {
  id: string;
  feedback_record_id: string;
  affected_component: string;
  affected_property: string;
  prediction_value?: number;
  prediction_min?: number;
  prediction_max?: number;
  observed_value?: number;
  discrepancy_residual?: number;
  units: string;
  interval_status: string;
  update_status: string;
  human_review_required: boolean;
  discrepancy_evidence_summary: string;
  created_at: string;
}

export interface FeedbackResponse {
  feedback_id: string;
  recommendation_run_id?: string;
  candidate_id?: string;
  material_id?: string;
  trial_identifier: string;
  observation_origin: string;
  observation_timestamp: string;
  validation_status: string;
  validation_message?: string;
  comparisons: MeasurementComparison[];
  model_update_candidates: ModelUpdateCandidate[];
  created_at: string;
}

export interface UserProfile {
  id: number;
  email: string;
  name?: string;
  picture?: string;
  is_active: boolean;
  created_at?: string;
  last_login?: string;
}

