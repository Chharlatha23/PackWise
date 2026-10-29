import React from 'react';
import type { RecommendationResponse } from '../types/api';
import { ParetoCandidateCard } from './ParetoCandidateCard';

interface RecommendationResultsProps {
  results: RecommendationResponse;
  onExplainCandidate?: (candidate: any) => void;
  onRecordFeedback?: (candidateId: string, materialName: string) => void;
}

export const RecommendationResults: React.FC<RecommendationResultsProps> = ({
  results,
  onExplainCandidate,
  onRecordFeedback,
}) => {
  const {
    total_candidates_evaluated,
    feasible_candidates_count,
    infeasible_candidates_count,
    unknown_candidates_count,
    pareto_front,
    inference_profile,
    requirement_envelope,
    candidate_summaries
  } = results;

  const hasPareto = pareto_front.candidates && pareto_front.candidates.length > 0;
  
  // Pipeline summary derived status logic
  const inferenceStatus = inference_profile && Object.keys(inference_profile).length > 0 ? "COMPLETED" : "UNKNOWN";
  const reqStatus = requirement_envelope ? "COMPLETED" : "UNKNOWN";
  const constraintsStatus = total_candidates_evaluated > 0 ? "COMPLETED" : "UNKNOWN";
  const evalStatus = total_candidates_evaluated > 0 ? "COMPLETED" : "UNKNOWN";
  const paretoStatus = hasPareto ? "COMPLETED" : (unknown_candidates_count > 0 ? "UNKNOWN" : "COMPLETED");

  const algorithmName = pareto_front?.solver_metadata?.algorithm_name || '';
  const isSurrogatePrioritized = algorithmName.includes('SURROGATE') || algorithmName.includes('INTELLIGENT');

  const renderPipelineStage = (name: string, status: string) => (
    <div className="flex flex-col items-center">
      <div className={`w-32 py-2 px-2 text-center rounded text-xs font-semibold border ${status === 'COMPLETED' ? 'bg-blue-50 text-blue-800 border-blue-200' : 'bg-amber-50 text-amber-800 border-amber-200'}`}>
        {name}
        <div className="text-[9px] uppercase mt-1 opacity-80">{status === 'UNKNOWN' ? 'UNKNOWN — insufficient verified evidence' : status}</div>
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <p className="text-sm text-slate-500 font-medium">Candidates Evaluated</p>
          <p className="text-3xl font-semibold text-slate-900 mt-2">{total_candidates_evaluated}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <p className="text-sm text-slate-500 font-medium">Feasible</p>
          <p className="text-3xl font-semibold text-emerald-600 mt-2">{feasible_candidates_count}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <p className="text-sm text-slate-500 font-medium">Infeasible</p>
          <p className="text-3xl font-semibold text-red-600 mt-2">{infeasible_candidates_count}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <p className="text-sm text-slate-500 font-medium">Unknown / Incomplete</p>
          <p className="text-3xl font-semibold text-amber-600 mt-2">{unknown_candidates_count}</p>
        </div>
        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col justify-between">
          <p className="text-sm text-slate-500 font-medium">Pareto Candidates</p>
          <p className="text-3xl font-semibold text-blue-600 mt-2">{pareto_front.candidate_count}</p>
        </div>
      </div>

      {/* Scientific Pipeline Summary */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 overflow-x-auto">
        <h3 className="text-lg font-semibold text-slate-800 mb-6">Scientific Evaluation Pipeline</h3>
        <div className="flex items-center justify-between min-w-[700px]">
          {renderPipelineStage("Property Inference", inferenceStatus)}
          <div className="h-0.5 flex-1 bg-slate-200 mx-2"></div>
          {renderPipelineStage("Packaging Requirements", reqStatus)}
          <div className="h-0.5 flex-1 bg-slate-200 mx-2"></div>
          {renderPipelineStage("Hard Constraints", constraintsStatus)}
          <div className="h-0.5 flex-1 bg-slate-200 mx-2"></div>
          {renderPipelineStage("Candidate Evaluation", evalStatus)}
          <div className="h-0.5 flex-1 bg-slate-200 mx-2"></div>
          {renderPipelineStage("Pareto Analysis", paretoStatus)}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Inference Summary */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-800">Property Inference</h3>
              <p className="text-xs text-slate-500">Scenario properties resolved from direct input or scientific evidence</p>
            </div>
            {inference_profile?.overall_confidence !== undefined && inference_profile?.overall_confidence !== null && (
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200" title="Scientific Evidence Confidence Score">
                Conf: {(inference_profile.overall_confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>

          {/* Scenario & Context Matrix: Commodity, Variety, Product Form, Ripeness Stage, Storage Type, Storage Temp, RH */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3 mb-4 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Commodity</span>
              <span className="font-bold text-slate-800 capitalize">
                {inference_profile?.commodity || <span className="text-amber-700 font-mono">UNKNOWN</span>}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Variety</span>
              <span className="font-bold text-slate-800 capitalize">
                {inference_profile?.variety || <span className="text-slate-500 italic">None Specified</span>}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Product Form</span>
              <span className="font-bold text-slate-800 capitalize">
                {inference_profile?.product_form || <span className="text-amber-700 font-mono">UNKNOWN</span>}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Ripeness Stage</span>
              <span className="font-bold text-slate-800 capitalize">
                {inference_profile?.ripeness_stage || <span className="text-amber-700 font-mono">UNKNOWN</span>}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Storage Type</span>
              <span className="font-bold text-slate-800 capitalize">
                {inference_profile?.storage_type || <span className="text-amber-700 font-mono">UNKNOWN</span>}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Storage Temp</span>
              <span className="font-bold text-slate-800">
                {inference_profile?.storage_temperature_c != null ? (
                  `${inference_profile.storage_temperature_c}°C`
                ) : (
                  <span className="text-amber-700 font-mono">UNKNOWN</span>
                )}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Relative Humidity</span>
              <span className="font-bold text-slate-800">
                {inference_profile?.relative_humidity_percent != null ? (
                  `${inference_profile.relative_humidity_percent}%`
                ) : (
                  <span className="text-amber-700 font-mono">UNKNOWN</span>
                )}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block font-medium text-[10px] uppercase">Overall Confidence</span>
              <span className="font-bold text-blue-700">
                {inference_profile?.overall_confidence != null ? (
                  `${(inference_profile.overall_confidence * 100).toFixed(0)}%`
                ) : (
                  <span className="text-amber-700 font-mono">UNKNOWN</span>
                )}
              </span>
            </div>
          </div>

          <div className="space-y-3">
            {inference_profile?.properties && Object.keys(inference_profile.properties).length > 0 ? (
              Object.entries(inference_profile.properties).map(([key, prop]: [string, any]) => {
                const isKnown = prop?.value !== null && prop?.value !== undefined;
                const isUserSupplied = prop?.resolution_level === 'user_supplied';
                const statusBadge = isUserSupplied
                  ? { text: 'User Provided', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' }
                  : isKnown
                  ? { text: prop?.resolution_level?.replace(/_/g, ' ') || 'Inferred', color: 'bg-blue-50 text-blue-700 border-blue-200' }
                  : { text: 'UNKNOWN (No Evidence)', color: 'bg-amber-50 text-amber-800 border-amber-200' };

                const citation = prop?.citations && prop.citations.length > 0 ? prop.citations[0] : null;

                return (
                  <div key={key} className="py-2.5 border-b border-slate-100 last:border-0">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-sm font-semibold text-slate-800 capitalize">{key.replace(/_/g, ' ')}</span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded border ${statusBadge.color}`}>
                            {statusBadge.text}
                          </span>
                          {prop?.uncertainty_range && (
                            <span className="text-[10px] text-slate-500 font-mono">
                              Range: [{prop.uncertainty_range[0]} – {prop.uncertainty_range[1]} {prop.unit || ''}]
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className={`text-sm font-bold ${isKnown ? 'text-slate-900' : 'text-amber-700 font-mono'}`}>
                          {isKnown ? `${prop.value} ${prop.unit || ''}` : 'UNKNOWN'}
                        </div>
                        {prop?.confidence != null && (
                          <div className="text-[10px] text-slate-500">
                            Confidence: {(prop.confidence * 100).toFixed(0)}%
                          </div>
                        )}
                      </div>
                    </div>

                    {citation && (
                      <div className="mt-1 text-[10px] text-slate-500 truncate max-w-full" title={citation}>
                        Ref: {citation}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="text-sm text-slate-500">No properties evaluated.</div>
            )}
          </div>
        </div>

        {/* Requirement Summary */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-800">Scientific Requirements</h3>
              <p className="text-xs text-slate-500">Derived shelf-life and gas/moisture transmission thresholds</p>
            </div>
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
              requirement_envelope?.overall_status === 'CALCULATED'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : requirement_envelope?.overall_status === 'PARTIALLY_CALCULATED'
                ? 'bg-blue-50 text-blue-700 border-blue-200'
                : 'bg-amber-50 text-amber-800 border-amber-200'
            }`}>
              {requirement_envelope?.overall_status || 'UNKNOWN'}
            </span>
          </div>

          <div className="space-y-3">
            {/* Target Gas Exchange (OTR / CO2TR) */}
            <div className="py-2.5 border-b border-slate-100">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-sm font-semibold text-slate-800">Gas Exchange (EMAP OTR/CO₂TR)</span>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Target O₂: {requirement_envelope?.gas_requirements?.target_o2_percent ?? 3}% | Target CO₂: {requirement_envelope?.gas_requirements?.target_co2_percent ?? 5}%
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${
                    requirement_envelope?.gas_requirements?.status === 'CALCULATED'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}>
                    {requirement_envelope?.gas_requirements?.status || 'UNKNOWN'}
                  </span>
                  <div className="text-xs font-mono font-semibold text-slate-900 mt-1">
                    {requirement_envelope?.gas_requirements?.required_otr_per_area?.value != null
                      ? `${requirement_envelope.gas_requirements.required_otr_per_area.value} cc/m²·day`
                      : 'OTR: UNKNOWN'}
                  </div>
                </div>
              </div>
              {requirement_envelope?.gas_requirements?.warnings?.[0] && (
                <div className="mt-1 text-[10px] text-amber-700 italic">
                  Note: {requirement_envelope.gas_requirements.warnings[0]}
                </div>
              )}
            </div>

            {/* Moisture Transfer (WVTR) */}
            <div className="py-2.5 border-b border-slate-100">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-sm font-semibold text-slate-800">Moisture Barrier (WVTR)</span>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Δp_w: {requirement_envelope?.moisture_requirements?.water_vapor_pressure_gradient_kpa?.value != null
                      ? `${requirement_envelope.moisture_requirements.water_vapor_pressure_gradient_kpa.value} kPa`
                      : 'Equilibrium undetermined'}
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${
                    requirement_envelope?.moisture_requirements?.status === 'CALCULATED'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : requirement_envelope?.moisture_requirements?.status === 'PARTIALLY_CALCULATED'
                      ? 'bg-blue-50 text-blue-700 border-blue-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}>
                    {requirement_envelope?.moisture_requirements?.status || 'UNKNOWN'}
                  </span>
                  <div className="text-xs font-mono font-semibold text-slate-900 mt-1">
                    {requirement_envelope?.moisture_requirements?.required_wvtr_per_area?.value != null
                      ? `${requirement_envelope.moisture_requirements.required_wvtr_per_area.value} g/m²·day`
                      : 'WVTR: UNKNOWN'}
                  </div>
                </div>
              </div>
              {requirement_envelope?.moisture_requirements?.warnings?.[0] && (
                <div className="mt-1 text-[10px] text-amber-700 italic">
                  Note: {requirement_envelope.moisture_requirements.warnings[0]}
                </div>
              )}
            </div>

            {/* Microbial & Respiration Deterioration Profile */}
            <div className="py-2.5">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-sm font-semibold text-slate-800">Primary Deterioration Vulnerabilities</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {requirement_envelope?.deterioration_profile?.primary_vulnerabilities?.map((v: string) => (
                      <span key={v} className="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md font-medium capitalize">
                        {v.replace(/_/g, ' ')}
                      </span>
                    )) || <span className="text-xs text-slate-500">None identified</span>}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border bg-slate-100 text-slate-700 border-slate-200">
                    Target: {requirement_envelope?.target_shelf_life_days || '—'} days
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pareto Candidates / Evaluated Candidates Section */}
      <div>
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 mb-4">
          <div>
            <h3 className="text-xl font-bold text-slate-900">
              {hasPareto ? 'Pareto-Optimal Candidate Materials' : 'Evaluated Material Candidate Status & Scientific Audit'}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              {hasPareto
                ? 'Non-dominated candidate materials passing all hard constraints and verified by exact physics.'
                : 'Exact-physics constraint status for all candidate materials evaluated from the material evidence database.'}
            </p>
          </div>

          {!hasPareto && candidate_summaries && candidate_summaries.length > 0 && (
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-slate-500 font-medium mr-1">Display:</span>
              <span className="px-2 py-1 rounded bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                All {candidate_summaries.length} Candidates
              </span>
            </div>
          )}
        </div>

        {!hasPareto ? (
          (candidate_summaries && candidate_summaries.length > 0) ? (
            <div className="space-y-6">
              <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-lg">
                <div className="flex">
                  <div className="ml-1">
                    <h4 className="text-sm font-bold text-amber-900">
                      Zero Candidates Verified as Strictly FEASIBLE
                    </h4>
                    <div className="mt-1.5 text-xs text-amber-800 space-y-1">
                      <p>
                        The inverse-design search engine evaluated <strong>{total_candidates_evaluated}</strong> material candidates from the database.
                        None could be confirmed as feasible because required barrier properties (such as respiration O₂ consumption or water vapor transmission rate) are unmeasured or indeterminate under the current scenario inputs.
                      </p>
                      <p className="font-medium">
                        {isSurrogatePrioritized 
                          ? "Materials are prioritized using M11 domain applicability and shelf-life objectives. Exact physics remains sovereign."
                          : "Materials are listed in deterministic database evaluation order."}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {candidate_summaries.map((summary: any) => {
                  const statusColor = summary.constraint_status === 'FEASIBLE'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    : summary.constraint_status === 'INFEASIBLE' 
                    ? 'bg-red-100 text-red-800 border-red-200' 
                    : 'bg-amber-100 text-amber-800 border-amber-200';

                  const badgeText = summary.constraint_status === 'FEASIBLE'
                    ? 'Verified Feasible'
                    : summary.constraint_status === 'INFEASIBLE'
                    ? 'Infeasible'
                    : 'Unverified / Indeterminate';
                  
                  // Extract individual constraint evaluations
                  const evals = summary.evaluation_details?.evaluations || [];

                  return (
                    <div key={summary.candidate_id} className="bg-slate-50 opacity-95 rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full relative">
                      {/* Status header badge */}
                      <div className={`absolute top-0 right-0 text-white text-[9px] font-black tracking-widest px-2.5 py-1 uppercase shadow-xs z-10 rounded-bl-lg border-b border-l ${
                        summary.constraint_status === 'FEASIBLE'
                          ? 'bg-emerald-600 border-emerald-700'
                          : summary.constraint_status === 'INFEASIBLE'
                          ? 'bg-red-600 border-red-700'
                          : 'bg-amber-500 border-amber-600'
                      }`}>
                        {badgeText}
                      </div>
                      
                      <div className="p-5 border-b border-slate-200 bg-white">
                        <div className="flex justify-between items-start gap-2 mb-2 pr-24">
                          <h4 className="text-sm font-bold text-slate-800 leading-snug">{summary.material_name}</h4>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${statusColor}`}>
                            {summary.constraint_status}
                          </span>
                          <span className="text-xs font-semibold text-slate-500">
                            {summary.total_thickness_um ? `${summary.total_thickness_um} µm` : 'Thickness unrecorded'}
                          </span>
                        </div>
                      </div>
                      
                      <div className="p-5 flex-1 flex flex-col text-sm">
                        {summary.applicability_state && (
                          <div className="mb-3 text-xs bg-white p-2.5 rounded-lg border border-slate-200">
                            <div className="flex justify-between mb-1">
                              <span className="font-medium text-slate-500">Surrogate Domain:</span> 
                              <span className="font-semibold text-slate-700">{summary.applicability_state.replace(/_/g, ' ')}</span>
                            </div>
                            {summary.predicted_shelf_life != null && (
                              <div className="flex justify-between">
                                <span className="font-medium text-slate-500">Predicted Shelf Life:</span> 
                                <span className="font-semibold text-slate-700">{summary.predicted_shelf_life.toFixed(1)} days</span>
                              </div>
                            )}
                          </div>
                        )}

                        <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Hard Barrier Constraints</h5>
                        <div className="bg-white p-3 rounded-lg border border-slate-100 space-y-2 text-xs flex-1">
                          {evals.length > 0 ? (
                            evals.map((ev: any) => {
                              let color = 'text-slate-600';
                              if (ev.status === 'INFEASIBLE') color = 'text-red-600 font-bold';
                              if (ev.status === 'UNKNOWN') color = 'text-amber-600 font-bold';
                              if (ev.status === 'FEASIBLE') color = 'text-emerald-600 font-bold';

                              return (
                                <div key={ev.constraint_type} className="border-b border-slate-50 last:border-0 pb-1.5 last:pb-0">
                                  <div className="flex justify-between items-center">
                                    <span className="capitalize font-medium text-slate-700 truncate mr-2" title={ev.constraint_type}>
                                      {ev.constraint_type.replace(/_/g, ' ')}
                                    </span>
                                    <span className={`${color} text-[10px] uppercase tracking-wide`}>{ev.status}</span>
                                  </div>
                                  {ev.reason && (
                                    <div className="text-[10px] text-slate-400 mt-0.5 line-clamp-1" title={ev.reason}>
                                      {ev.reason}
                                    </div>
                                  )}
                                </div>
                              );
                            })
                          ) : (
                            <div className="text-slate-400 text-xs italic">No individual constraint records.</div>
                          )}
                        </div>

                        {/* Action buttons */}
                        <div className="mt-4 pt-3 border-t border-slate-200 flex gap-2">
                          {onExplainCandidate && summary.explainability && (
                            <button
                              onClick={() => onExplainCandidate(summary.explainability)}
                              className="flex-1 py-1.5 px-2 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold rounded-lg border border-blue-200 transition-colors cursor-pointer"
                            >
                              Constraint Audit
                            </button>
                          )}
                          {onRecordFeedback && (
                            <button
                              onClick={() => onRecordFeedback(summary.candidate_id, summary.material_name)}
                              className="py-1.5 px-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                            >
                              Trial Feedback
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            total_candidates_evaluated > 0 ? (
              <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm text-center">
                <h4 className="text-lg font-bold text-slate-800 mb-3">Evaluation Indeterminate</h4>
                <p className="text-slate-600 mb-4 max-w-2xl mx-auto text-sm leading-relaxed">
                  No candidate could be confirmed as feasible.
                </p>
              </div>
            ) : (
              <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm text-center text-slate-600">
                No candidates evaluated from the database.
              </div>
            )
          )
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {pareto_front.candidates.map((cand) => (
              <ParetoCandidateCard
                key={cand.pareto_candidate_id}
                candidate={cand}
                onExplain={(c) => {
                  if (onExplainCandidate) {
                    const candidateSummary = candidate_summaries?.find((cs: any) => cs.candidate_id === c.candidate_design?.candidate_id);
                    onExplainCandidate(candidateSummary?.explainability || {
                      candidate_id: c.pareto_candidate_id,
                      material_name: c.candidate_design?.material_name,
                      overall_feasibility_status: c.constraint_compliance_summary?.overall_feasibility_status || 'FEASIBLE',
                      constraints: [],
                      counterfactuals: [],
                      trade_off_summary: c.explanation_payload?.trade_off_summary,
                    });
                  }
                }}
                onFeedback={onRecordFeedback}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
