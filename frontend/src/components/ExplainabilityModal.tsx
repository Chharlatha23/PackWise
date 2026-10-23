import React, { useState } from 'react';
import type { CandidateExplainabilityReport, ConstraintExplanation, CounterfactualExplanation } from '../types/api';

interface ExplainabilityModalProps {
  report: CandidateExplainabilityReport;
  onClose: () => void;
  onOpenFeedback?: (candidateId: string, materialName: string) => void;
}

export const ExplainabilityModal: React.FC<ExplainabilityModalProps> = ({
  report,
  onClose,
  onOpenFeedback,
}) => {
  const [activeTab, setActiveTab] = useState<'constraints' | 'counterfactuals' | 'provenance'>('constraints');

  const getStatusBadge = (status: string) => {
    if (status === 'FEASIBLE') return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    if (status === 'INFEASIBLE') return 'bg-red-100 text-red-800 border-red-300';
    return 'bg-amber-100 text-amber-800 border-amber-300';
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-slate-900 text-white p-6 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-white tracking-tight">{report.material_name}</h2>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${getStatusBadge(report.overall_feasibility_status)}`}>
                {report.overall_feasibility_status}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1 font-mono">Candidate ID: {report.candidate_id}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-2xl font-light leading-none transition-colors"
          >
            &times;
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-3 gap-2">
          <button
            onClick={() => setActiveTab('constraints')}
            className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'constraints'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Constraint Audit ({report.constraints?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('counterfactuals')}
            className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'counterfactuals'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Counterfactual Boundaries ({report.counterfactuals?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('provenance')}
            className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === 'provenance'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Scientific Citations & Provenance
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-800">
          {report.trade_off_summary && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
              <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-1">Scientific Trade-off Summary</h4>
              <p className="text-sm text-blue-800">{report.trade_off_summary}</p>
            </div>
          )}

          {activeTab === 'constraints' && (
            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Deterministic Constraint Evaluation
              </h4>
              <div className="grid gap-3">
                {report.constraints && report.constraints.length > 0 ? (
                  report.constraints.map((c: ConstraintExplanation, idx: number) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col gap-2"
                    >
                      <div className="flex justify-between items-start">
                        <span className="font-semibold text-slate-900 text-sm capitalize">
                          {c.constraint_name.replace(/_/g, ' ')}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase border ${getStatusBadge(c.status)}`}>
                          {c.status}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600 flex flex-wrap gap-x-4 gap-y-1 font-mono">
                        {c.required_value !== undefined && (
                          <span>Required: {c.comparison_operator} {c.required_value.toFixed(2)} {c.unit}</span>
                        )}
                        <span>
                          Material Property:{' '}
                          {c.material_is_interval
                            ? `[${c.material_value_min?.toFixed(2)} — ${c.material_value_max?.toFixed(2)}]`
                            : c.material_value_min?.toFixed(2) || 'UNKNOWN'}{' '}
                          {c.unit}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 mt-1 italic">{c.scientific_rationale}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">No constraint records available.</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'counterfactuals' && (
            <div className="space-y-4">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Deterministic Counterfactual Thresholds
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Mathematical boundaries where candidate feasibility or individual constraint states transition.
                </p>
              </div>

              <div className="grid gap-3">
                {report.counterfactuals && report.counterfactuals.length > 0 ? (
                  report.counterfactuals.map((cf: CounterfactualExplanation, idx: number) => (
                    <div key={idx} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col gap-2">
                      <div className="flex justify-between items-start">
                        <span className="font-semibold text-slate-900 text-sm capitalize">
                          {cf.constraint_name.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                          {cf.direction_to_flip.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700">{cf.description}</p>
                      {cf.threshold_min !== undefined && (
                        <div className="text-xs font-mono font-semibold text-blue-700 bg-blue-50 px-3 py-1.5 rounded border border-blue-200">
                          Critical Boundary: {cf.threshold_min.toFixed(2)} {cf.threshold_max ? `— ${cf.threshold_max.toFixed(2)}` : ''} {cf.unit}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">No counterfactual threshold shifts detected.</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'provenance' && (
            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Scientific Evidence & Literature Provenance
              </h4>
              <div className="space-y-2">
                {report.evidence_citations && report.evidence_citations.length > 0 ? (
                  report.evidence_citations.map((cite: string, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-xs font-mono text-slate-700">
                      {cite}
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">Standard M5 baseline peer-reviewed literature and TDS datasheet evidence.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-50 p-4 px-6 border-t border-slate-200 flex justify-between items-center">
          {onOpenFeedback && (
            <button
              onClick={() => onOpenFeedback(report.candidate_id, report.material_name)}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
            >
              Record Empirical Trial Feedback
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 text-xs font-semibold rounded-lg transition-colors ml-auto"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
