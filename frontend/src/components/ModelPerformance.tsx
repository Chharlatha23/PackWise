import React from 'react';
import {
  Activity,
  ShieldCheck
} from 'lucide-react';


export const ModelPerformance: React.FC = () => {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs">
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full mb-1">
          <Activity size={14} />
          Algorithm & Search Engine Verification
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Model Performance & Search Tiers</h1>
        <p className="text-sm text-slate-500 mt-1 max-w-2xl">
          Scientific hierarchy of PackWise inverse-design search engines, epistemic out-of-distribution (OOD) criteria, and exact-physics verification.
        </p>
      </div>

      {/* 3 Solver Architecture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* M9 Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md">
              Tier M9
            </span>
            <span className="text-xs font-semibold text-slate-500">Baseline</span>
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Deterministic Enumeration</h3>
            <p className="text-xs text-slate-500 mt-1">Exhaustive discrete candidate lattice exploration.</p>
          </div>
          <div className="space-y-2 text-xs divide-y divide-slate-100">
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Methodology:</span>
              <span className="font-semibold text-slate-800">Brute-Force Lattice</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Interval Handling:</span>
              <span className="font-semibold text-emerald-700">Exact Bounds Preserved</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">ML Surrogates:</span>
              <span className="font-semibold text-slate-700">None (Pure Physics)</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Evaluation Scope:</span>
              <span className="font-semibold text-blue-700">Full Lattice Enumeration</span>
            </div>
          </div>
        </div>

        {/* M10 Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-md">
              Tier M10
            </span>
            <span className="text-xs font-semibold text-slate-500">Heuristic</span>
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Adaptive Heuristic Search</h3>
            <p className="text-xs text-slate-500 mt-1">Domain-informed candidate ranking without learned models.</p>
          </div>
          <div className="space-y-2 text-xs divide-y divide-slate-100">
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Methodology:</span>
              <span className="font-semibold text-slate-800">Adaptive Pruning</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Interval Handling:</span>
              <span className="font-semibold text-emerald-700">Exact Bounds Preserved</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">ML Surrogates:</span>
              <span className="font-semibold text-slate-700">None (Deterministic)</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Search Strategy:</span>
              <span className="font-semibold text-indigo-700">Prioritized Traversal</span>
            </div>
          </div>
        </div>

        {/* M11 Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-bold uppercase tracking-wider text-purple-600 bg-purple-50 px-2.5 py-1 rounded-md">
              Tier M11
            </span>
            <span className="text-xs font-semibold text-slate-500">Surrogate-Guided</span>
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Surrogate-Assisted Search</h3>
            <p className="text-xs text-slate-500 mt-1">Surrogate-guided candidate ordering with exact physics verification.</p>
          </div>
          <div className="space-y-2 text-xs divide-y divide-slate-100">
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Methodology:</span>
              <span className="font-semibold text-slate-800">OOD-Gated Surrogate</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Final Gate:</span>
              <span className="font-semibold text-emerald-700">Exact Physical Equations</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">ML Surrogates:</span>
              <span className="font-semibold text-purple-700">Candidate Prioritizer</span>
            </div>
            <div className="pt-2 flex justify-between">
              <span className="text-slate-500">Safety Authority:</span>
              <span className="font-semibold text-blue-700">Exact Physics Sovereign</span>
            </div>
          </div>
        </div>

      </div>

      {/* Governance & Verifiability Statement */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs space-y-4">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck size={20} className="text-blue-600" />
          Rigorous Scientific Principles & Verification Mandate
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-slate-600 leading-relaxed">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <span className="font-bold text-slate-900 block text-sm">Authoritative Exact-Physics Barrier:</span>
            <p>
              Surrogate models in M11 only prioritize evaluation sequence. A candidate packaging design cannot enter the verified non-dominated Pareto front unless it has successfully passed the full closed-form differential equations for oxygen and carbon dioxide equilibrium and water vapor permeation.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
            <span className="font-bold text-slate-900 block text-sm">Strict Epistemic State Preservation:</span>
            <p>
              The system operates strictly across three classifications: <span className="font-semibold text-emerald-700">FEASIBLE</span>, <span className="font-semibold text-red-700">INFEASIBLE</span>, and <span className="font-semibold text-amber-700">UNKNOWN</span>. When experimental data is absent, unknown status is explicitly preserved and never collapsed to artificial numbers.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
