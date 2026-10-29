import React, { useState } from 'react';
import {
  Settings,
  Key,
  Globe,
  Database,
  CheckCircle2
} from 'lucide-react';

import { API_BASE_URL } from '../api/client';

export const SettingsPage: React.FC = () => {
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-xs">
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full mb-1">
          <Settings size={14} />
          System Configuration & Preferences
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Review backend connectivity, database configuration, and Google OAuth parameters.
        </p>
      </div>

      {saved && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
          <span>Local configuration preferences updated successfully.</span>
        </div>
      )}

      {/* Settings Forms */}
      <form onSubmit={handleSave} className="space-y-6">
        
        {/* API Endpoint Configuration */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <Globe size={18} className="text-blue-600" />
            Backend Connection
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">FastAPI Backend URL</label>
              <input
                type="text"
                disabled
                value={API_BASE_URL}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl bg-slate-50 text-slate-600 font-mono"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Configured via VITE_API_BASE_URL</span>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">CORS Client Origin</label>
              <input
                type="text"
                disabled
                value={window.location.origin}
                className="w-full px-3 py-2 border border-slate-200 rounded-xl bg-slate-50 text-slate-600 font-mono"
              />
              <span className="text-[10px] text-slate-400 mt-1 block">Authorized Web SPA Origin</span>
            </div>
          </div>
        </div>

        {/* Database & Storage Architecture */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <Database size={18} className="text-emerald-600" />
            Database Topology
          </h2>

          <div className="space-y-3 text-xs">
            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="font-bold text-slate-800 block">Scientific Knowledge Base:</span>
              <p className="text-slate-500">
                SQLite canonical repository (<code>food_packaging.db</code>) maintaining verified commodity kinetics and film barrier properties.
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <span className="font-bold text-slate-800 block">Authentication & User Store:</span>
              <p className="text-slate-500">
                MySQL active datastore (<code>localhost:3306/foodpack_ai</code>) preserving user identity records, profile pictures, and timestamps.
              </p>
            </div>
          </div>
        </div>

        {/* Security & OAuth */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 pb-3 border-b border-slate-100">
            <Key size={18} className="text-purple-600" />
            Authentication & Security
          </h2>

          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} className="text-emerald-500" />
              <span>Google OAuth 2.0 Authorization Code flow with CSRF token validation</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} className="text-emerald-500" />
              <span>HS256 JWT access tokens signed with server-side secret key</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 size={14} className="text-emerald-500" />
              <span>Zero client-side credential exposure (client secrets isolated in backend environment)</span>
            </div>
          </div>
        </div>

      </form>
    </div>
  );
};
