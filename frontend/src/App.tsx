import { useState, useEffect } from 'react';
import { PackagingRequestForm } from './components/PackagingRequestForm';
import { RecommendationResults } from './components/RecommendationResults';
import { fetchRecommendation, checkHealth } from './api/client';
import type { PackagingRequest, RecommendationResponse } from './types/api';

function App() {
  const [results, setResults] = useState<RecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isApiConnected, setIsApiConnected] = useState<boolean | null>(null);

  useEffect(() => {
    const verifyApi = async () => {
      const isConnected = await checkHealth();
      setIsApiConnected(isConnected);
    };
    verifyApi();
    const interval = setInterval(verifyApi, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const handleRequestSubmit = async (request: PackagingRequest) => {
    setIsLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const response = await fetchRecommendation(request);
      setResults(response);
    } catch (err: any) {
      setError(err.message || 'Unable to connect to the recommendation engine.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8 font-sans text-slate-900">
      <div className="max-w-6xl mx-auto space-y-8">
        
        <header className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">AI Food Packaging Optimizer</h1>
            <p className="text-sm text-slate-500 mt-1">Scientific Inverse-Design Recommendation Engine</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 shadow-inner shrink-0">
            <span className="text-xs font-medium text-slate-600 uppercase tracking-wide">API Status</span>
            <div className={`w-2 h-2 rounded-full ${isApiConnected === null ? 'bg-slate-300' : isApiConnected ? 'bg-emerald-500' : 'bg-red-500'}`} />
            <span className={`text-xs font-medium ${isApiConnected === null ? 'text-slate-500' : isApiConnected ? 'text-emerald-700' : 'text-red-700'}`}>
              {isApiConnected === null ? 'Connecting...' : isApiConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </header>

        <PackagingRequestForm onSubmit={handleRequestSubmit} isLoading={isLoading} />

        {error && (
          <div className="bg-red-50 border border-red-200 p-4 rounded-xl shadow-sm">
            <h3 className="font-semibold text-red-900">Execution Failed</h3>
            <p className="text-red-800 text-sm mt-1">{error}</p>
          </div>
        )}

        {results && <RecommendationResults results={results} />}
      </div>
    </div>
  );
}

export default App;
