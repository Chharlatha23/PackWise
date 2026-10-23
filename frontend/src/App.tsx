import { useState, useEffect } from 'react';
import { PackagingRequestForm } from './components/PackagingRequestForm';
import { RecommendationResults } from './components/RecommendationResults';
import { ExplainabilityModal } from './components/ExplainabilityModal';
import { FeedbackModal } from './components/FeedbackModal';
import { FeedbackDashboard } from './components/FeedbackDashboard';
import { fetchRecommendation, checkHealth } from './api/client';
import type { PackagingRequest, RecommendationResponse, CandidateExplainabilityReport } from './types/api';

function App() {
  const [results, setResults] = useState<RecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isApiConnected, setIsApiConnected] = useState<boolean | null>(null);

  // Tab navigation
  const [currentView, setCurrentView] = useState<'optimizer' | 'feedback'>('optimizer');

  // Modals state
  const [activeExplainReport, setActiveExplainReport] = useState<CandidateExplainabilityReport | null>(null);
  const [feedbackModalConfig, setFeedbackModalConfig] = useState<{
    isOpen: boolean;
    candidateId?: string;
    materialName?: string;
  }>({ isOpen: false });

  useEffect(() => {
    const verifyApi = async () => {
      const isConnected = await checkHealth();
      setIsApiConnected(isConnected);
    };
    verifyApi();
    const interval = setInterval(verifyApi, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRequestSubmit = async (request: PackagingRequest, searchEngine: string) => {
    setIsLoading(true);
    setError(null);
    setResults(null);
    
    try {
      const response = await fetchRecommendation(request, searchEngine);
      setResults(response);
    } catch (err: any) {
      setError(err.message || 'Unable to connect to the recommendation engine.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOpenFeedback = (candidateId?: string, materialName?: string) => {
    setFeedbackModalConfig({
      isOpen: true,
      candidateId,
      materialName,
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8 font-sans text-slate-900">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Main Header */}
        <header className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">PackWise</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 font-semibold uppercase tracking-wider">
                Scientific Inverse-Design
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1 font-medium">
              PackWise — Evidence-Driven Inverse-Design Food Packaging Recommendation System
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 shadow-inner shrink-0">
              <span className="text-xs font-medium text-slate-600 uppercase tracking-wide">API Status</span>
              <div className={`w-2 h-2 rounded-full ${isApiConnected === null ? 'bg-slate-300' : isApiConnected ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <span className={`text-xs font-medium ${isApiConnected === null ? 'text-slate-500' : isApiConnected ? 'text-emerald-700' : 'text-red-700'}`}>
                {isApiConnected === null ? 'Connecting...' : isApiConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </header>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 bg-white px-6 rounded-xl shadow-sm">
          <button
            onClick={() => setCurrentView('optimizer')}
            className={`py-3.5 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              currentView === 'optimizer'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Recommendation Engine
          </button>
          <button
            onClick={() => setCurrentView('feedback')}
            className={`py-3.5 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              currentView === 'feedback'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Trial Feedback & Model Audit Ledger
          </button>
        </div>

        {/* View Router */}
        {currentView === 'optimizer' ? (
          <>
            <PackagingRequestForm onSubmit={handleRequestSubmit} isLoading={isLoading} />

            {error && (
              <div className="bg-red-50 border border-red-200 p-4 rounded-xl shadow-sm">
                <h3 className="font-semibold text-red-900">Recommendation Pipeline Error</h3>
                <p className="text-red-800 text-sm mt-1">{error}</p>
              </div>
            )}

            {results && (
              <RecommendationResults
                results={results}
                onExplainCandidate={(rep) => setActiveExplainReport(rep)}
                onRecordFeedback={(candId, matName) => handleOpenFeedback(candId, matName)}
              />
            )}
          </>
        ) : (
          <FeedbackDashboard onNewFeedbackClick={() => handleOpenFeedback()} />
        )}

        {/* Explainability Modal */}
        {activeExplainReport && (
          <ExplainabilityModal
            report={activeExplainReport}
            onClose={() => setActiveExplainReport(null)}
            onOpenFeedback={(candId, matName) => {
              setActiveExplainReport(null);
              handleOpenFeedback(candId, matName);
            }}
          />
        )}

        {/* Feedback Modal */}
        {feedbackModalConfig.isOpen && (
          <FeedbackModal
            recommendationRunId={results?.recommendation_run_id}
            candidateId={feedbackModalConfig.candidateId}
            materialName={feedbackModalConfig.materialName}
            onClose={() => setFeedbackModalConfig({ isOpen: false })}
          />
        )}
      </div>
    </div>
  );
}

export default App;
