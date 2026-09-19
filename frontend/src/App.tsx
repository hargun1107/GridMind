import React, { useState, useEffect } from 'react';
import { Sidebar, NavTab } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { Overview } from '@/pages/Overview';
import { Forecast } from '@/pages/Forecast';
import { Optimization } from '@/pages/Optimization';
import { Appliances } from '@/pages/Appliances';
import { Simulation } from '@/pages/Simulation';
import { Model } from '@/pages/Model';
import { api } from '@/api/client';
import { HealthResponse } from '@/api/types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const checkHealth = async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const res = await api.getHealth();
      setHealth(res);
    } catch (err: any) {
      setHealth(null);
      setHealthError(err.message || 'Backend unavailable');
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // Poll health status every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex min-h-screen bg-background text-gray-100 font-sans">
      {/* Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        health={health}
        healthLoading={healthLoading}
        onRefreshHealth={checkHealth}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-background bg-grid-pattern">
        <Header
          activeTab={activeTab}
          isBackendOnline={!!health && health.status === 'online'}
          onRefreshAll={checkHealth}
          isRefreshing={healthLoading}
        />

        <main className="flex-1 p-6 max-w-7xl w-full mx-auto overflow-y-auto">
          {activeTab === 'overview' && (
            <Overview
              health={health}
              healthError={healthError}
              onNavigateTab={setActiveTab}
            />
          )}
          {activeTab === 'forecast' && <Forecast />}
          {activeTab === 'optimization' && <Optimization />}
          {activeTab === 'appliances' && <Appliances />}
          {activeTab === 'simulation' && <Simulation />}
          {activeTab === 'model' && <Model />}
        </main>
      </div>
    </div>
  );
};

export default App;
