import React, { useState, useEffect } from 'react';
import { RefreshCw, Server, AlertCircle } from 'lucide-react';
import { NavTab } from './Sidebar';

interface HeaderProps {
  activeTab: NavTab;
  isBackendOnline: boolean;
  onRefreshAll?: () => void;
  isRefreshing?: boolean;
}

const TAB_TITLES: Record<NavTab, { title: string; subtitle: string }> = {
  overview: {
    title: 'Energy Intelligence Center',
    subtitle: 'AI-powered hostel demand forecasting and peak-load optimization.',
  },
  forecast: {
    title: '24-Hour Demand Forecast',
    subtitle: 'Autoregressive Ridge regression demand curve trained on real utility load dynamics.',
  },
  optimization: {
    title: 'Peak Load Optimization',
    subtitle: 'Google OR-Tools CP-SAT discrete-interval constraint solver for flexible appliance shifting.',
  },
  appliances: {
    title: 'Appliance Flexibility Matrix',
    subtitle: '48 half-hour scheduling intervals across the 24-hour facility operational horizon.',
  },
  simulation: {
    title: 'What-If Scenario Simulation',
    subtitle: 'Evaluate electrical impact of demographic growth, circuit capacity, and fleet adjustments.',
  },
  model: {
    title: 'Model Telemetry & Provenance',
    subtitle: 'Technical verification metrics, feature engineering, and training pipeline provenance.',
  },
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  isBackendOnline,
  onRefreshAll,
  isRefreshing,
}) => {
  const [timeStr, setTimeStr] = useState<string>('');
  const meta = TAB_TITLES[activeTab] || TAB_TITLES.overview;

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-panel-border bg-panel/70 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-10">
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-base font-semibold text-white font-mono tracking-wide">
            {meta.title}
          </h1>
          <span className="text-[11px] text-gray-500 font-mono">/</span>
          <span className="text-xs text-gray-400 font-mono capitalize">{activeTab}</span>
        </div>
        <p className="text-xs text-gray-400 mt-0.5">{meta.subtitle}</p>
      </div>

      <div className="flex items-center gap-4">
        {/* UTC / Local telemetry clock */}
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded bg-panel-light border border-panel-border text-xs font-mono text-gray-300">
          <span className="text-gray-500">SYS TIME:</span>
          <span className="text-brand font-semibold">{timeStr}</span>
        </div>

        {/* Global refresh button */}
        {onRefreshAll && (
          <button
            onClick={onRefreshAll}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-panel-light hover:bg-panel-border border border-panel-border text-xs font-mono text-gray-300 hover:text-white transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-brand' : ''}`} />
            <span>SYNC</span>
          </button>
        )}
      </div>
    </header>
  );
};
