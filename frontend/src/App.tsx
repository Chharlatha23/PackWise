import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { Sidebar, type NavItemKey } from './components/Sidebar';
import { OverviewPage } from './components/OverviewPage';
import { PackagingRequestForm } from './components/PackagingRequestForm';
import { RecommendationResults } from './components/RecommendationResults';
import { PackageComparison } from './components/PackageComparison';
import { WhatIfAnalysis } from './components/WhatIfAnalysis';
import { EvidenceLibrary } from './components/EvidenceLibrary';
import { FeedbackDashboard } from './components/FeedbackDashboard';
import { ModelPerformance } from './components/ModelPerformance';
import { SettingsPage } from './components/SettingsPage';
import { ExplainabilityModal } from './components/ExplainabilityModal';
import { FeedbackModal } from './components/FeedbackModal';
import { fetchRecommendation, checkHealth } from './api/client';
import { Menu, LogOut, ArrowLeft } from 'lucide-react';
import type { PackagingRequest, RecommendationResponse, CandidateExplainabilityReport } from './types/api';

import { RegisterPage } from './components/RegisterPage';

type AppPage = 'landing' | 'login' | 'register' | 'dashboard';

function AppContent() {
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  
  // Page navigation state: 'landing', 'login', 'register', or 'dashboard'
  const [currentPage, setCurrentPage] = useState<AppPage>(() => {
    const path = window.location.pathname;
    const search = window.location.search;
    if (path === '/register') {
      return 'register';
    }
    if (path === '/login' || search.includes('token=') || search.includes('code=') || search.includes('error=')) {
      return 'login';
    }
    if (path === '/dashboard') {
      return 'dashboard';
    }
    return 'landing';
  });

  // Active workspace navigation item inside the dashboard
  const [activeNavItem, setActiveNavItem] = useState<NavItemKey>('overview');

  // Sidebar responsive collapse state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Recommendation engine state
  const [results, setResults] = useState<RecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isApiConnected, setIsApiConnected] = useState<boolean | null>(null);

  // Modals state
  const [activeExplainReport, setActiveExplainReport] = useState<CandidateExplainabilityReport | null>(null);
  const [feedbackModalConfig, setFeedbackModalConfig] = useState<{
    isOpen: boolean;
    candidateId?: string;
    materialName?: string;
  }>({ isOpen: false });

  // Handle URL history popstate
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      if (path === '/register') {
        setCurrentPage('register');
      } else if (path === '/login') {
        setCurrentPage('login');
      } else if (path === '/dashboard') {
        setCurrentPage('dashboard');
      } else {
        setCurrentPage('landing');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = (page: string, navItem?: NavItemKey) => {
    let targetPage: AppPage = 'landing';
    let urlPath = '/';
    if (page === 'register') {
      targetPage = 'register';
      urlPath = '/register';
    } else if (page === 'login') {
      targetPage = 'login';
      urlPath = '/login';
    } else if (page === 'dashboard') {
      targetPage = 'dashboard';
      urlPath = '/dashboard';
      if (navItem) {
        setActiveNavItem(navItem);
      }
    } else {
      targetPage = 'landing';
      urlPath = '/';
    }

    // Route Protection: Unauthenticated users attempting to access dashboard are sent to login
    if (targetPage === 'dashboard' && !isAuthenticated && !authLoading) {
      targetPage = 'login';
      urlPath = '/login';
    }

    setCurrentPage(targetPage);
    window.history.pushState({}, '', urlPath);
    window.scrollTo(0, 0);
  };

  // Verify backend health
  useEffect(() => {
    const verifyApi = async () => {
      const isConnected = await checkHealth();
      setIsApiConnected(isConnected);
    };
    verifyApi();
    const interval = setInterval(verifyApi, 30000);
    return () => clearInterval(interval);
  }, []);

  // Protected route check when current page is dashboard
  useEffect(() => {
    if (!authLoading && currentPage === 'dashboard' && !isAuthenticated) {
      setCurrentPage('login');
      window.history.replaceState({}, '', '/login');
    }
  }, [authLoading, currentPage, isAuthenticated]);

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

  // Route: Landing Page
  if (currentPage === 'landing') {
    return <LandingPage onNavigate={navigateTo} isAuthenticated={isAuthenticated} />;
  }

  // Route: Login Page
  if (currentPage === 'login') {
    return <LoginPage onNavigate={navigateTo} />;
  }

  // Route: Registration Page
  if (currentPage === 'register') {
    return <RegisterPage onNavigate={navigateTo} />;
  }

  // Route: Dashboard (Multi-Page Protected SaaS Shell)
  return (
    <div className="min-h-screen bg-slate-50 flex font-sans text-slate-900 selection:bg-blue-100">
      
      {/* Persistent Left Sidebar */}
      <Sidebar
        activeItem={activeNavItem}
        onSelect={(item) => {
          setActiveNavItem(item);
          // If returning to recommendation engine, keep previous results or clear if needed
        }}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div
        className={`flex-1 flex flex-col min-w-0 transition-all duration-200 ${
          sidebarCollapsed ? 'lg:pl-18' : 'lg:pl-68'
        }`}
      >
        {/* Top Header Bar */}
        <header className="h-16 px-4 sm:px-8 bg-white border-b border-slate-200 flex items-center justify-between sticky top-0 z-30 shadow-xs">
          {/* Mobile Menu & Active Page Label */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
              title="Open Navigation"
            >
              <Menu size={20} />
            </button>
            <div className="hidden sm:flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Workspace</span>
              <span className="text-slate-300">/</span>
              <span className="text-sm font-bold text-slate-800 capitalize">
                {activeNavItem === 'recommend'
                  ? 'Recommendation Engine'
                  : activeNavItem === 'compare'
                  ? 'Package Comparison'
                  : activeNavItem === 'whatif'
                  ? 'What-If Analysis'
                  : activeNavItem === 'evidence'
                  ? 'Evidence Library'
                  : activeNavItem === 'feedback'
                  ? 'Trial Feedback & Audit'
                  : activeNavItem === 'performance'
                  ? 'Model Performance'
                  : activeNavItem === 'settings'
                  ? 'Settings'
                  : 'Overview'}
              </span>
            </div>
          </div>

          {/* Right Header Controls: API Indicator, User Profile & Logout */}
          <div className="flex items-center gap-4">
            {/* Subtle API Status Badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200 text-[11px] font-medium text-slate-600">
              <span
                className={`w-2 h-2 rounded-full ${
                  isApiConnected === null
                    ? 'bg-slate-300'
                    : isApiConnected
                    ? 'bg-emerald-500'
                    : 'bg-red-500'
                }`}
              />
              <span className="hidden md:inline">
                {isApiConnected === null ? 'Connecting...' : isApiConnected ? 'Backend Connected' : 'Backend Offline'}
              </span>
            </div>

            {/* User Profile & Sign Out */}
            {user && (
              <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt={user.name || user.email}
                    className="w-8 h-8 rounded-full border border-slate-300 shadow-xs object-cover"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-blue-700 text-white flex items-center justify-center font-bold text-xs uppercase shadow-xs">
                    {(user.name || user.email || 'U').charAt(0)}
                  </div>
                )}
                <div className="hidden md:block text-left">
                  <div className="text-xs font-bold text-slate-900 truncate max-w-[130px]">
                    {user.name || user.email}
                  </div>
                  <div className="text-[10px] text-slate-400 truncate max-w-[130px]">
                    {user.email}
                  </div>
                </div>
                <button
                  onClick={() => {
                    logout();
                    navigateTo('landing');
                  }}
                  className="p-1.5 rounded-lg text-slate-500 hover:text-red-700 hover:bg-red-50 transition-colors"
                  title="Sign out of PackWise"
                >
                  <LogOut size={16} />
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Dynamic Page Workspace Body */}
        <main className="flex-1 p-4 sm:p-8 overflow-y-auto">
          {/* Overview Dashboard */}
          {activeNavItem === 'overview' && (
            <OverviewPage
              onNavigate={(item) => setActiveNavItem(item)}
              userName={user?.name}
              userEmail={user?.email}
            />
          )}

          {/* Recommendation Engine Workflow */}
          {activeNavItem === 'recommend' && (
            <div className="max-w-6xl mx-auto space-y-8">
              {results ? (
                <div className="space-y-6">
                  <button
                    onClick={() => setResults(null)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-200 bg-white text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors shadow-xs cursor-pointer"
                  >
                    <ArrowLeft size={15} />
                    Back to Request Form
                  </button>
                  <RecommendationResults
                    results={results}
                    onExplainCandidate={(rep) => setActiveExplainReport(rep)}
                    onRecordFeedback={(candId, matName) => handleOpenFeedback(candId, matName)}
                  />
                </div>
              ) : (
                <>
                  <PackagingRequestForm onSubmit={handleRequestSubmit} isLoading={isLoading} />
                  {error && (
                    <div className="bg-red-50 border border-red-200 p-4 rounded-xl shadow-xs">
                      <h3 className="font-semibold text-red-900 text-sm">Recommendation Pipeline Error</h3>
                      <p className="text-red-800 text-xs mt-1">{error}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Package Comparison */}
          {activeNavItem === 'compare' && <PackageComparison />}

          {/* What-If Analysis */}
          {activeNavItem === 'whatif' && <WhatIfAnalysis />}

          {/* Evidence Library */}
          {activeNavItem === 'evidence' && <EvidenceLibrary />}

          {/* Trial Feedback & Audit */}
          {activeNavItem === 'feedback' && (
            <div className="max-w-6xl mx-auto">
              <FeedbackDashboard onNewFeedbackClick={() => handleOpenFeedback()} />
            </div>
          )}

          {/* Model Performance */}
          {activeNavItem === 'performance' && <ModelPerformance />}

          {/* Settings */}
          {activeNavItem === 'settings' && <SettingsPage />}
        </main>
      </div>

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
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
