import React from 'react';
import {
  Activity,
  TrendingUp,
  Zap,
  SlidersHorizontal,
  FlaskConical,
  Database,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { HealthResponse } from '@/api/types';

export type NavTab = 'overview' | 'forecast' | 'optimization' | 'appliances' | 'simulation' | 'model';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  health,
  healthLoading,
  onRefreshHealth,
}) => {
  const isOnline = !!health && health.status === 'online';

  const navItems = [
    { id: 'overview' as NavTab, label: 'Overview', icon: Activity, badge: 'Live' },
    { id: 'forecast' as NavTab, label: 'Demand Forecast', icon: TrendingUp },
    { id: 'optimization' as NavTab, label: 'Peak Optimization', icon: Zap, highlight: true },
    { id: 'appliances' as NavTab, label: 'Appliance Matrix', icon: SlidersHorizontal },
    { id: 'simulation' as NavTab, label: 'What-If Simulation', icon: FlaskConical },
    { id: 'model' as NavTab, label: 'Model Provenance', icon: Database },
  ];

  return (
    <aside className="w-64 bg-panel border-r border-panel-border flex flex-col justify-between h-screen sticky top-0 select-none z-20">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-panel-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded bg-brand/10 border border-brand/30 flex items-center justify-center text-brand">
              <Zap className="w-5 h-5 fill-brand/20 text-brand" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg tracking-wider text-white font-mono">GRIDMIND</span>
                <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-brand/15 text-brand border border-brand/30">
                  {health?.version ? `v${health.version}` : 'API'}
                </span>
              </div>
              <p className="text-[10px] font-mono tracking-widest text-gray-400 uppercase">
                ENERGY INTELLIGENCE
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          <div className="px-3 pt-2 pb-1.5 text-[10px] font-mono uppercase tracking-wider text-gray-500 font-semibold">
            Control Center
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={cn(
                  'w-full flex items-center justify-between px-3.5 py-2.5 rounded text-sm font-medium transition-all duration-150 text-left',
                  isActive
                    ? 'bg-brand/10 text-white border-l-2 border-brand font-semibold shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-panel-light'
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      'w-4 h-4 transition-colors',
                      isActive ? 'text-brand' : 'text-gray-500 group-hover:text-gray-300'
                    )}
                  />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-panel-border text-gray-300">
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Backend Status Footer */}
      <div className="p-4 border-t border-panel-border bg-panel-subtle/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'w-2.5 h-2.5 rounded-full inline-block animate-pulse',
                isOnline ? 'bg-brand shadow-[0_0_8px_#10E575]' : 'bg-danger shadow-[0_0_8px_#EF4444]'
              )}
            />
            <span className="text-xs font-mono font-semibold tracking-wide">
              {isOnline ? (
                <span className="text-brand">SYSTEM ONLINE</span>
              ) : (
                <span className="text-danger">BACKEND OFFLINE</span>
              )}
            </span>
          </div>

          <button
            onClick={onRefreshHealth}
            disabled={healthLoading}
            title="Refresh connection status"
            className="p-1 hover:bg-panel-light rounded text-gray-400 hover:text-gray-200 transition-colors"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', healthLoading && 'animate-spin text-brand')} />
          </button>
        </div>

        <div className="mt-2 text-[10px] font-mono text-gray-500 flex items-center justify-between">
          <span>Port 8000</span>
          <span>{health?.version ? `API v${health.version}` : '127.0.0.1'}</span>
        </div>
      </div>
    </aside>
  );
};
