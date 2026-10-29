import React, { useEffect, useState } from 'react';
import {
  Cpu,
  FlaskConical,
  Layers,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Database,
  RefreshCw
} from 'lucide-react';
import { fetchOverviewMetrics } from '../api/client';
import type { NavItemKey } from './Sidebar';

interface OverviewPageProps {
  onNavigate: (item: NavItemKey) => void;
  userEmail?: string;
  userName?: string;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  onNavigate,
  userEmail,
  userName,
}) => {
  const [metrics, setMetrics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);


  const loadMetrics = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchOverviewMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load system metrics.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-1">
            <ShieldCheck size={14} />
            Scientific Decision Support System
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Welcome back, {userName || userEmail?.split('@')[0] || 'Researcher'}
          </h1>
          <p className="text-sm text-slate-500 max-w-2xl leading-relaxed">
            PackWise couples closed-form transpiration and respiration kinetics with multi-objective inverse-design optimization to generate exact-physics-verified food packaging specifications.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <button
            onClick={() => onNavigate('recommend')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium text-sm hover:bg-blue-700 active:scale-[0.99] transition-all shadow-xs cursor-pointer"
          >
            <Cpu size={16} />
            New Recommendation
          </button>
          <button
            onClick={loadMetrics}
            className="p-2.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors cursor-pointer"
            title="Refresh overview metrics"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200 text-xs text-amber-900 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold">Notice:</span>
            <span>{error}</span>
          </div>
          <button
            onClick={loadMetrics}
            className="px-3 py-1 rounded-lg bg-white border border-amber-300 text-amber-900 font-medium hover:bg-amber-100 transition-colors shrink-0 cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* Metrics Row */}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Canonical Materials</span>
            <Layers size={16} className="text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : metrics?.database_metrics?.packaging_materials ?? 11}
          </div>
          <p className="text-xs text-slate-500 mt-1">Verified films (LDPE, HDPE, BOPP, PLA, etc.)</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Commodity Profiles</span>
            <Database size={16} className="text-emerald-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : metrics?.database_metrics?.food_commodities ?? 17}
          </div>
          <p className="text-xs text-slate-500 mt-1">USDA & UC Davis produce datasets</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Evidence Records</span>
            <ShieldCheck size={16} className="text-purple-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : metrics?.database_metrics?.evidence_records ?? 47}
          </div>
          <p className="text-xs text-slate-500 mt-1">Traceable experimental literature entries</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Trial Observations</span>
            <FlaskConical size={16} className="text-amber-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isLoading ? '...' : metrics?.database_metrics?.trial_feedback_records ?? 0}
          </div>
          <p className="text-xs text-slate-500 mt-1">M12 human-governed audit entries</p>
        </div>
      </div>

      {/* Quick Action Cards & Scientific Pipeline Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left 2 Cols: Search Stages Overview */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Active Search Engines</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Configurable inverse-design solver tiers with authoritative exact-physics verification
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Operational
            </span>
          </div>

          <div className="space-y-4">
            <div className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors bg-slate-50/50 flex items-start gap-4">
              <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-800 flex items-center justify-center font-bold text-sm shrink-0">
                M9
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Deterministic Baseline</h3>
                  <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-slate-200 text-slate-700">Lattice Enumeration</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Exhaustively constructs thickness and barrier permutations across candidate material libraries. Exact non-dominated Pareto front sorting.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors bg-slate-50/50 flex items-start gap-4">
              <div className="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-800 flex items-center justify-center font-bold text-sm shrink-0">
                M10
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Adaptive Heuristic Search</h3>
                  <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">Heuristic Prioritized</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Applies deterministic domain-informed heuristics to rank candidate exploration order. No unverified machine learning models used.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors bg-slate-50/50 flex items-start gap-4">
              <div className="w-9 h-9 rounded-lg bg-purple-100 text-purple-800 flex items-center justify-center font-bold text-sm shrink-0">
                M11
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Surrogate-Assisted Optimization</h3>
                  <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-purple-100 text-purple-700">Exact-Physics Authoritative</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  ML surrogates accelerate exploration with epistemic out-of-distribution (OOD) gating. <strong>Exact physical equations remain the sole authority</strong> for Pareto admissibility.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Quick Access Tools */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <h2 className="text-lg font-bold text-slate-900 border-b border-slate-100 pb-3">Quick Workflows</h2>
            
            <button
              onClick={() => onNavigate('compare')}
              className="w-full text-left p-3.5 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 transition-all flex items-center justify-between group cursor-pointer"
            >
              <div className="space-y-0.5">
                <div className="text-sm font-semibold text-slate-800 group-hover:text-blue-700">Package Comparison</div>
                <div className="text-xs text-slate-500">Cross-reference OTR, CO₂TR, WVTR barrier specs</div>
              </div>
              <ArrowRight size={16} className="text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-1" />
            </button>

            <button
              onClick={() => onNavigate('whatif')}
              className="w-full text-left p-3.5 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 transition-all flex items-center justify-between group cursor-pointer"
            >
              <div className="space-y-0.5">
                <div className="text-sm font-semibold text-slate-800 group-hover:text-blue-700">What-If Analysis</div>
                <div className="text-xs text-slate-500">Perturb storage temp, RH, and transit durations</div>
              </div>
              <ArrowRight size={16} className="text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-1" />
            </button>

            <button
              onClick={() => onNavigate('feedback')}
              className="w-full text-left p-3.5 rounded-xl border border-slate-200 hover:border-blue-300 hover:bg-blue-50/40 transition-all flex items-center justify-between group cursor-pointer"
            >
              <div className="space-y-0.5">
                <div className="text-sm font-semibold text-slate-800 group-hover:text-blue-700">Trial Feedback & Audit</div>
                <div className="text-xs text-slate-500">Record trial measurements & model update candidates</div>
              </div>
              <ArrowRight size={16} className="text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-1" />
            </button>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-2">
            <div className="font-semibold text-slate-800 flex items-center gap-1.5">
              <CheckCircle2 size={15} className="text-emerald-600" />
              Scientific Compliance Policy
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              No automatic parameter retraining occurs. Empirical discrepancies generate structured audit candidates for human scientist review.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};
