import React, { useState } from 'react';
import type { FeedbackSubmission, FeedbackResponse } from '../types/api';
import { submitFeedback } from '../api/client';

interface FeedbackModalProps {
  recommendationRunId?: string;
  candidateId?: string;
  materialName?: string;
  onClose: () => void;
  onSuccess?: (response: FeedbackResponse) => void;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  recommendationRunId,
  candidateId,
  materialName,
  onClose,
  onSuccess,
}) => {
  const [trialId, setTrialId] = useState(`TRIAL-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`);
  const [origin, setOrigin] = useState<'REAL_PRODUCTION' | 'REAL_PILOT' | 'SYNTHETIC_TEST' | 'DEMO'>('REAL_PILOT');
  const [shelfLife, setShelfLife] = useState<string>('');
  const [otr, setOtr] = useState<string>('');
  const [co2tr, setCo2tr] = useState<string>('');
  const [wvtr, setWvtr] = useState<string>('');
  const [condition, setCondition] = useState<string>('ACCEPTABLE');
  const [investigator, setInvestigator] = useState<string>('');
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FeedbackResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    const payload: FeedbackSubmission = {
      recommendation_run_id: recommendationRunId,
      candidate_id: candidateId,
      trial_identifier: trialId,
      observation_origin: origin,
      observed_shelf_life_days: shelfLife !== '' ? parseFloat(shelfLife) : undefined,
      observed_otr: otr !== '' ? parseFloat(otr) : undefined,
      observed_co2tr: co2tr !== '' ? parseFloat(co2tr) : undefined,
      observed_wvtr: wvtr !== '' ? parseFloat(wvtr) : undefined,
      observed_product_condition: condition,
      evidence_source_metadata: investigator ? { investigator_name: investigator } : undefined,
    };

    try {
      const res = await submitFeedback(payload);
      setResult(res);
      if (onSuccess) onSuccess(res);
    } catch (err: any) {
      setError(err.message || 'Failed to submit trial feedback.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-slate-900 text-white p-6 flex justify-between items-start">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Record Empirical Trial Observation</h2>
            <p className="text-xs text-slate-300 mt-1">
              Feedback Loop for Material: <span className="font-semibold text-white">{materialName || 'Candidate'}</span>
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl font-light transition-colors">
            &times;
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 p-3.5 rounded-lg text-xs text-red-800">
              {error}
            </div>
          )}

          {result ? (
            <div className="space-y-6">
              <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="text-emerald-700 font-bold text-sm">Feedback Recorded & Analyzed Successfully</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold">
                    {result.validation_status}
                  </span>
                </div>
                <p className="text-xs text-emerald-800 mt-1">
                  Feedback ID: <span className="font-mono">{result.feedback_id}</span>
                </p>
              </div>

              {/* Comparisons */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
                  Predicted vs Observed Comparison
                </h4>
                <div className="space-y-2">
                  {result.comparisons.map((c, i) => (
                    <div key={i} className="p-3.5 rounded-xl border border-slate-200 bg-slate-50 text-xs flex flex-col gap-1">
                      <div className="flex justify-between items-center">
                        <span className="font-bold text-slate-800 capitalize">{c.property_name.replace(/_/g, ' ')}</span>
                        <span className={`px-2 py-0.5 rounded font-bold uppercase text-[10px] ${
                          c.comparison_status === 'MATCHED_WITHIN_INTERVAL' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {c.comparison_status.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-slate-600">{c.explanation}</p>
                      <div className="flex gap-4 font-mono text-[11px] text-slate-700 mt-1">
                        {c.predicted_value !== undefined && (
                          <span>Predicted: {c.is_predicted_interval ? `[${c.predicted_min} — ${c.predicted_max}]` : c.predicted_value} {c.unit}</span>
                        )}
                        {c.observed_value !== undefined && (
                          <span>Observed: {c.observed_value} {c.unit}</span>
                        )}
                        {c.discrepancy_residual != null && (
                          <span className="font-semibold text-slate-900">
                            Residual: {c.discrepancy_residual > 0 ? `+${Number(c.discrepancy_residual).toFixed(2)}` : Number(c.discrepancy_residual).toFixed(2)} {c.unit}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Model Update Candidates */}
              {result.model_update_candidates.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900 mb-2">
                    Model Update Candidate Generated ({result.model_update_candidates.length})
                  </h4>
                  <p className="text-xs text-amber-800 mb-3">
                    Discrepancy flagged for human expert review. Zero automatic model retraining has occurred, preserving scientific freeze.
                  </p>
                  <div className="space-y-2">
                    {result.model_update_candidates.map((uc) => (
                      <div key={uc.id} className="bg-white p-3 rounded-lg border border-amber-200 text-xs">
                        <div className="flex justify-between font-semibold text-slate-800">
                          <span>{uc.affected_component}: {uc.affected_property}</span>
                          <span className="text-[10px] uppercase font-bold text-amber-700">{uc.update_status}</span>
                        </div>
                        <p className="text-slate-600 text-[11px] mt-1">{uc.discrepancy_evidence_summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Trial Identifier</label>
                  <input
                    type="text"
                    required
                    value={trialId}
                    onChange={(e) => setTrialId(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 font-mono shadow-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Observation Origin</label>
                  <select
                    value={origin}
                    onChange={(e: any) => setOrigin(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white shadow-sm font-semibold"
                  >
                    <option value="REAL_PILOT">Real Pilot Trial</option>
                    <option value="REAL_PRODUCTION">Real Production</option>
                    <option value="SYNTHETIC_TEST">Synthetic Test</option>
                    <option value="DEMO">Demo Scenario</option>
                  </select>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Measured Packaging Trial Outcomes
                </h4>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-slate-600 mb-1">Observed Shelf Life (days)</label>
                    <input
                      type="number"
                      step="any"
                      min="0.1"
                      value={shelfLife}
                      onChange={(e) => setShelfLife(e.target.value)}
                      placeholder="e.g. 16.5"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm text-slate-900 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-600 mb-1">Observed OTR (cm³/m²·day·atm)</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={otr}
                      onChange={(e) => setOtr(e.target.value)}
                      placeholder="e.g. 1850"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm text-slate-900 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-600 mb-1">Observed CO2TR (cm³/m²·day·atm)</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={co2tr}
                      onChange={(e) => setCo2tr(e.target.value)}
                      placeholder="e.g. 7400"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm text-slate-900 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-600 mb-1">Observed WVTR (g/m²·day)</label>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={wvtr}
                      onChange={(e) => setWvtr(e.target.value)}
                      placeholder="e.g. 4.2"
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm text-slate-900 bg-white"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Product Quality Condition</label>
                  <select
                    value={condition}
                    onChange={(e) => setCondition(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white shadow-sm"
                  >
                    <option value="ACCEPTABLE">ACCEPTABLE</option>
                    <option value="MARGINAL">MARGINAL</option>
                    <option value="SPOILED">SPOILED</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Lead Investigator / Lab</label>
                  <input
                    type="text"
                    value={investigator}
                    onChange={(e) => setInvestigator(e.target.value)}
                    placeholder="e.g. Postharvest Lab 2"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 shadow-sm"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 text-xs font-semibold rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? 'Evaluating Discrepancies...' : 'Submit Trial Feedback'}
                </button>
              </div>
            </form>
          )}
        </div>

        {result && (
          <div className="bg-slate-50 p-4 px-6 border-t border-slate-200 flex justify-end">
            <button
              onClick={onClose}
              className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
