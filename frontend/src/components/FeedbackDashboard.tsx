import React, { useEffect, useState } from 'react';
import type { FeedbackResponse, ModelUpdateCandidate } from '../types/api';
import { fetchAllFeedback, fetchModelUpdates } from '../api/client';

interface FeedbackDashboardProps {
  onNewFeedbackClick: () => void;
}

export const FeedbackDashboard: React.FC<FeedbackDashboardProps> = ({ onNewFeedbackClick }) => {
  const [feedbackList, setFeedbackList] = useState<FeedbackResponse[]>([]);
  const [updateCandidates, setUpdateCandidates] = useState<ModelUpdateCandidate[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'trials' | 'candidates'>('trials');

  const loadData = async () => {
    setLoading(true);
    try {
      const [fList, uList] = await Promise.all([
        fetchAllFeedback().catch(() => []),
        fetchModelUpdates().catch(() => [])
      ]);
      setFeedbackList(fList);
      setUpdateCandidates(uList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="bg-slate-800 px-6 py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 className="text-lg font-medium text-white">Packaging Feedback & Model Discrepancy Ledger</h2>
          <p className="text-xs text-slate-300 mt-0.5">
            M12 Real-World Feedback Loop — Zero automatic model retraining; discrepancies recorded for expert audit.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadData}
            className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-3 py-1.5 rounded-lg border border-slate-600 transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={onNewFeedbackClick}
            className="text-xs bg-blue-600 hover:bg-blue-500 text-white font-semibold px-3 py-1.5 rounded-lg shadow-sm transition-colors"
          >
            + Record Trial Observation
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-3 gap-2">
        <button
          onClick={() => setActiveTab('trials')}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'trials'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Recorded Packaging Trials ({feedbackList.length})
        </button>
        <button
          onClick={() => setActiveTab('candidates')}
          className={`pb-3 px-3 text-sm font-semibold border-b-2 transition-colors ${
            activeTab === 'candidates'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Model Update Candidates ({updateCandidates.length})
        </button>
      </div>

      {/* Body */}
      <div className="p-6">
        {loading ? (
          <div className="text-center py-8 text-sm text-slate-500">Loading trial observations and model candidates...</div>
        ) : activeTab === 'trials' ? (
          feedbackList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              No empirical packaging trial feedback recorded yet. Submit an observation to test discrepancy analysis.
            </div>
          ) : (
            <div className="space-y-4">
              {feedbackList.map((f) => (
                <div key={f.feedback_id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col gap-3">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                    <div>
                      <span className="font-bold text-slate-900 text-sm font-mono mr-2">{f.trial_identifier}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-semibold uppercase">
                        {f.observation_origin}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400 font-mono">
                      {f.created_at ? new Date(f.created_at).toLocaleString() : ''}
                    </span>
                  </div>

                  {f.comparisons && f.comparisons.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-100">
                      {f.comparisons.map((c, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-white border border-slate-200 text-xs">
                          <div className="flex justify-between font-medium">
                            <span className="capitalize text-slate-700">{c.property_name.replace(/_/g, ' ')}</span>
                            <span className={`text-[10px] font-bold ${
                              c.comparison_status === 'MATCHED_WITHIN_INTERVAL' ? 'text-emerald-700' : 'text-amber-700'
                            }`}>
                              {c.comparison_status === 'MATCHED_WITHIN_INTERVAL' ? 'MATCH' : 'OUTSIDE'}
                            </span>
                          </div>
                          <div className="text-[11px] font-mono text-slate-600 mt-1">
                            Obs: {c.observed_value !== undefined ? c.observed_value : '—'} {c.unit}
                          </div>
                          {c.discrepancy_residual !== undefined && (
                            <div className="text-[11px] font-mono font-semibold text-slate-800">
                              Res: {c.discrepancy_residual > 0 ? `+${c.discrepancy_residual.toFixed(2)}` : c.discrepancy_residual.toFixed(2)}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )
        ) : (
          updateCandidates.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              Zero model update candidates generated. All recorded observations match predicted intervals.
            </div>
          ) : (
            <div className="space-y-3">
              {updateCandidates.map((uc) => (
                <div key={uc.id} className="p-4 rounded-xl border border-amber-200 bg-amber-50/60 flex flex-col gap-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-bold text-slate-900 text-sm">{uc.affected_component}</span>
                      <span className="text-xs text-slate-600 ml-2">Property: <strong className="font-mono">{uc.affected_property}</strong></span>
                    </div>
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 uppercase">
                      {uc.update_status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-700">{uc.discrepancy_evidence_summary}</p>
                  <div className="flex gap-4 font-mono text-xs text-slate-800 pt-1 border-t border-amber-200/60">
                    <span>Pred: {uc.prediction_value !== undefined ? uc.prediction_value : `[${uc.prediction_min} — ${uc.prediction_max}]`}</span>
                    <span>Obs: {uc.observed_value}</span>
                    <span className="font-bold">Residual: {uc.discrepancy_residual !== undefined ? uc.discrepancy_residual.toFixed(2) : '—'} {uc.units}</span>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
};
