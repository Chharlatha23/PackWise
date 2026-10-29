import React, { useState } from 'react';
import {
  SlidersHorizontal,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Thermometer,
  CloudRain,
  Clock,
  Truck
} from 'lucide-react';
import { fetchRecommendation } from '../api/client';
import type { PackagingRequest, RecommendationResponse } from '../types/api';

export const WhatIfAnalysis: React.FC = () => {
  // Baseline Scenario (Default Strawberry chilled 14d)
  const [baselineRequest] = useState<PackagingRequest>({

    commodity: 'strawberry',
    product_form: 'whole',
    ripeness_stage: 'ripe',
    target_shelf_life_days: 14,
    storage_type: 'chilled',
    storage_temperature_c: 2.0,
    relative_humidity_percent: 90,
    transportation_duration_days: 2,
    package_surface_area_m2: 0.045,
    package_headspace_volume_cm3: 250,
    product_mass_kg: 0.25,
  });

  // What-If Modified Parameters
  const [perturbedParams, setPerturbedParams] = useState({
    storage_temperature_c: 8.0, // Temperature abuse scenario (+6 C)
    relative_humidity_percent: 75, // Dry supply chain (-15% RH)
    target_shelf_life_days: 21, // Extended target (+7 days)
    transportation_duration_days: 5, // Extended transit
  });

  const [baselineResult, setBaselineResult] = useState<RecommendationResponse | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<RecommendationResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runComparison = async () => {
    setIsSimulating(true);
    setError(null);
    try {
      // 1. Execute baseline evaluation
      const resBase = await fetchRecommendation(baselineRequest, 'deterministic_exhaustive');
      setBaselineResult(resBase);

      // 2. Execute perturbed scenario through authoritative backend engine
      const modifiedRequest: PackagingRequest = {
        ...baselineRequest,
        storage_temperature_c: perturbedParams.storage_temperature_c,
        relative_humidity_percent: perturbedParams.relative_humidity_percent,
        target_shelf_life_days: perturbedParams.target_shelf_life_days,
        transportation_duration_days: perturbedParams.transportation_duration_days,
      };

      const resWhatIf = await fetchRecommendation(modifiedRequest, 'deterministic_exhaustive');
      setWhatIfResult(resWhatIf);
    } catch (err: any) {
      setError(err.message || 'What-If evaluation failed on backend recommendation pipeline.');
    } finally {
      setIsSimulating(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full mb-1">
            <SlidersHorizontal size={14} />
            Sensitivity & Scenario Stress-Testing
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">What-If Analysis</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Stress-test supply chain scenarios (e.g., cold chain temperature breaks, ambient dry logistics) via the authoritative exact-physics backend engine.
          </p>
        </div>

        <button
          onClick={runComparison}
          disabled={isSimulating}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 text-white font-semibold text-xs hover:bg-blue-700 disabled:opacity-50 transition-all shadow-xs cursor-pointer"
        >
          {isSimulating ? (
            <RefreshCw size={16} className="animate-spin" />
          ) : (
            <SlidersHorizontal size={16} />
          )}
          {isSimulating ? 'Solving Physics Scenarios...' : 'Run What-If Simulation'}
        </button>
      </div>

      {/* Parameter Control Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Baseline Scenario Box */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Baseline Context</span>
              <h3 className="text-base font-bold text-slate-900">Standard Chilled Logistics</h3>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 font-medium">Control</span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block mb-1">Commodity</span>
              <span className="font-bold text-slate-800 text-sm capitalize">{baselineRequest.commodity}</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block mb-1">Target Shelf Life</span>
              <span className="font-bold text-slate-800 text-sm">{baselineRequest.target_shelf_life_days} days</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block mb-1">Storage Temperature</span>
              <span className="font-bold text-slate-800 text-sm">{baselineRequest.storage_temperature_c}°C</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
              <span className="text-slate-400 block mb-1">Relative Humidity</span>
              <span className="font-bold text-slate-800 text-sm">{baselineRequest.relative_humidity_percent}%</span>
            </div>
          </div>
        </div>

        {/* Perturbed Parameter Box */}
        <div className="bg-white border-2 border-blue-500/30 rounded-2xl p-6 shadow-xs space-y-4 bg-blue-50/10">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Stress Parameters</span>
              <h3 className="text-base font-bold text-slate-900">Perturbed What-If Condition</h3>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-md bg-blue-100 text-blue-700 font-semibold">Stress Test</span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Thermometer size={13} className="text-red-500" />
                Storage Temp (°C)
              </label>
              <input
                type="number"
                step="0.5"
                value={perturbedParams.storage_temperature_c}
                onChange={(e) =>
                  setPerturbedParams({
                    ...perturbedParams,
                    storage_temperature_c: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white font-semibold text-slate-900 shadow-xs focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <CloudRain size={13} className="text-blue-500" />
                Relative Humidity (%)
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={perturbedParams.relative_humidity_percent}
                onChange={(e) =>
                  setPerturbedParams({
                    ...perturbedParams,
                    relative_humidity_percent: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white font-semibold text-slate-900 shadow-xs focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Clock size={13} className="text-amber-500" />
                Target Shelf Life (days)
              </label>
              <input
                type="number"
                min="1"
                value={perturbedParams.target_shelf_life_days}
                onChange={(e) =>
                  setPerturbedParams({
                    ...perturbedParams,
                    target_shelf_life_days: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white font-semibold text-slate-900 shadow-xs focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-700 mb-1 flex items-center gap-1">
                <Truck size={13} className="text-slate-500" />
                Transit Duration (days)
              </label>
              <input
                type="number"
                min="0"
                value={perturbedParams.transportation_duration_days}
                onChange={(e) =>
                  setPerturbedParams({
                    ...perturbedParams,
                    transportation_duration_days: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white font-semibold text-slate-900 shadow-xs focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
          </div>
        </div>

      </div>

      {/* Error Display */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center gap-2">
          <AlertCircle size={16} className="text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Side-by-Side Simulation Results */}
      {baselineResult && whatIfResult && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Exact-Physics Feasibility Shift</h2>
              <p className="text-xs text-slate-500">
                Comparing solver outcome between baseline and perturbed cold chain stress test
              </p>
            </div>
            <span className="text-xs text-slate-400 font-mono">Backend Run Traceable</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Baseline Outcome */}
            <div className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sm text-slate-900">Baseline Outcome</h4>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 font-semibold">
                  Control
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Evaluated Candidates:</span>
                  <span className="font-bold text-slate-800">{baselineResult.total_candidates_evaluated}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Feasible Count:</span>
                  <span className="font-bold text-emerald-700">{baselineResult.feasible_candidates_count}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Pareto Optimal Candidates:</span>
                  <span className="font-bold text-blue-700">{baselineResult.pareto_front?.candidates?.length || 0}</span>
                </div>
              </div>
            </div>

            {/* Perturbed Outcome */}
            <div className="p-5 rounded-xl border-2 border-blue-400/40 bg-blue-50/20 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sm text-slate-900">Perturbed Scenario Outcome</h4>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold">
                  Perturbed
                </span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Evaluated Candidates:</span>
                  <span className="font-bold text-slate-800">{whatIfResult.total_candidates_evaluated}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Feasible Count:</span>
                  <span className="font-bold text-emerald-700">{whatIfResult.feasible_candidates_count}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span className="text-slate-500">Pareto Optimal Candidates:</span>
                  <span className="font-bold text-blue-700">{whatIfResult.pareto_front?.candidates?.length || 0}</span>
                </div>
              </div>
            </div>

          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-2.5">
            <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block text-slate-800">Scientific Sensitivity Notice:</span>
              Higher temperatures accelerate Michaelis-Menten respiration rates, tightening the oxygen permeation window. Exact-physics validation ensures no unfeasible barrier material is recommended.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
