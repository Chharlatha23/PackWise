import React from 'react';
import {
  LayoutDashboard,
  Cpu,
  Scale,
  SlidersHorizontal,
  BookOpen,
  FlaskConical,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  X
} from 'lucide-react';

export type NavItemKey =
  | 'overview'
  | 'recommend'
  | 'compare'
  | 'whatif'
  | 'evidence'
  | 'feedback'
  | 'performance'
  | 'settings';

interface SidebarProps {
  activeItem: NavItemKey;
  onSelect: (item: NavItemKey) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

interface NavItemConfig {
  key: NavItemKey;
  label: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  badge?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeItem,
  onSelect,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}) => {
  const workspaceItems: NavItemConfig[] = [
    { key: 'overview', label: 'Overview', icon: LayoutDashboard },
    { key: 'recommend', label: 'Recommendation Engine', icon: Cpu },
    { key: 'compare', label: 'Package Comparison', icon: Scale },
    { key: 'whatif', label: 'What-If Analysis', icon: SlidersHorizontal },
  ];

  const validationItems: NavItemConfig[] = [
    { key: 'evidence', label: 'Evidence Library', icon: BookOpen },
    { key: 'feedback', label: 'Trial Feedback & Audit', icon: FlaskConical },
    { key: 'performance', label: 'Model Performance', icon: Activity },
  ];

  const systemItems: NavItemConfig[] = [
    { key: 'settings', label: 'Settings', icon: Settings },
  ];

  const renderNavGroup = (title: string, items: NavItemConfig[]) => (
    <div className="mb-6">
      {!collapsed && (
        <div className="px-3 mb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          {title}
        </div>
      )}
      <ul className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeItem === item.key;
          return (
            <li key={item.key}>
              <button
                onClick={() => {
                  onSelect(item.key);
                  onCloseMobile();
                }}
                title={collapsed ? item.label : undefined}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 shadow-xs border border-blue-200/60 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80 border border-transparent'
                } ${collapsed ? 'justify-center px-2' : ''}`}
              >
                <Icon
                  size={18}
                  className={`shrink-0 ${
                    isActive ? 'text-blue-600' : 'text-slate-500'
                  }`}
                />
                {!collapsed && (
                  <span className="truncate text-left flex-1">{item.label}</span>
                )}
                {!collapsed && item.badge && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-semibold">
                    {item.badge}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-slate-900/40 z-40 lg:hidden backdrop-blur-xs transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 bg-white border-r border-slate-200 flex flex-col transition-all duration-200 ${
          collapsed ? 'w-18' : 'w-68'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shrink-0 shadow-xs">
              <ShieldCheck size={18} />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <div className="text-base font-bold text-slate-900 tracking-tight leading-tight">
                  PackWise
                </div>
                <div className="text-[10px] text-slate-400 font-medium truncate">
                  Inverse-Design Platform
                </div>
              </div>
            )}
          </div>

          {/* Desktop Collapse Toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>

          {/* Mobile Close Button */}
          <button
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation Groups */}
        <div className="flex-1 overflow-y-auto px-3 py-4 select-none">
          {renderNavGroup('Workspace', workspaceItems)}
          {renderNavGroup('Validation & Evidence', validationItems)}
          {renderNavGroup('System', systemItems)}
        </div>

        {/* Scientific Compliance Badge at bottom */}
        {!collapsed && (
          <div className="p-3 m-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-500 space-y-1">
            <div className="font-semibold text-slate-700 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Exact-Physics Verification
            </div>
            <p className="text-[10px] text-slate-400 leading-tight">
              M9 baseline, M10 adaptive, M11 surrogate hierarchy enforced.
            </p>
          </div>
        )}
      </aside>
    </>
  );
};
