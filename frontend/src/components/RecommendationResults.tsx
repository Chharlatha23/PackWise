import React from 'react';
import type { RecommendationResponse } from '../types/api';
import { ParetoCandidateCard } from './ParetoCandidateCard';

interface RecommendationResultsProps {
  results: RecommendationResponse;
}

export const RecommendationResults: React.FC<RecommendationResultsProps> = ({ results }) => {
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Property Inference</h3>
          <div className="space-y-3">
            {inference_profile && Object.keys(inference_profile).length > 0 ? (
              Object.entries(inference_profile).map(([key, data]: [string, any]) => (
                <div key={key} className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
                  <span className="text-sm font-medium text-slate-700 capitalize">{key.replace(/_/g, ' ')}</span>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-slate-900">{data?.value !== null && data?.value !== undefined ? data.value : 'UNKNOWN'}</div>
                    <div className="text-xs text-slate-500">{data?.epistemic_status || 'Evidence insufficient'}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">No properties inferred.</div>
            )}
          </div>
        </div>

        {/* Requirement Summary */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Scientific Requirements</h3>
          <div className="space-y-3">
            {requirement_envelope && Object.keys(requirement_envelope).length > 0 ? (
              Object.entries(requirement_envelope).map(([reqKey, reqData]: [string, any]) => {
                let statusText = 'UNKNOWN';
                let statusColor = 'text-amber-700 bg-amber-50 border-amber-200';
                
                if (reqData && typeof reqData === 'object' && reqData.status) {
                  statusText = reqData.status;
                  if (statusText === 'CALCULATED') statusColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
                  if (statusText === 'PARTIALLY CALCULATED') statusColor = 'text-blue-700 bg-blue-50 border-blue-200';
                } else if (reqData) {
                  statusText = 'CALCULATED';
                  statusColor = 'text-emerald-700 bg-emerald-50 border-emerald-200';
                }
                
                return (
                  <div key={reqKey} className="flex justify-between items-center py-2 border-b border-slate-50 last:border-0">
                    <span className="text-sm font-medium text-slate-700 capitalize">{reqKey.replace(/_/g, ' ')}</span>
                    <span className={`text-[10px] uppercase font-semibold px-2 py-1 rounded border ${statusColor}`}>
                      {statusText}
                    </span>
                  </div>
                )
              })
            ) : (
              <div className="text-sm text-slate-500">No requirements calculated.</div>
            )}
          </div>
        </div>
      </div>

      {/* Pareto Candidates / Empty State */}
      <div>
        <h3 className="text-xl font-bold text-slate-900 mb-4">
          {hasPareto ? 'Pareto Candidates' : 'Provisional Alternatives — Not Verified as Feasible'}
        </h3>
        {!hasPareto ? (
          (candidate_summaries && candidate_summaries.length > 0) ? (
            <div className="space-y-6">
              <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-lg">
                <div className="flex">
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-amber-800">
                      No candidate was verified as strictly FEASIBLE.
                    </h3>
                    <div className="mt-2 text-sm text-amber-700">
                      <p>
                        The following candidates are alternatives for further evaluation, not confirmed suitable packages. 
                        {isSurrogatePrioritized 
                          ? " They are ordered by the M11 surrogate search priority based on domain applicability and target performance."
                          : " Candidates are listed in the order returned by the search engine; surrogate prioritization was not applied."}
                        <br />Please review the exact constraint failures or unknown scientific boundaries.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {candidate_summaries.slice(0, 3).map((summary: any) => {
                  const statusColor = summary.constraint_status === 'INFEASIBLE' 
                    ? 'bg-red-100 text-red-800 border-red-200' 
                    : 'bg-amber-100 text-amber-800 border-amber-200';
                  
                  return (
                    <div key={summary.candidate_id} className="bg-slate-50 opacity-95 rounded-xl shadow-sm border border-dashed border-amber-300 overflow-hidden flex flex-col h-full relative">
                      {/* Unverified overlay badge */}
                      <div className="absolute top-0 right-0 bg-amber-500 text-white text-[9px] font-black tracking-widest px-2 py-1 uppercase shadow-sm z-10 rounded-bl-lg border-b border-l border-amber-600">
                        Unverified
                      </div>
                      
                      <div className="p-5 border-b border-amber-200 bg-amber-50/70">
                        <div className="flex justify-between items-start gap-2 mb-2 pr-12">
                          <h3 className="text-sm font-bold text-slate-800 leading-snug">{summary.material_name}</h3>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${statusColor}`}>
                            {summary.constraint_status}
                          </span>
                          <span className="text-xs font-semibold text-slate-500">
                            {summary.total_thickness_um ? `${summary.total_thickness_um} µm` : 'Unknown thick.'}
                          </span>
                        </div>
                      </div>
                      
                      <div className="p-5 flex-1 flex flex-col text-sm">
                        <div className="mb-4 text-xs bg-white p-2 rounded border border-slate-200">
                          {summary.applicability_state && (
                            <div className="flex justify-between mb-1">
                              <span className="font-medium text-slate-500">Surrogate Domain:</span> 
                              <span className="font-semibold text-slate-700">{summary.applicability_state.replace(/_/g, ' ')}</span>
                            </div>
                          )}
                          {summary.predicted_shelf_life != null && (
                            <div className="flex justify-between">
                              <span className="font-medium text-slate-500">Predicted Shelf Life:</span> 
                              <span className="font-semibold text-slate-700">{summary.predicted_shelf_life.toFixed(1)} days</span>
                            </div>
                          )}
                        </div>

                        <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Constraint Profile</h4>
                        <div className="bg-white p-3 rounded-lg border border-slate-100 space-y-2 text-xs">
                          {summary.evaluation_details && Object.entries(summary.evaluation_details).map(([k, v]: [string, any]) => {
                            if (k === 'overall_feasibility_status' || k === 'all_hard_constraints_satisfied' || k === 'overall_status') return null;
                            if (typeof v !== 'object' || !v || !v.status) return null;
                            
                            let color = 'text-slate-600';
                            if (v.status === 'INFEASIBLE') color = 'text-red-600 font-bold';
                            if (v.status === 'UNKNOWN') color = 'text-amber-600 font-bold';
                            if (v.status === 'FEASIBLE') color = 'text-emerald-600';

                            return (
                              <div key={k} className="flex justify-between items-center border-b border-slate-50 last:border-0 pb-1 last:pb-0">
                                <span className="capitalize text-slate-600 truncate mr-2" title={k.replace(/_/g, ' ')}>{k.replace(/_/g, ' ')}</span>
                                <span className={`${color} text-[10px] uppercase tracking-wide`}>{v.status}</span>
                              </div>
                            );
                          })}
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
                <h4 className="text-lg font-bold text-slate-800 mb-3">Ranking Not Scientifically Supportable</h4>
                <p className="text-slate-600 mb-8 max-w-2xl mx-auto text-sm leading-relaxed">
                  No candidate can be meaningfully ranked because essential information or comparable evaluation results are unavailable.
                </p>
              </div>
            ) : (
               <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm text-center text-slate-600">
                  No feasible candidates found for these requirements.
               </div>
            )
          )
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {pareto_front.candidates.map((cand) => (
              <ParetoCandidateCard key={cand.pareto_candidate_id} candidate={cand} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
