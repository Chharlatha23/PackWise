import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  Search,
  RefreshCw,
  CheckCircle2,
  Filter
} from 'lucide-react';

import { fetchEvidenceLibrary } from '../api/client';

export const EvidenceLibrary: React.FC = () => {
  const [records, setRecords] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClass, setFilterClass] = useState<string>('all');

  const loadEvidence = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchEvidenceLibrary(100);
      setRecords(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load scientific evidence library.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEvidence();
  }, []);

  const filteredRecords = records.filter((rec) => {
    const matchesSearch =
      rec.source_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.dataset_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rec.record_identifier?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesClass = filterClass === 'all' || rec.evidence_classification === filterClass;
    return matchesSearch && matchesClass;
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full mb-1">
            <BookOpen size={14} />
            Traceable Scientific Ground Truth
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Evidence Library</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Repository of canonical peer-reviewed publications, institutional food databases (USDA, UC Davis, WUR), and barrier property extractions.
          </p>
        </div>

        <button
          onClick={loadEvidence}
          className="p-2.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors cursor-pointer"
          title="Refresh evidence library"
        >
          <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Library Filter Bar & Table */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-4 bg-slate-50/50">
          <div className="relative flex-1 max-w-md">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Filter by source, institution, or reference..."
              className="w-full pl-9 pr-4 py-2 text-xs border border-slate-300 rounded-xl bg-white shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div className="flex items-center gap-3">
            <Filter size={14} className="text-slate-400" />
            <select
              value={filterClass}
              onChange={(e) => setFilterClass(e.target.value)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 bg-white text-slate-700 shadow-xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            >
              <option value="all">All Classifications</option>
              <option value="EXPERIMENTAL_LITERATURE_DATA">Experimental Literature</option>
              <option value="SOURCE_MEASURED">Source Measured</option>
              <option value="MODEL_PREDICTED">Model Predicted</option>
            </select>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-500">
            <RefreshCw size={24} className="animate-spin text-blue-600 mx-auto mb-2" />
            Loading scientific evidence records...
          </div>
        ) : error ? (
          <div className="p-6 text-center text-xs text-amber-900 bg-amber-50/80 m-4 rounded-xl border border-amber-200 space-y-2">
            <p className="font-semibold">Notice: {error}</p>
            <button
              onClick={loadEvidence}
              className="px-3 py-1 bg-white border border-amber-300 text-amber-900 font-medium rounded-lg hover:bg-amber-100 transition-colors cursor-pointer"
            >
              Retry
            </button>
          </div>
        ) : filteredRecords.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">
            No evidence records matched your search parameters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <th className="py-3 px-4">Source / Institution</th>
                  <th className="py-3 px-4">Dataset Type</th>
                  <th className="py-3 px-4">Classification</th>
                  <th className="py-3 px-4">Verification Status</th>
                  <th className="py-3 px-4">Extracted Physical Properties</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRecords.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-slate-900">
                      <div>{rec.source_name}</div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">{rec.record_identifier}</div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600 font-medium">
                      {rec.dataset_type}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                        {rec.evidence_classification?.replace(/_/g, ' ') || 'Literature'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
                        <CheckCircle2 size={13} className="text-emerald-500" />
                        {rec.verification_status?.replace(/_/g, ' ') || 'Verified'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-600">
                      {rec.observations && rec.observations.length > 0 ? (
                        <div className="space-y-1">
                          {rec.observations.map((o: any, i: number) => (
                            <div key={i} className="text-[11px]">
                              <span className="font-semibold text-slate-800">{o.property_name}:</span> {o.value} {o.unit}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Canonical metadata record</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
