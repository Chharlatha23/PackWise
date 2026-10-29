import React, { useEffect, useState } from 'react';
import {
  Scale,
  Search,
  Filter,
  RefreshCw
} from 'lucide-react';

import { fetchPackagingMaterials } from '../api/client';

export const PackageComparison: React.FC = () => {
  const [materials, setMaterials] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStructure, setSelectedStructure] = useState<string>('all');
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);

  const loadMaterials = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchPackagingMaterials();
      setMaterials(data);
      if (data.length >= 2) {
        setSelectedForCompare([data[0].id, data[1].id]);
      } else if (data.length === 1) {
        setSelectedForCompare([data[0].id]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load packaging candidates');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMaterials();
  }, []);

  const toggleSelect = (id: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 4) {
        return [...prev.slice(1), id];
      }
      return [...prev, id];
    });
  };

  const filteredMaterials = materials.filter((m) => {
    const matchesSearch = m.material_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStruct = selectedStructure === 'all' || m.structure_type === selectedStructure;
    return matchesSearch && matchesStruct;
  });

  const comparedMaterials = materials.filter((m) => selectedForCompare.includes(m.id));

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full mb-1">
            <Scale size={14} />
            Candidate Cross-Comparison
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Package Comparison</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Directly cross-reference oxygen, carbon dioxide, and water vapor barrier performance across canonical packaging films.
          </p>
        </div>

        <button
          onClick={loadMaterials}
          className="p-2.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors cursor-pointer"
          title="Refresh material database"
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Comparison Grid (Selected Items) */}
      {comparedMaterials.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Side-by-Side Property Matrix</h2>
              <p className="text-xs text-slate-500">
                Comparing {comparedMaterials.length} selected candidate{comparedMaterials.length > 1 ? 's' : ''} (select up to 4 from table below)
              </p>
            </div>
            <span className="text-xs text-slate-400 font-medium">Standard Barrier Units</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {comparedMaterials.map((mat) => {
              const otr = mat.properties?.OTR;
              const co2tr = mat.properties?.CO2TR;
              const wvtr = mat.properties?.WVTR;

              return (
                <div key={mat.id} className="p-4 rounded-xl border-2 border-blue-500/30 bg-blue-50/20 space-y-4">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                      {mat.structure_type || 'Film'}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 mt-1.5 line-clamp-2">{mat.material_name}</h3>
                  </div>

                  <div className="space-y-2 text-xs divide-y divide-slate-100">
                    <div className="pt-2 flex justify-between items-baseline">
                      <span className="text-slate-500">OTR:</span>
                      <span className="font-semibold text-slate-800">
                        {otr?.value !== undefined ? `${otr.value} ${otr.unit || 'cm³/m²·d·bar'}` : 'Not Reported'}
                      </span>
                    </div>

                    <div className="pt-2 flex justify-between items-baseline">
                      <span className="text-slate-500">CO₂TR:</span>
                      <span className="font-semibold text-slate-800">
                        {co2tr?.value !== undefined ? `${co2tr.value} ${co2tr.unit || 'cm³/m²·d·bar'}` : 'Not Reported'}
                      </span>
                    </div>

                    <div className="pt-2 flex justify-between items-baseline">
                      <span className="text-slate-500">WVTR:</span>
                      <span className="font-semibold text-slate-800">
                        {wvtr?.value !== undefined ? `${wvtr.value} ${wvtr.unit || 'g/m²·d'}` : 'Not Reported'}
                      </span>
                    </div>

                    <div className="pt-2 flex justify-between items-baseline">
                      <span className="text-slate-500">Nominal Thickness:</span>
                      <span className="font-semibold text-slate-800">
                        {otr?.thickness_um ?? wvtr?.thickness_um ?? 'Variable'} µm
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Material Master Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
        {/* Table Filters */}
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-4 bg-slate-50/50">
          <div className="relative flex-1 max-w-md">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by polymer or material name..."
              className="w-full pl-9 pr-4 py-2 text-xs border border-slate-300 rounded-xl bg-white shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-3">
            <Filter size={14} className="text-slate-400" />
            <select
              value={selectedStructure}
              onChange={(e) => setSelectedStructure(e.target.value)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-700 shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            >
              <option value="all">All Structures</option>
              <option value="MONOLAYER">Monolayer</option>
              <option value="MULTILAYER">Multilayer</option>
              <option value="COATED">Coated</option>
            </select>
          </div>
        </div>

        {/* Table Content */}
        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <RefreshCw size={24} className="animate-spin text-blue-600 mx-auto mb-2" />
            Loading material barrier records...
          </div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-amber-900 bg-amber-50/80 m-4 rounded-xl border border-amber-200 space-y-2">
            <p className="font-semibold">Notice: {error}</p>
            <button
              onClick={loadMaterials}
              className="px-3 py-1 bg-white border border-amber-300 text-amber-900 font-medium rounded-lg hover:bg-amber-100 transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        ) : filteredMaterials.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">
            No packaging materials match the current filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4 w-12 text-center">Compare</th>
                  <th className="py-3 px-4">Material Name</th>
                  <th className="py-3 px-4">Structure</th>
                  <th className="py-3 px-4">OTR (cm³/m²·d·bar)</th>
                  <th className="py-3 px-4">CO₂TR (cm³/m²·d·bar)</th>
                  <th className="py-3 px-4">WVTR (g/m²·d)</th>
                  <th className="py-3 px-4">Test Conditions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredMaterials.map((mat) => {
                  const isSelected = selectedForCompare.includes(mat.id);
                  const otr = mat.properties?.OTR;
                  const co2tr = mat.properties?.CO2TR;
                  const wvtr = mat.properties?.WVTR;

                  return (
                    <tr
                      key={mat.id}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        isSelected ? 'bg-blue-50/40' : ''
                      }`}
                    >
                      <td className="py-3 px-4 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(mat.id)}
                          className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-4 font-bold text-slate-900">
                        {mat.material_name}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium text-[10px]">
                          {mat.structure_type || 'Monolayer'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-slate-800">
                        {otr?.value !== undefined ? otr.value : '—'}
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-slate-800">
                        {co2tr?.value !== undefined ? co2tr.value : '—'}
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-slate-800">
                        {wvtr?.value !== undefined ? wvtr.value : '—'}
                      </td>
                      <td className="py-3 px-4 text-slate-500 text-[11px]">
                        {otr?.temperature_c ? `${otr.temperature_c}°C` : 'Standard temp'}, {otr?.rh_percent ? `${otr.rh_percent}% RH` : '0% RH'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
