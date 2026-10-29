import React, { useState, useEffect } from 'react';
import {
  Apple,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  Info,
  Check,
  Cpu,
  Layers,
  Thermometer,
  Box
} from 'lucide-react';
import type { PackagingRequest } from '../types/api';
import { fetchCommodities } from '../api/client';

interface PackagingRequestFormProps {
  onSubmit: (request: PackagingRequest, searchEngine: string) => void;
  isLoading: boolean;
}

export const PackagingRequestForm: React.FC<PackagingRequestFormProps> = ({ onSubmit, isLoading }) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [formData, setFormData] = useState<Partial<PackagingRequest>>({});
  const [searchEngine, setSearchEngine] = useState<string>('deterministic_exhaustive');
  const [commoditiesList, setCommoditiesList] = useState<string[]>([
    'apple',
    'durian',
    'salmon',
    'strawberry'
  ]);

  useEffect(() => {
    fetchCommodities().then((list) => {
      if (list && list.length > 0) {
        setCommoditiesList(list);
      }
    });
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    let parsedValue: string | number | undefined = value;

    if (type === 'number') {
      parsedValue = value === '' ? undefined : Number(value);
    }

    setFormData((prev) => ({
      ...prev,
      [name]: parsedValue === '' ? undefined : parsedValue,
    }));
  };

  const handleApplyPreset = (presetName: string) => {
    if (presetName === 'strawberry') {
      setFormData({
        commodity: 'strawberry',
        variety: 'Camarosa',
        product_form: 'whole',
        ripeness_stage: 'ripe',
        target_shelf_life_days: 14,
        storage_type: 'chilled',
        storage_temperature_c: 2.0,
        relative_humidity_percent: 92,
        product_mass_kg: 0.25,
        package_surface_area_m2: 0.045,
        package_headspace_volume_cm3: 250,
      });
    } else if (presetName === 'apple') {
      setFormData({
        commodity: 'apple',
        variety: 'Gala',
        product_form: 'whole',
        ripeness_stage: 'ripe',
        target_shelf_life_days: 60,
        storage_type: 'chilled',
        storage_temperature_c: 1.0,
        relative_humidity_percent: 90,
        product_mass_kg: 1.0,
        package_surface_area_m2: 0.12,
        package_headspace_volume_cm3: 500,
      });
    } else if (presetName === 'salmon') {
      setFormData({
        commodity: 'salmon',
        variety: 'Atlantic',
        product_form: 'fillet',
        ripeness_stage: 'fresh',
        target_shelf_life_days: 10,
        storage_type: 'chilled',
        storage_temperature_c: 1.0,
        relative_humidity_percent: 95,
        product_mass_kg: 0.3,
        package_surface_area_m2: 0.06,
        package_headspace_volume_cm3: 200,
      });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.commodity || !formData.product_form || !formData.ripeness_stage || !formData.target_shelf_life_days) {
      setCurrentStep(1);
      return;
    }
    if (!formData.storage_type) {
      setCurrentStep(2);
      return;
    }
    onSubmit(formData as PackagingRequest, searchEngine);
  };

  const getVarietySuggestions = () => {
    const commodity = (formData.commodity || '').trim().toLowerCase();
    if (commodity === 'apple') return ['Gala', 'Granny Smith'];
    if (commodity === 'durian') return ['Monthong'];
    if (commodity === 'salmon') return ['Atlantic'];
    if (commodity === 'strawberry') return ['Camarosa', 'Chandler'];
    return [];
  };

  const varietySuggestions = getVarietySuggestions();

  const isStep1Valid = !!(
    formData.commodity &&
    formData.product_form &&
    formData.ripeness_stage &&
    formData.target_shelf_life_days
  );

  const isStep2Valid = !!formData.storage_type;

  const steps = [
    { number: 1, title: 'Commodity Profile', icon: Apple, desc: 'Product specs & shelf life' },
    { number: 2, title: 'Storage & Logistics', icon: Thermometer, desc: 'Environmental parameters' },
    { number: 3, title: 'Scientific Properties', icon: Layers, desc: 'Optional for evidence inference' },
    { number: 4, title: 'Package Geometry', icon: Box, desc: 'Dimensions & solver stage' },
  ];

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-xs border border-slate-200 overflow-hidden">
      {/* Top Banner with Presets */}
      <div className="bg-slate-900 px-6 py-5 text-white flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-400 uppercase tracking-wider mb-1">
            <Cpu size={14} />
            Inverse-Design Solver Input
          </div>
          <h2 className="text-xl font-bold tracking-tight">Packaging Recommendation Request</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Define food commodity context, supply chain storage conditions, and solver tier.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
            <Sparkles size={13} className="text-amber-400" />
            Quick Presets:
          </span>
          <button
            type="button"
            onClick={() => handleApplyPreset('strawberry')}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1.5 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          >
            Strawberry
          </button>
          <button
            type="button"
            onClick={() => handleApplyPreset('apple')}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1.5 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          >
            Apple
          </button>
          <button
            type="button"
            onClick={() => handleApplyPreset('salmon')}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1.5 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          >
            Salmon
          </button>
          <button
            type="button"
            onClick={() => handleApplyPreset('durian')}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1.5 rounded-lg border border-slate-700 transition-colors cursor-pointer"
          >
            Durian
          </button>
        </div>
      </div>

      {/* Guided Stepper Tabs */}
      <div className="border-b border-slate-200 bg-slate-50/60 px-6 py-3 overflow-x-auto">
        <div className="flex items-center justify-between min-w-[600px] gap-4">
          {steps.map((s, idx) => {
            const Icon = s.icon;
            const isCompleted = currentStep > s.number;
            const isCurrent = currentStep === s.number;
            return (
              <React.Fragment key={s.number}>
                <button
                  type="button"
                  onClick={() => setCurrentStep(s.number)}
                  className={`flex items-center gap-3 text-left py-1.5 px-2 rounded-lg transition-colors cursor-pointer ${
                    isCurrent
                      ? 'text-blue-700 font-semibold'
                      : isCompleted
                      ? 'text-slate-700 hover:text-slate-900'
                      : 'text-slate-400 hover:text-slate-600'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                      isCurrent
                        ? 'bg-blue-600 text-white shadow-xs'
                        : isCompleted
                        ? 'bg-emerald-500 text-white'
                        : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {isCompleted ? <Check size={14} /> : <Icon size={14} />}
                  </div>
                  <div>
                    <div className="text-xs font-bold leading-none">{s.title}</div>
                    <div className="text-[10px] text-slate-400 mt-0.5">{s.desc}</div>
                  </div>
                </button>
                {idx < steps.length - 1 && (
                  <div className="flex-1 h-px bg-slate-200 min-w-8" />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>


      {/* Step Form Body */}
      <div className="p-6 sm:p-8 space-y-6">
        
        {/* Step 1: Commodity Profile */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Step 1 — Commodity Profile</h3>
              <p className="text-xs text-slate-500 mt-0.5">Specify basic food product identity and required shelf-life target.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Commodity <span className="text-red-500">*</span>
                </label>
                <input
                  required
                  type="text"
                  list="commodity-suggestions"
                  name="commodity"
                  value={formData.commodity || ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. strawberry, apple, salmon"
                />
                <datalist id="commodity-suggestions">
                  {commoditiesList.map((comm) => (
                    <option key={comm} value={comm} />
                  ))}
                </datalist>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Variety
                </label>
                <input
                  type="text"
                  list="variety-suggestions"
                  name="variety"
                  value={formData.variety || ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. Camarosa, Gala"
                />
                <datalist id="variety-suggestions">
                  {varietySuggestions.map((v) => (
                    <option key={v} value={v} />
                  ))}
                </datalist>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Product Form <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  name="product_form"
                  value={formData.product_form || ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white text-slate-900"
                >
                  <option value="" disabled>Select product form...</option>
                  <option value="whole">Whole</option>
                  <option value="sliced">Sliced</option>
                  <option value="diced">Diced</option>
                  <option value="shredded">Shredded</option>
                  <option value="puree">Puree</option>
                  <option value="juice">Juice</option>
                  <option value="fillet">Fillet</option>
                  <option value="portioned">Portioned</option>
                  <option value="ground">Ground</option>
                  <option value="powder">Powder</option>
                  <option value="liquid">Liquid</option>
                  <option value="paste">Paste</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Ripeness Stage <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  name="ripeness_stage"
                  value={formData.ripeness_stage || ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white text-slate-900"
                >
                  <option value="" disabled>Select ripeness stage...</option>
                  <option value="immature">Immature</option>
                  <option value="mature_green">Mature Green</option>
                  <option value="breaker">Breaker</option>
                  <option value="turning">Turning</option>
                  <option value="ripe">Ripe</option>
                  <option value="fully_ripe">Fully Ripe</option>
                  <option value="overripe">Overripe</option>
                  <option value="fresh">Fresh (meat/seafood)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Target Shelf Life (days) <span className="text-red-500">*</span>
                </label>
                <input
                  required
                  type="number"
                  min="1"
                  step="any"
                  name="target_shelf_life_days"
                  value={formData.target_shelf_life_days || ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. 14"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Storage & Logistics */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Step 2 — Storage & Logistics</h3>
              <p className="text-xs text-slate-500 mt-0.5">Define cold chain conditions and transport durations.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Storage Type <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  name="storage_type"
                  value={formData.storage_type || ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white text-slate-900"
                >
                  <option value="" disabled>Select a type...</option>
                  <option value="chilled">Chilled</option>
                  <option value="ambient">Ambient</option>
                  <option value="frozen">Frozen</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Storage Temperature (°C)
                </label>
                <input
                  type="number"
                  step="any"
                  name="storage_temperature_c"
                  value={formData.storage_temperature_c ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. 2.0"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Relative Humidity (%)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="100"
                  name="relative_humidity_percent"
                  value={formData.relative_humidity_percent ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. 90"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Transportation Type
                </label>
                <input
                  type="text"
                  name="transportation_type"
                  value={formData.transportation_type || ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. Refrigerated truck, Air freight"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Transportation Duration (days)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  name="transportation_duration_days"
                  value={formData.transportation_duration_days ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. 2"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Scientific Properties */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div className="pb-3 border-b border-slate-100 flex flex-col sm:flex-row justify-between sm:items-baseline gap-2">
              <div>
                <h3 className="text-base font-bold text-slate-900">Step 3 — Scientific Properties</h3>
                <p className="text-xs text-slate-500 mt-0.5">Direct physical measurements or allow evidence-driven inference.</p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-3">
              <Info size={16} className="text-amber-700 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block text-amber-950">Optional Property Inputs:</span>
                Leave fields blank to permit the backend multi-tier inference engine to resolve properties from canonical USDA, UC Davis, and CIRAD/WUR literature.
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Moisture Content (%)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="100"
                  name="moisture_percent"
                  value={formData.moisture_percent ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="Blank to infer"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Fat Content (%)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="100"
                  name="fat_percent"
                  value={formData.fat_percent ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="Blank to infer"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  pH Level
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="14"
                  name="ph"
                  value={formData.ph ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="Blank to infer"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Respiration Rate (mg/kg·h)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  name="respiration_rate"
                  value={formData.respiration_rate ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="Blank to infer"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Package Geometry & Search Tier */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div className="pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Step 4 — Package Geometry & Solver Tier</h3>
              <p className="text-xs text-slate-500 mt-0.5">Specify dimensional constraints and choose the inverse-design search tier.</p>
            </div>

            {/* Inverse Design Search Tier */}
            <div className="bg-slate-50 p-5 rounded-xl border border-slate-200 space-y-3">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                    Inverse-Design Search Stage
                  </label>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Select the optimization algorithm to explore the non-dominated Pareto front.
                  </p>
                </div>
                <select
                  value={searchEngine}
                  onChange={(e) => setSearchEngine(e.target.value)}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-900 shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="deterministic_exhaustive">M9 — Deterministic Baseline (Exhaustive)</option>
                  <option value="intelligent">M10 — Adaptive Heuristic Search</option>
                  <option value="ai_surrogate_prioritized">M11 — Surrogate-Assisted Search</option>
                </select>
              </div>

              <div className="text-xs text-slate-600 bg-white p-3 rounded-lg border border-slate-200/80">
                {searchEngine === 'deterministic_exhaustive' && (
                  <span><strong>M9 Deterministic Baseline:</strong> Exhaustively evaluates full candidate lattice; preserves interval physical boundaries.</span>
                )}
                {searchEngine === 'intelligent' && (
                  <span><strong>M10 Adaptive Heuristic:</strong> Domain-guided deterministic prioritization without unverified ML models.</span>
                )}
                {searchEngine === 'ai_surrogate_prioritized' && (
                  <span><strong>M11 Surrogate-Assisted:</strong> Machine learning shortlists candidates; <em>exact physical evaluation remains authoritative for Pareto front entry</em>.</span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Package Surface Area (m²)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  name="package_surface_area_m2"
                  value={formData.package_surface_area_m2 ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. 0.045"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Headspace Volume (cm³)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  name="package_headspace_volume_cm3"
                  value={formData.package_headspace_volume_cm3 ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. 250"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Product Mass (kg)
                </label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  name="product_mass_kg"
                  value={formData.product_mass_kg ?? ''}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900"
                  placeholder="e.g. 0.25"
                />
              </div>
            </div>
          </div>
        )}

        {/* Stepper Navigation Controls */}
        <div className="pt-6 border-t border-slate-100 flex items-center justify-between">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={() => setCurrentStep((prev) => prev - 1)}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors cursor-pointer"
            >
              <ChevronLeft size={16} />
              Back
            </button>
          ) : (
            <div />
          )}

          <div className="flex items-center gap-3">
            {currentStep < 4 ? (
              <button
                type="button"
                onClick={() => setCurrentStep((prev) => prev + 1)}
                disabled={(currentStep === 1 && !isStep1Valid) || (currentStep === 2 && !isStep2Valid)}
                className="flex items-center gap-1.5 px-5 py-2.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-xs cursor-pointer"
              >
                Continue
                <ChevronRight size={16} />
              </button>
            ) : (
              <button
                type="submit"
                disabled={isLoading}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-blue-700 text-white text-sm font-semibold hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-xs cursor-pointer"
              >
                {isLoading && (
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {isLoading ? 'Executing Inverse-Design Solver...' : 'Generate Recommendations'}
              </button>
            )}
          </div>
        </div>

      </div>
    </form>
  );
};


