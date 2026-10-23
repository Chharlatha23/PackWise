import React, { useState } from 'react';
import type { PackagingRequest } from '../types/api';

interface PackagingRequestFormProps {
  onSubmit: (request: PackagingRequest, searchEngine: string) => void;
  isLoading: boolean;
}

export const PackagingRequestForm: React.FC<PackagingRequestFormProps> = ({ onSubmit, isLoading }) => {
  const [formData, setFormData] = useState<Partial<PackagingRequest>>({});
  const [searchEngine, setSearchEngine] = useState<string>('deterministic_exhaustive');

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

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="bg-slate-800 px-6 py-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 className="text-lg font-medium text-white">Packaging Recommendation Request</h2>
          <p className="text-xs text-slate-300 mt-0.5">Define food commodity context and inverse-design execution parameters.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-300 font-medium">Quick Presets:</span>
          <button type="button" onClick={() => handleApplyPreset('strawberry')} className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-2.5 py-1 rounded border border-slate-600 transition-colors">Strawberry</button>
          <button type="button" onClick={() => handleApplyPreset('apple')} className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-2.5 py-1 rounded border border-slate-600 transition-colors">Apple</button>
          <button type="button" onClick={() => handleApplyPreset('salmon')} className="text-xs bg-slate-700 hover:bg-slate-600 text-white px-2.5 py-1 rounded border border-slate-600 transition-colors">Salmon</button>
        </div>
      </div>
      
      <div className="p-6 space-y-8">
        {/* Search Engine Tier Selector */}
        <section className="bg-slate-50 p-4 rounded-lg border border-slate-200">
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <div>
              <label className="block text-sm font-semibold text-slate-800">Inverse-Design Search Stage</label>
              <p className="text-xs text-slate-500 mt-0.5">Select the optimization tier according to the research protocol.</p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={searchEngine}
                onChange={(e) => setSearchEngine(e.target.value)}
                className="px-3 py-1.5 text-xs font-semibold rounded-md border border-slate-300 bg-white text-slate-800 shadow-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="deterministic_exhaustive">M9 — Deterministic Baseline (Exhaustive)</option>
                <option value="intelligent">M10 — Adaptive Heuristic Search</option>
                <option value="ai_surrogate_prioritized">M11 — Surrogate-Assisted Search (Exact Physics Verified)</option>
              </select>
            </div>
          </div>
          <div className="mt-2 text-[11px] text-slate-600">
            {searchEngine === 'deterministic_exhaustive' && 'Evaluates the complete candidate space deterministically without heuristic acceleration.'}
            {searchEngine === 'intelligent' && 'Uses deterministic adaptive candidate prioritization. Zero learned ML.'}
            {searchEngine === 'ai_surrogate_prioritized' && 'Surrogate models accelerate candidate shortlisting; all Pareto candidates are rigorously verified via exact physics.'}
          </div>
        </section>

        <section>
          <div className="mb-4 pb-2 border-b border-slate-100">
            <h3 className="text-base font-semibold text-slate-800">A. Commodity Profile</h3>
            <p className="text-sm text-slate-500">Core parameters defining the food product.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Commodity <span className="text-red-500">*</span></label>
              <input required type="text" list="commodity-suggestions" name="commodity" value={formData.commodity || ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="e.g. strawberry" />
              <datalist id="commodity-suggestions">
                <option value="apple" />
                <option value="durian" />
                <option value="salmon" />
                <option value="strawberry" />
              </datalist>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Variety</label>
              <input type="text" list="variety-suggestions" name="variety" value={formData.variety || ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="e.g. Camarosa" />
              <datalist id="variety-suggestions">
                {varietySuggestions.map(v => (
                  <option key={v} value={v} />
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Product Form <span className="text-red-500">*</span></label>
              <select required name="product_form" value={formData.product_form || ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-white text-slate-900">
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
              <label className="block text-sm font-medium text-slate-700 mb-1">Ripeness Stage <span className="text-red-500">*</span></label>
              <select required name="ripeness_stage" value={formData.ripeness_stage || ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-white text-slate-900">
                <option value="" disabled>Select ripeness stage...</option>
                <option value="immature">Immature</option>
                <option value="mature_green">Mature Green</option>
                <option value="breaker">Breaker</option>
                <option value="turning">Turning</option>
                <option value="ripe">Ripe</option>
                <option value="fully_ripe">Fully Ripe</option>
                <option value="overripe">Overripe</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Target Shelf Life (days) <span className="text-red-500">*</span></label>
              <input required type="number" min="1" step="any" name="target_shelf_life_days" value={formData.target_shelf_life_days || ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="e.g. 14" />
            </div>
          </div>
        </section>

        <section>
          <div className="mb-4 pb-2 border-b border-slate-100">
            <h3 className="text-base font-semibold text-slate-800">B. Storage & Logistics</h3>
            <p className="text-sm text-slate-500">Environmental conditions during the supply chain.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Storage Type <span className="text-red-500">*</span></label>
              <select required name="storage_type" value={formData.storage_type || ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm bg-white text-slate-900">
                <option value="" disabled>Select a type...</option>
                <option value="chilled">Chilled</option>
                <option value="ambient">Ambient</option>
                <option value="frozen">Frozen</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Storage Temperature (°C)</label>
              <input type="number" step="any" name="storage_temperature_c" value={formData.storage_temperature_c ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="e.g. 2.0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Relative Humidity (%)</label>
              <input type="number" step="any" min="0" max="100" name="relative_humidity_percent" value={formData.relative_humidity_percent ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="e.g. 90" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Transportation Type</label>
              <input type="text" name="transportation_type" value={formData.transportation_type || ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="e.g. Refrigerated truck" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Transportation Duration (days)</label>
              <input type="number" step="any" min="0" name="transportation_duration_days" value={formData.transportation_duration_days ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="e.g. 2" />
            </div>
          </div>
        </section>

        <section>
          <div className="mb-4 pb-2 border-b border-slate-100 flex flex-col sm:flex-row justify-between sm:items-baseline">
            <h3 className="text-base font-semibold text-slate-800">C. Scientific Properties <span className="font-normal text-slate-500 text-sm ml-2">(Optional — leave blank to allow evidence-based inference)</span></h3>
          </div>
          <p className="text-xs text-amber-800 bg-amber-50 px-3 py-2 rounded-md border border-amber-200 mb-4 inline-block shadow-sm">
            Unknown scientific properties are resolved by the backend inference engine when sufficient evidence exists.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Moisture (%)</label>
              <input type="number" step="any" min="0" max="100" name="moisture_percent" value={formData.moisture_percent ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="Blank to infer" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Fat (%)</label>
              <input type="number" step="any" min="0" max="100" name="fat_percent" value={formData.fat_percent ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="Blank to infer" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">pH</label>
              <input type="number" step="any" min="0" max="14" name="ph" value={formData.ph ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="Blank to infer" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Respiration Rate (mg/kg·h)</label>
              <input type="number" step="any" min="0" name="respiration_rate" value={formData.respiration_rate ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="Blank to infer" />
            </div>
          </div>
        </section>

        <section>
          <div className="mb-4 pb-2 border-b border-slate-100">
            <h3 className="text-base font-semibold text-slate-800">D. Package Geometry</h3>
            <p className="text-sm text-slate-500">Used by the packaging requirement and gas-exchange calculations.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-x-6 gap-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Surface Area (m²)</label>
              <input type="number" step="any" min="0" name="package_surface_area_m2" value={formData.package_surface_area_m2 ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="Optional" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Headspace Volume (cm³)</label>
              <input type="number" step="any" min="0" name="package_headspace_volume_cm3" value={formData.package_headspace_volume_cm3 ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="Optional" />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Product Mass (kg)</label>
              <input type="number" step="any" min="0" name="product_mass_kg" value={formData.product_mass_kg ?? ''} onChange={handleChange} className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm text-slate-900" placeholder="Optional" />
            </div>
          </div>
        </section>

        <div className="pt-6 flex justify-end border-t border-slate-100">
          <button 
            type="submit" 
            disabled={isLoading}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-700 text-white text-sm font-medium rounded-md shadow-sm hover:bg-blue-800 disabled:opacity-70 disabled:cursor-not-allowed transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            {isLoading && (
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {isLoading ? 'Analyzing Packaging Requirements...' : 'Generate Packaging Recommendation'}
          </button>
        </div>
      </div>
    </form>
  );
};
