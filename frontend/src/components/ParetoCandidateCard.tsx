import React from 'react';
import type { ParetoCandidate } from '../types/api';

interface ParetoCandidateCardProps {
  candidate: ParetoCandidate;
}

export const ParetoCandidateCard: React.FC<ParetoCandidateCardProps> = ({ candidate }) => {
  const { candidate_design, objective_values, explanation_payload, constraint_compliance_summary } = candidate;
  
  const thicknessObj = objective_values['f_thickness'];
  const thicknessDisplay = thicknessObj 
    ? (thicknessObj.is_interval ? `[${thicknessObj.value_min?.toFixed(1)} — ${thicknessObj.value_max?.toFixed(1)}] ${thicknessObj.unit}` : `${thicknessObj.value?.toFixed(1)} ${thicknessObj.unit}`)
    : (candidate_design.decision_variables?.total_thickness_um ? `${candidate_design.decision_variables.total_thickness_um} um` : 'Unknown');

  const renderObjective = (key: string, label: string) => {
    const obj = objective_values[key];
    if (!obj) return null;

    return (
      <div className="flex justify-between items-center py-1.5 border-b border-slate-100 last:border-0 text-sm">
        <span className="font-medium text-slate-600">{label}</span>
        <div className="text-right">
          <span className="font-semibold text-slate-900 font-mono">
            {obj.is_interval ? `[${obj.value_min?.toFixed(2)} — ${obj.value_max?.toFixed(2)}]` : obj.value?.toFixed(2)}
          </span>
          <span className="text-xs text-slate-500 ml-1">{obj.unit}</span>
        </div>
      </div>
    );
  };

  const status = constraint_compliance_summary?.overall_feasibility_status || 'UNKNOWN';
  let statusColor = 'bg-amber-100 text-amber-800 border-amber-200';
  if (status === 'FEASIBLE') statusColor = 'bg-emerald-100 text-emerald-800 border-emerald-200';
  if (status === 'INFEASIBLE') statusColor = 'bg-red-100 text-red-800 border-red-200';

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full hover:shadow-md transition-shadow">
      <div className="p-5 border-b border-slate-100 bg-slate-50 flex flex-col gap-3">
        <div className="flex justify-between items-start gap-4">
          <h3 className="text-base font-bold text-slate-900 leading-snug">{candidate_design.material_name}</h3>
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border whitespace-nowrap ${statusColor}`}>
            {status}
          </span>
        </div>
        <div className="flex justify-between items-center text-xs text-slate-500">
          <span className="font-mono truncate mr-2 opacity-60" title={candidate.pareto_candidate_id}>{candidate.pareto_candidate_id.split('-')[0]}...</span>
          <span className="font-semibold text-slate-600">{thicknessDisplay}</span>
        </div>
      </div>

      <div className="p-5 flex-1 flex flex-col gap-5">
        <div>
          <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Scientific Objectives</h4>
          <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
            {renderObjective('f_thickness', 'Thickness')}
            {renderObjective('f_moisture_margin', 'Moisture Margin')}
            {renderObjective('f_gas_alignment', 'Gas Alignment')}
            {renderObjective('f_shelf_life_margin', 'Shelf Life Margin')}
          </div>
        </div>

        {explanation_payload && (
          <div className="mt-auto pt-4 border-t border-slate-100">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Evaluation Profile</h4>
            <div className="space-y-3 text-sm">
              <div className="flex flex-col">
                <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wide">Primary Strength</span>
                <span className="text-emerald-700 font-medium leading-tight">{explanation_payload.primary_strength || 'None'}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wide">Limiting Barrier</span>
                <span className="text-amber-700 font-medium leading-tight">{explanation_payload.limiting_barrier || 'None'}</span>
              </div>
            </div>
            {explanation_payload.trade_off_summary && (
              <p className="mt-4 text-[11px] text-slate-600 italic bg-slate-50 p-2.5 rounded-md border border-slate-100 leading-relaxed">
                "{explanation_payload.trade_off_summary}"
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
