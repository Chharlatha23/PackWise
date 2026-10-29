import React, { useState } from 'react';
import ecoPackagingImage from '../assets/eco_packaging_hero.png';
import {
  Cpu,
  Scale,
  Sparkles,
  BookOpen,
  FlaskConical,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  Menu,
  X,
  Lock,
  ChevronRight,
  FileCheck2,
  Mail,
  Copy,
  Check
} from 'lucide-react';
import type { NavItemKey } from './Sidebar';

interface LandingPageProps {
  onNavigate: (page: string, navItem?: NavItemKey) => void;
  isAuthenticated: boolean;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onNavigate, isAuthenticated }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const recipientEmail = 'foodpackai@gmail.com';
  const emailSubject = 'PackWise — Research Collaboration Inquiry';
  const emailBody =
    'Hello PackWise Research Team,\n\nI am interested in learning more about the PackWise evidence-driven inverse-design food packaging recommendation system.\n\nI would like to discuss a potential research collaboration.\n\nPlease let me know how we can proceed.\n\nThank you.';

  const mailtoUrl = `mailto:${recipientEmail}?subject=${encodeURIComponent(
    emailSubject
  )}&body=${encodeURIComponent(emailBody)}`;

  const handleContactClick = () => {
    // Attempt standard mailto launch
    window.location.href = mailtoUrl;

    // Fallback copy to clipboard in case default email client is not configured
    if (navigator.clipboard) {
      navigator.clipboard.writeText(recipientEmail).then(() => {
        setCopiedEmail(true);
        setTimeout(() => setCopiedEmail(false), 3000);
      });
    }
  };

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleCardClick = (navItem: NavItemKey) => {
    if (isAuthenticated) {
      onNavigate('dashboard', navItem);
    } else {
      onNavigate('login');
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFBF7] text-[#241C17] flex flex-col font-sans selection:bg-[#E2D8CC] scroll-smooth">
      {/* Sticky Professional Navbar */}
      <header className="sticky top-0 z-50 w-full bg-[#FDFBF7]/95 backdrop-blur-md border-b border-[#EBE5DC]">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 h-20 flex items-center justify-between">
          
          {/* Logo and Brand */}
          <div 
            onClick={() => {
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-[#4A3B32] flex items-center justify-center text-amber-100 font-bold text-lg shadow-xs group-hover:bg-[#3D2F27] transition-colors">
              <svg className="w-5 h-5 text-[#EFE7DE]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <div className="flex flex-col">
              <span className="text-2xl font-bold tracking-tight text-[#2B231D] leading-none">PackWise</span>
              <span className="text-[10px] uppercase font-semibold text-[#8C7E74] tracking-wider mt-1 hidden sm:inline">
                Inverse-Design Food Packaging
              </span>
            </div>
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex items-center gap-7">
            <button
              onClick={() => scrollToSection('about')}
              className="text-sm font-medium text-[#6B5E55] hover:text-[#2B231D] transition-colors cursor-pointer"
            >
              About
            </button>
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="text-sm font-medium text-[#6B5E55] hover:text-[#2B231D] transition-colors cursor-pointer"
            >
              How It Works
            </button>
            <button
              onClick={() => scrollToSection('scientific-approach')}
              className="text-sm font-medium text-[#6B5E55] hover:text-[#2B231D] transition-colors cursor-pointer"
            >
              Scientific Approach
            </button>
            <button
              onClick={() => scrollToSection('capabilities')}
              className="text-sm font-medium text-[#6B5E55] hover:text-[#2B231D] transition-colors cursor-pointer"
            >
              Capabilities
            </button>
            <button
              onClick={() => scrollToSection('contact')}
              className="text-sm font-medium text-[#6B5E55] hover:text-[#2B231D] transition-colors cursor-pointer"
            >
              Contact
            </button>

            <div className="h-5 w-px bg-[#E5DDCF] mx-1" />

            {/* Single Sign In or Dashboard CTA */}
            {isAuthenticated ? (
              <button
                onClick={() => onNavigate('dashboard')}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-[#4A3B32] text-[#FDFBF7] hover:bg-[#382C25] active:scale-[0.99] transition-all shadow-xs cursor-pointer"
              >
                Go to Dashboard
              </button>
            ) : (
              <button
                onClick={() => onNavigate('login')}
                className="px-5 py-2.5 rounded-xl text-sm font-semibold text-[#4A3B32] border border-[#DCD3C7] bg-[#F7F3ED] hover:bg-[#EFE8DD] active:scale-[0.99] transition-all cursor-pointer"
              >
                Sign in
              </button>
            )}
          </nav>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-[#4A3B32] hover:bg-[#EFE8DE] transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-b border-[#EBE5DC] bg-[#FDFBF7] px-6 py-4 space-y-3">
            <button
              onClick={() => scrollToSection('about')}
              className="block w-full text-left py-2 text-sm font-medium text-[#6B5E55] hover:text-[#2B231D]"
            >
              About
            </button>
            <button
              onClick={() => scrollToSection('how-it-works')}
              className="block w-full text-left py-2 text-sm font-medium text-[#6B5E55] hover:text-[#2B231D]"
            >
              How It Works
            </button>
            <button
              onClick={() => scrollToSection('scientific-approach')}
              className="block w-full text-left py-2 text-sm font-medium text-[#6B5E55] hover:text-[#2B231D]"
            >
              Scientific Approach
            </button>
            <button
              onClick={() => scrollToSection('capabilities')}
              className="block w-full text-left py-2 text-sm font-medium text-[#6B5E55] hover:text-[#2B231D]"
            >
              Capabilities
            </button>
            <button
              onClick={() => scrollToSection('contact')}
              className="block w-full text-left py-2 text-sm font-medium text-[#6B5E55] hover:text-[#2B231D]"
            >
              Contact
            </button>
            <div className="pt-2 border-t border-[#EAE3D8]">
              {isAuthenticated ? (
                <button
                  onClick={() => onNavigate('dashboard')}
                  className="w-full py-2.5 rounded-xl text-sm font-semibold bg-[#4A3B32] text-[#FDFBF7] text-center"
                >
                  Go to Dashboard
                </button>
              ) : (
                <button
                  onClick={() => onNavigate('login')}
                  className="w-full py-2.5 rounded-xl text-sm font-semibold text-[#4A3B32] border border-[#DCD3C7] bg-[#F7F3ED] text-center"
                >
                  Sign in
                </button>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Hero Section */}
      <section className="w-full max-w-7xl mx-auto px-6 sm:px-10 py-12 sm:py-20 lg:py-24">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          
          {/* Left Column: Headlines & CTA */}
          <div className="flex flex-col items-start space-y-8">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#EFE9DE] text-[#4A3B32] text-xs font-semibold tracking-wide border border-[#E2D8CC]">
                <ShieldCheck size={14} className="text-[#6B5E55]" />
                Evidence-Driven Inverse-Design Decision Support
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-[#241C17] leading-[1.12]">
                Design better food packaging through science.
              </h1>
              <p className="text-lg sm:text-xl text-[#6B5E55] leading-relaxed max-w-xl font-normal">
                Explore packaging materials, evaluate shelf-life requirements, and compare evidence-driven solutions for sustainable food packaging.
              </p>
            </div>

            {/* Action Buttons: ONLY Get Started as primary CTA, no duplicate sign-in */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={() => onNavigate(isAuthenticated ? 'dashboard' : 'register')}
                className="flex items-center gap-2.5 px-8 py-4 rounded-xl font-semibold text-base bg-[#4A3B32] text-[#FDFBF7] hover:bg-[#382C25] active:scale-[0.99] transition-all shadow-sm hover:shadow cursor-pointer"
              >
                <span>Get Started</span>
                <ArrowRight size={18} />
              </button>
            </div>

            {/* Feature highlights badge row */}
            <div className="pt-6 border-t border-[#EAE3D8] w-full grid grid-cols-3 gap-4 text-xs text-[#7A6D63]">
              <div>
                <span className="font-semibold block text-[#3A2F27]">Barrier Physics</span>
                M9/M10/M11 solver tiers
              </div>
              <div>
                <span className="font-semibold block text-[#3A2F27]">Eco Metrics</span>
                Biodegradable & bio-PET
              </div>
              <div>
                <span className="font-semibold block text-[#3A2F27]">Pareto Optimal</span>
                Exact-physics verification
              </div>
            </div>
          </div>

          {/* Right Column: Hero Visual Image */}
          <div className="relative flex justify-center lg:justify-end">
            <div className="relative w-full max-w-[560px] aspect-[4/3] rounded-3xl overflow-hidden shadow-md border border-[#E7DFD4] bg-[#EFEAE2]">
              <img
                src={ecoPackagingImage}
                alt="Eco-friendly kraft food packaging still life with cookies and almonds"
                className="w-full h-full object-cover rounded-3xl"
              />
              <div className="absolute inset-0 ring-1 ring-inset ring-black/5 rounded-3xl pointer-events-none" />
            </div>
          </div>

        </div>
      </section>

      {/* Section 1: About PackWise */}
      <section id="about" className="w-full border-t border-[#EBE5DC] bg-white py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 space-y-12">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#6B5E55]">
              About the Platform
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#241C17]">
              Bridging Food Science, Barrier Physics, and Sustainable Packaging
            </h2>
            <p className="text-base sm:text-lg text-[#6B5E55] leading-relaxed">
              Selecting appropriate food packaging materials is often a trial-and-error process prone to over-packaging, premature spoilage, and non-recyclable multi-material waste. PackWise transforms this challenge through computational inverse design.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-[#FDFBF7] border border-[#EAE3D8] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                <FileCheck2 size={20} />
              </div>
              <h3 className="text-lg font-bold text-[#2B231D]">The Food Packaging Challenge</h3>
              <p className="text-sm text-[#6B5E55] leading-relaxed">
                Fresh foods continuously respire and transpire moisture. Choosing an arbitrary film can lead to anaerobic fermentation, moisture condensation, or rapid lipid oxidation.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-[#FDFBF7] border border-[#EAE3D8] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                <Cpu size={20} />
              </div>
              <h3 className="text-lg font-bold text-[#2B231D]">Computational Inverse Design</h3>
              <p className="text-sm text-[#6B5E55] leading-relaxed">
                Rather than testing materials forward one-by-one, PackWise works backwards from commodity tolerance bounds ($O_2, CO_2, RH$) to identify feasible material thicknesses and permeation profiles.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-[#FDFBF7] border border-[#EAE3D8] space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                <ShieldCheck size={20} />
              </div>
              <h3 className="text-lg font-bold text-[#2B231D]">Evidence & Physical Rigor</h3>
              <p className="text-sm text-[#6B5E55] leading-relaxed">
                Every calculation is anchored in peer-reviewed postharvest literature (USDA, UC Davis, WUR). Exact-physics equations govern final feasibility—no unverified AI hallucinations.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: How It Works */}
      <section id="how-it-works" className="w-full border-t border-[#EBE5DC] bg-[#FAF7F2] py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#6B5E55]">
              Guided Methodology
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#241C17]">
              How PackWise Recommends Solutions
            </h2>
            <p className="text-sm sm:text-base text-[#6B5E55]">
              A 4-step evidence-driven workflow from agricultural parameters to verified material trade-offs.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-2xl bg-white border border-[#EAE3D8] shadow-xs space-y-4 relative">
              <div className="text-2xl font-bold text-[#4A3B32] font-mono">01</div>
              <h3 className="text-base font-bold text-[#2B231D]">Commodity Profile</h3>
              <p className="text-xs text-[#6B5E55] leading-relaxed">
                Define the food commodity, variety, ripeness stage, and target shelf life (e.g., strawberries at 14 days).
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white border border-[#EAE3D8] shadow-xs space-y-4 relative">
              <div className="text-2xl font-bold text-[#4A3B32] font-mono">02</div>
              <h3 className="text-base font-bold text-[#2B231D]">Storage & Logistics</h3>
              <p className="text-xs text-[#6B5E55] leading-relaxed">
                Specify storage temperature, ambient relative humidity, transport duration, and package dimensions.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white border border-[#EAE3D8] shadow-xs space-y-4 relative">
              <div className="text-2xl font-bold text-[#4A3B32] font-mono">03</div>
              <h3 className="text-base font-bold text-[#2B231D]">Scientific Engine</h3>
              <p className="text-xs text-[#6B5E55] leading-relaxed">
                Evaluate transpiration and respiration kinetics against barrier permeabilities ($OTR, CO_2TR, WVTR$).
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white border border-[#EAE3D8] shadow-xs space-y-4 relative">
              <div className="text-2xl font-bold text-[#4A3B32] font-mono">04</div>
              <h3 className="text-base font-bold text-[#2B231D]">Pareto Trade-offs</h3>
              <p className="text-xs text-[#6B5E55] leading-relaxed">
                Review verified non-dominated candidates balancing material thickness, gas alignment, and shelf-life margin.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: Scientific Approach */}
      <section id="scientific-approach" className="w-full border-t border-[#EBE5DC] bg-white py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 space-y-12">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#6B5E55]">
              Rigorous Mathematical Hierarchy
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#241C17]">
              Inverse-Design Solver Tiers
            </h2>
            <p className="text-base text-[#6B5E55] leading-relaxed">
              PackWise offers three distinct inverse-design solver strategies. To ensure scientific integrity, exact physics remains the sole authoritative gatekeeper across all tiers.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* M9 Tier */}
            <div className="p-6 rounded-2xl bg-[#FDFBF7] border border-[#EAE3D8] space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-[#EAE3D8] text-[#4A3B32]">
                  Tier M9
                </span>
                <span className="text-xs font-semibold text-[#8C7E74]">Lattice Enumeration</span>
              </div>
              <h3 className="text-base font-bold text-[#2B231D]">Deterministic Baseline</h3>
              <p className="text-xs text-[#6B5E55] leading-relaxed">
                Exhaustively evaluates candidate material thickness permutations across the discrete parameter lattice. Pure numerical physics without machine learning.
              </p>
              <div className="pt-3 border-t border-[#EAE3D8] text-[11px] text-[#7A6D63] space-y-1">
                <div>• Pure physics calculations</div>
                <div>• Discrete lattice evaluation</div>
                <div>• Interval preservation preserved</div>
              </div>
            </div>

            {/* M10 Tier */}
            <div className="p-6 rounded-2xl bg-[#FDFBF7] border border-[#EAE3D8] space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-[#E4DBCF] text-[#4A3B32]">
                  Tier M10
                </span>
                <span className="text-xs font-semibold text-[#8C7E74]">Heuristic Prioritized</span>
              </div>
              <h3 className="text-base font-bold text-[#2B231D]">Adaptive Heuristic Search</h3>
              <p className="text-xs text-[#6B5E55] leading-relaxed">
                Applies deterministic postharvest packaging heuristics to prioritize candidate exploration sequence. Contains no learned ML models.
              </p>
              <div className="pt-3 border-t border-[#EAE3D8] text-[11px] text-[#7A6D63] space-y-1">
                <div>• Deterministic search ordering</div>
                <div>• Domain-informed pruning</div>
                <div>• No unverified ML approximations</div>
              </div>
            </div>

            {/* M11 Tier */}
            <div className="p-6 rounded-2xl bg-[#FDFBF7] border border-[#EAE3D8] space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-[#DDD2C4] text-[#4A3B32]">
                  Tier M11
                </span>
                <span className="text-xs font-semibold text-[#4A3B32]">Exact-Physics Authoritative</span>
              </div>
              <h3 className="text-base font-bold text-[#2B231D]">Surrogate-Assisted Search</h3>
              <p className="text-xs text-[#6B5E55] leading-relaxed">
                Employs surrogate models strictly for candidate exploration ordering with out-of-distribution (OOD) checks. <strong>Exact physics equations are sovereign</strong>—only verified candidates enter the Pareto front.
              </p>
              <div className="pt-3 border-t border-[#EAE3D8] text-[11px] text-[#7A6D63] space-y-1">
                <div>• Surrogate guides exploration order</div>
                <div>• Mandatory exact-physics gateway</div>
                <div>• Zero automated model retraining</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 4: Key Capabilities */}
      <section id="capabilities" className="w-full border-t border-[#EBE5DC] bg-[#FAF7F2] py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 space-y-12">
          <div className="text-center max-w-2xl mx-auto space-y-3">
            <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#6B5E55]">
              System Features
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#241C17]">
              Comprehensive Scientific Capabilities
            </h2>
            <p className="text-sm sm:text-base text-[#6B5E55]">
              Explore the dedicated modules built into the PackWise decision-support workspace.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {/* Card 1: Recommendation Engine */}
            <div 
              onClick={() => handleCardClick('recommend')}
              className="p-6 rounded-2xl bg-white border border-[#EAE3D8] hover:border-[#CFC2B2] shadow-xs hover:shadow transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                  <Cpu size={20} />
                </div>
                <h3 className="text-base font-bold text-[#2B231D] group-hover:text-[#4A3B32]">Recommendation Engine</h3>
                <p className="text-xs text-[#6B5E55] leading-relaxed">
                  Four-step guided inverse-design wizard with commodity presets (Strawberry, Apple, Salmon) and custom property inference.
                </p>
              </div>
              <div className="pt-4 flex items-center text-xs font-semibold text-[#4A3B32] gap-1 group-hover:translate-x-1 transition-transform">
                <span>Launch Engine</span>
                <ChevronRight size={14} />
              </div>
            </div>

            {/* Card 2: Package Comparison */}
            <div 
              onClick={() => handleCardClick('compare')}
              className="p-6 rounded-2xl bg-white border border-[#EAE3D8] hover:border-[#CFC2B2] shadow-xs hover:shadow transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                  <Scale size={20} />
                </div>
                <h3 className="text-base font-bold text-[#2B231D] group-hover:text-[#4A3B32]">Package Comparison</h3>
                <p className="text-xs text-[#6B5E55] leading-relaxed">
                  Side-by-side barrier property matrix comparing OTR, CO₂TR, WVTR, and nominal film thicknesses across canonical materials.
                </p>
              </div>
              <div className="pt-4 flex items-center text-xs font-semibold text-[#4A3B32] gap-1 group-hover:translate-x-1 transition-transform">
                <span>Compare Materials</span>
                <ChevronRight size={14} />
              </div>
            </div>

            {/* Card 3: What-If Analysis */}
            <div 
              onClick={() => handleCardClick('whatif')}
              className="p-6 rounded-2xl bg-white border border-[#EAE3D8] hover:border-[#CFC2B2] shadow-xs hover:shadow transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                  <Sparkles size={20} />
                </div>
                <h3 className="text-base font-bold text-[#2B231D] group-hover:text-[#4A3B32]">What-If Analysis</h3>
                <p className="text-xs text-[#6B5E55] leading-relaxed">
                  Evaluate logistics stress scenarios: perturb storage temperatures, relative humidity, and transit durations against live physics.
                </p>
              </div>
              <div className="pt-4 flex items-center text-xs font-semibold text-[#4A3B32] gap-1 group-hover:translate-x-1 transition-transform">
                <span>Test Scenarios</span>
                <ChevronRight size={14} />
              </div>
            </div>

            {/* Card 4: Evidence Library */}
            <div 
              onClick={() => handleCardClick('evidence')}
              className="p-6 rounded-2xl bg-white border border-[#EAE3D8] hover:border-[#CFC2B2] shadow-xs hover:shadow transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                  <BookOpen size={20} />
                </div>
                <h3 className="text-base font-bold text-[#2B231D] group-hover:text-[#4A3B32]">Evidence Library</h3>
                <p className="text-xs text-[#6B5E55] leading-relaxed">
                  Searchable literature repository linking canonical datasets (USDA, UC Davis, WUR, ComBase) with traceable food observations.
                </p>
              </div>
              <div className="pt-4 flex items-center text-xs font-semibold text-[#4A3B32] gap-1 group-hover:translate-x-1 transition-transform">
                <span>View Evidence</span>
                <ChevronRight size={14} />
              </div>
            </div>

            {/* Card 5: Trial Feedback & Audit */}
            <div 
              onClick={() => handleCardClick('feedback')}
              className="p-6 rounded-2xl bg-white border border-[#EAE3D8] hover:border-[#CFC2B2] shadow-xs hover:shadow transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-[#EFE9DF] text-[#4A3B32] flex items-center justify-center font-bold">
                  <FlaskConical size={20} />
                </div>
                <h3 className="text-base font-bold text-[#2B231D] group-hover:text-[#4A3B32]">Trial Feedback & Audit</h3>
                <p className="text-xs text-[#6B5E55] leading-relaxed">
                  Record physical packaging trial observations to track prediction residuals. Generates structured candidates for human expert review.
                </p>
              </div>
              <div className="pt-4 flex items-center text-xs font-semibold text-[#4A3B32] gap-1 group-hover:translate-x-1 transition-transform">
                <span>Inspect Feedback</span>
                <ChevronRight size={14} />
              </div>
            </div>

            {/* Card 6: Authentication & Security */}
            <div 
              onClick={() => onNavigate('login')}
              className="p-6 rounded-2xl bg-[#EFE9DF]/50 border border-[#E2D8CC] shadow-xs flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-xl bg-[#4A3B32] text-[#FDFBF7] flex items-center justify-center font-bold">
                  <Lock size={20} />
                </div>
                <h3 className="text-base font-bold text-[#2B231D]">Enterprise Access Control</h3>
                <p className="text-xs text-[#6B5E55] leading-relaxed">
                  Secure Google OAuth 2.0 authorization code flow with signed JWT tokens and session expiration handling.
                </p>
              </div>
              <div className="pt-4 flex items-center text-xs font-semibold text-[#4A3B32] gap-1">
                <span>{isAuthenticated ? 'Authenticated Active' : 'Sign in to access'}</span>
                <CheckCircle2 size={14} className="text-emerald-700" />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Section 5: Contact & Inquiries */}
      <section id="contact" className="w-full border-t border-[#EBE5DC] bg-white py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-6 sm:px-10">
          <div className="bg-[#FAF7F2] border border-[#EAE3D8] rounded-3xl p-8 sm:p-12 flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
            <div className="space-y-2 max-w-xl">
              <h2 className="text-2xl sm:text-3xl font-bold text-[#241C17]">Interested in Research Collaboration?</h2>
              <p className="text-sm text-[#6B5E55] leading-relaxed">
                PackWise was developed as an evidence-driven inverse-design decision support system. For academic inquiries, data integrations, or technical reviews, reach out to our project team.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
              <a
                href={mailtoUrl}
                onClick={handleContactClick}
                className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl font-semibold text-sm bg-[#4A3B32] text-[#FDFBF7] hover:bg-[#382C25] text-center transition-colors shadow-xs cursor-pointer"
                title="Send inquiry to foodpackai@gmail.com"
              >
                <Mail size={16} />
                <span>Contact Research Team</span>
              </a>
              <button
                onClick={() => onNavigate(isAuthenticated ? 'dashboard' : 'login')}
                className="px-6 py-3.5 rounded-xl font-semibold text-sm text-[#4A3B32] border border-[#DCD3C7] bg-[#FDFBF7] hover:bg-[#EFE8DD] text-center transition-colors cursor-pointer"
              >
                Launch Workspace
              </button>
            </div>
          </div>

          {/* Quick email display and copy notice */}
          <div className="mt-4 flex flex-wrap items-center justify-between text-xs text-[#7A6D63] px-2 gap-2">
            <div className="flex items-center gap-2">
              <span className="font-medium text-[#4A3B32]">Direct Email:</span>
              <a
                href={`mailto:${recipientEmail}`}
                className="font-mono text-[#382C25] underline decoration-[#CFC2B2] hover:decoration-[#382C25]"
              >
                {recipientEmail}
              </a>
            </div>
            <button
              onClick={() => {
                if (navigator.clipboard) {
                  navigator.clipboard.writeText(recipientEmail).then(() => {
                    setCopiedEmail(true);
                    setTimeout(() => setCopiedEmail(false), 3000);
                  });
                }
              }}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[#E2D8CC] bg-white text-[#4A3B32] hover:bg-[#EFE9DF] transition-colors cursor-pointer"
            >
              {copiedEmail ? (
                <>
                  <Check size={13} className="text-emerald-700" />
                  <span className="text-emerald-800 font-semibold">Copied to clipboard</span>
                </>
              ) : (
                <>
                  <Copy size={13} />
                  <span>Copy email address</span>
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full border-t border-[#EBE5DC] bg-[#FAF7F2] py-12 text-sm text-[#8C7E74]">
        <div className="max-w-7xl mx-auto px-6 sm:px-10 flex flex-col sm:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#4A3B32] flex items-center justify-center text-amber-100 font-bold text-xs">
              PW
            </div>
            <span className="font-bold text-[#2B231D]">PackWise</span>
            <span className="text-xs text-[#8C7E74]">© 2026 Evidence-Driven Inverse-Design Food Packaging</span>
          </div>

          <div className="flex items-center gap-6 text-xs text-[#6B5E55]">
            <button onClick={() => scrollToSection('about')} className="hover:text-[#2B231D]">About</button>
            <button onClick={() => scrollToSection('how-it-works')} className="hover:text-[#2B231D]">How It Works</button>
            <button onClick={() => scrollToSection('scientific-approach')} className="hover:text-[#2B231D]">Scientific Approach</button>
            <button onClick={() => scrollToSection('capabilities')} className="hover:text-[#2B231D]">Capabilities</button>
            <button onClick={() => scrollToSection('contact')} className="hover:text-[#2B231D]">Contact</button>
          </div>
        </div>
      </footer>
    </div>
  );
};
