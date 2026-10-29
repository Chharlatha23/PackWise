import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  fetchGoogleAuthUrl,
  exchangeGoogleCodeForToken,
  loginWithEmailPassword,
  forgotPasswordApi,
  resetPasswordApi,
  API_BASE_URL
} from '../api/client';
import { Mail, Lock, Eye, EyeOff, ArrowLeft, KeyRound, CheckCircle2 } from 'lucide-react';

interface LoginPageProps {
  onNavigate: (page: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate }) => {
  const { loginWithToken, isAuthenticated } = useAuth();
  
  // Traditional login states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  // Forgot / Reset password sub-states
  const [viewMode, setViewMode] = useState<'login' | 'forgot' | 'reset'>('login');
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSuccess, setForgotSuccess] = useState<string | null>(null);
  
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Check URL query parameters for token (successful OAuth callback), code, reset_token, or error
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tokenParam = urlParams.get('token');
    const codeParam = urlParams.get('code');
    const stateParam = urlParams.get('state');
    const errorParam = urlParams.get('error');
    const resetParam = urlParams.get('reset_token');

    if (errorParam) {
      setErrorMessage(decodeURIComponent(errorParam));
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (resetParam) {
      setResetToken(resetParam);
      setViewMode('reset');
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (tokenParam) {
      setIsSubmitting(true);
      loginWithToken(tokenParam)
        .then(() => {
          window.history.replaceState({}, document.title, window.location.pathname);
          onNavigate('dashboard');
        })
        .catch((err) => {
          setErrorMessage(err.message || 'Authentication failed. Please try again.');
          setIsSubmitting(false);
        });
    } else if (codeParam) {
      setIsSubmitting(true);
      exchangeGoogleCodeForToken(codeParam, stateParam || undefined)
        .then((res) => {
          return loginWithToken(res.access_token);
        })
        .then(() => {
          window.history.replaceState({}, document.title, window.location.pathname);
          onNavigate('dashboard');
        })
        .catch((err) => {
          setErrorMessage(err.message || 'Failed to exchange authorization code.');
          setIsSubmitting(false);
          window.history.replaceState({}, document.title, window.location.pathname);
        });
    }
  }, [loginWithToken, onNavigate]);

  // If already authenticated, redirect to redirect target or dashboard
  useEffect(() => {
    if (isAuthenticated && !window.location.search.includes('token=')) {
      const urlParams = new URLSearchParams(window.location.search);
      const redirectTarget = urlParams.get('redirect');
      if (redirectTarget === 'dashboard' || redirectTarget === '/dashboard') {
        onNavigate('dashboard');
      } else {
        onNavigate('dashboard');
      }
    }
  }, [isAuthenticated, onNavigate]);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email.trim()) {
      setErrorMessage('Please enter your email address.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await loginWithEmailPassword(email.trim(), password);
      await loginWithToken(res.access_token);
      
      const urlParams = new URLSearchParams(window.location.search);
      const redirectTarget = urlParams.get('redirect');
      if (redirectTarget === 'dashboard' || redirectTarget === '/dashboard') {
        onNavigate('dashboard');
      } else {
        onNavigate('dashboard');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setForgotSuccess(null);

    if (!forgotEmail.trim()) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await forgotPasswordApi(forgotEmail.trim());
      setForgotSuccess(res.message);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to process password reset request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setResetSuccess(null);

    if (!resetToken.trim()) {
      setErrorMessage('Password reset token is missing or invalid.');
      return;
    }
    if (newPassword.length < 8) {
      setErrorMessage('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await resetPasswordApi(resetToken.trim(), newPassword);
      setResetSuccess(res.message);
      setTimeout(() => {
        setViewMode('login');
        setResetSuccess(null);
      }, 2500);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to reset password.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSignIn = async () => {
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const { authorization_url } = await fetchGoogleAuthUrl();
      if (authorization_url) {
        window.location.href = authorization_url;
      } else {
        window.location.href = `${API_BASE_URL}/api/v1/auth/google/redirect`;
      }
    } catch (err: any) {
      try {
        window.location.href = `${API_BASE_URL}/api/v1/auth/google/redirect`;
      } catch (fallbackErr) {
        setErrorMessage(err.message || 'Unable to connect to Google OAuth service.');
        setIsSubmitting(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-[#1E293B] flex flex-col font-sans selection:bg-[#E2D8CC]">
      {/* Top Header */}
      <header className="w-full max-w-7xl mx-auto px-6 sm:px-10 py-6 flex items-center justify-between border-b border-[#EBE5DC]">
        <div 
          onClick={() => onNavigate('landing')}
          className="flex items-center gap-2.5 cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-xl bg-[#4A3B32] flex items-center justify-center text-amber-100 font-bold text-lg shadow-xs group-hover:bg-[#3D2F27] transition-colors">
            <svg className="w-5 h-5 text-[#EFE7DE]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
          <span className="text-2xl font-bold tracking-tight text-[#2B231D]">PackWise</span>
        </div>

        <button
          onClick={() => onNavigate('landing')}
          className="text-sm font-medium text-[#6B5E55] hover:text-[#2B231D] transition-colors flex items-center gap-1.5 cursor-pointer"
        >
          <ArrowLeft size={16} />
          Back to Home
        </button>
      </header>

      {/* Main Authentication Card */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 py-12">
        <div className="w-full max-w-md bg-white border border-[#E7DFD4] rounded-2xl shadow-xs p-8 sm:p-10 space-y-6">
          
          {/* Header */}
          <div className="text-center space-y-1.5">
            <div className="inline-flex w-12 h-12 rounded-2xl bg-[#F7F3ED] border border-[#EAE2D7] items-center justify-center text-[#4A3B32] mb-1 shadow-inner">
              <KeyRound size={22} />
            </div>
            <h1 className="text-2xl font-bold text-[#241C17] tracking-tight">
              {viewMode === 'forgot'
                ? 'Reset Password'
                : viewMode === 'reset'
                ? 'Create New Password'
                : 'Sign in to PackWise'}
            </h1>
            <p className="text-xs text-[#7A6D63]">
              {viewMode === 'forgot'
                ? 'Enter your email to receive a secure recovery link'
                : viewMode === 'reset'
                ? 'Choose a strong password with at least 8 characters'
                : 'Access the evidence-driven packaging recommendation workspace'}
            </p>
          </div>

          {/* Feedback & Error Messages */}
          {errorMessage && (
            <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2.5">
              <div className="flex-1">
                <span className="font-semibold block">Authentication Notice</span>
                <span className="mt-0.5 text-red-700 leading-relaxed block">{errorMessage}</span>
              </div>
            </div>
          )}

          {forgotSuccess && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-start gap-2.5">
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">
                {forgotSuccess}
              </div>
            </div>
          )}

          {resetSuccess && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-start gap-2.5">
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">
                {resetSuccess} Redirecting to login...
              </div>
            </div>
          )}

          {/* VIEW: LOGIN FORM */}
          {viewMode === 'login' && (
            <div className="space-y-6">
              <form onSubmit={handleEmailLogin} className="space-y-4">
                {/* Email Field */}
                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-[#4A3B32]">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@organization.com"
                      className="w-full pl-10 pr-4 py-2.5 text-sm border border-[#D5CABE] rounded-xl bg-white shadow-xs focus:ring-2 focus:ring-[#4A3B32]/10 focus:border-[#4A3B32] outline-none transition-all"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-semibold text-[#4A3B32]">
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setErrorMessage(null);
                        setForgotEmail(email);
                        setViewMode('forgot');
                      }}
                      className="text-xs text-[#6B5E55] hover:text-[#241C17] hover:underline cursor-pointer"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-10 py-2.5 text-sm border border-[#D5CABE] rounded-xl bg-white shadow-xs focus:ring-2 focus:ring-[#4A3B32]/10 focus:border-[#4A3B32] outline-none transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-[#4A3B32] text-[#FDFBF7] hover:bg-[#382C25] active:scale-[0.99] transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? 'Authenticating...' : 'Sign In'}
                </button>
              </form>

              {/* Divider */}
              <div className="relative flex items-center">
                <div className="flex-grow border-t border-[#EAE2D7]"></div>
                <span className="flex-shrink mx-3 text-[11px] uppercase tracking-wider text-[#9E9084]">Or Continue With</span>
                <div className="flex-grow border-t border-[#EAE2D7]"></div>
              </div>

              {/* Google OAuth Button */}
              <button
                onClick={handleGoogleSignIn}
                disabled={isSubmitting}
                className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl border border-[#D5CABE] bg-white hover:bg-[#FAF8F5] active:bg-[#F2ECE3] text-[#2C241E] font-medium text-sm transition-all shadow-xs hover:shadow disabled:opacity-50 cursor-pointer"
              >
                {/* Google G Logo SVG */}
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
                </svg>
                <span>Continue with Google</span>
              </button>

              {/* Link to Register */}
              <div className="pt-2 text-center text-xs text-[#7A6D63]">
                <span>Don't have an account? </span>
                <button
                  type="button"
                  onClick={() => onNavigate('register')}
                  className="font-semibold text-[#4A3B32] hover:underline cursor-pointer"
                >
                  Sign up
                </button>
              </div>
            </div>
          )}

          {/* VIEW: FORGOT PASSWORD */}
          {viewMode === 'forgot' && (
            <div className="space-y-5">
              <form onSubmit={handleForgotPassword} className="space-y-4">
                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-[#4A3B32]">
                    Registered Email Address
                  </label>
                  <div className="relative">
                    <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="email"
                      required
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      placeholder="name@organization.com"
                      className="w-full pl-10 pr-4 py-2.5 text-sm border border-[#D5CABE] rounded-xl bg-white shadow-xs focus:ring-2 focus:ring-[#4A3B32]/10 focus:border-[#4A3B32] outline-none transition-all"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-[#4A3B32] text-[#FDFBF7] hover:bg-[#382C25] active:scale-[0.99] transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? 'Sending Link...' : 'Send Recovery Link'}
                </button>
              </form>

              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    setViewMode('login');
                  }}
                  className="text-xs font-medium text-[#6B5E55] hover:text-[#241C17] hover:underline cursor-pointer"
                >
                  Return to sign in
                </button>
              </div>
            </div>
          )}

          {/* VIEW: RESET PASSWORD FORM */}
          {viewMode === 'reset' && (
            <div className="space-y-5">
              <form onSubmit={handleResetPassword} className="space-y-4">
                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-[#4A3B32]">
                    New Password
                  </label>
                  <div className="relative">
                    <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type={showResetPassword ? 'text' : 'password'}
                      required
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Minimum 8 characters"
                      className="w-full pl-10 pr-10 py-2.5 text-sm border border-[#D5CABE] rounded-xl bg-white shadow-xs focus:ring-2 focus:ring-[#4A3B32]/10 focus:border-[#4A3B32] outline-none transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowResetPassword(!showResetPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
                    >
                      {showResetPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="block text-xs font-semibold text-[#4A3B32]">
                    Confirm New Password
                  </label>
                  <div className="relative">
                    <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type={showResetPassword ? 'text' : 'password'}
                      required
                      value={confirmNewPassword}
                      onChange={(e) => setConfirmNewPassword(e.target.value)}
                      placeholder="Re-enter password"
                      className="w-full pl-10 pr-4 py-2.5 text-sm border border-[#D5CABE] rounded-xl bg-white shadow-xs focus:ring-2 focus:ring-[#4A3B32]/10 focus:border-[#4A3B32] outline-none transition-all"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 px-4 rounded-xl font-semibold text-sm bg-[#4A3B32] text-[#FDFBF7] hover:bg-[#382C25] active:scale-[0.99] transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                >
                  {isSubmitting ? 'Updating...' : 'Set New Password'}
                </button>
              </form>

              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    setViewMode('login');
                  }}
                  className="text-xs font-medium text-[#6B5E55] hover:text-[#241C17] hover:underline cursor-pointer"
                >
                  Cancel and sign in
                </button>
              </div>
            </div>
          )}

        </div>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-[#EBE5DC] py-6 text-center text-xs text-[#8C7E74]">
        © 2026 PackWise — Evidence-Driven Inverse-Design Food Packaging
      </footer>
    </div>
  );
};
