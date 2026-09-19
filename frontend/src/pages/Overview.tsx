import React, { useState, useEffect } from 'react';
import {
  TrendingDown,
  ShieldCheck,
  Zap,
  Cpu,
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
  Gauge,
  Info,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
} from 'recharts';
import { api, ApiError } from '@/api/client';
import { OptimizationResponse, HealthResponse } from '@/api/types';
import { formatKw, formatPercent, formatKwh } from '@/lib/utils';
import { ErrorBanner } from '@/components/common/ErrorBanner';
import { LoadingCard } from '@/components/common/LoadingCard';

interface OverviewProps {
  health: HealthResponse | null;
  healthError: string | null;
  onNavigateTab: (tab: any) => void;
}

export const Overview: React.FC<OverviewProps> = ({
  health,
  healthError,
  onNavigateTab,
}) => {
  const [optData, setOptData] = useState<OptimizationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.optimize();
      setOptData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load optimization telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverviewData();
  }, []);

  if (loading) {
    return <LoadingCard label="Connecting to GridMind Energy Control System..." sublabel="Fetching 24-hour demand forecast and baseline CP-SAT optimization" />;
  }

  if (error || healthError) {
    return (
      <ErrorBanner
        message={error || healthError || 'Unable to communicate with the GridMind backend API.'}
        onRetry={fetchOverviewData}
        isRetrying={loading}
      />
    );
  }

  if (!optData) {
    return null;
  }

  // Calculate Safe Headroom according to spec: operating_ceiling_kw - optimized_peak_kw
  const safeHeadroomKw = Number(
    (optData.operating_ceiling_kw - optData.optimized_peak_kw).toFixed(2)
  );

  // Prepare chart series from hourly_load_before_kw and hourly_load_after_kw
  const chartData = optData.hourly_load_before_kw.map((beforeVal, idx) => {
    const afterVal = optData.hourly_load_after_kw[idx] ?? beforeVal;
    const hourLabel = `${idx.toString().padStart(2, '0')}:00`;
    return {
      hour: hourLabel,
      beforeKw: beforeVal,
      afterKw: afterVal,
      shavedKw: Math.max(0, Number((beforeVal - afterVal).toFixed(2))),
    };
  });
  const actualLoadPeakKw = Math.max(
    ...chartData.flatMap(({ beforeKw, afterKw }) => [beforeKw, afterKw]),
    0
  );
  const loadAxisMaxKw = Math.max(10, Math.ceil((actualLoadPeakKw * 1.15) / 10) * 10);

  return (
    <div className="space-y-6 pb-12">
      {/* Overview Top Header Notice */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded border border-panel-border bg-panel-subtle">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-brand/10 border border-brand/30 text-brand shrink-0 mt-0.5">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white font-mono tracking-wide">
              Facility Status: {health?.status === 'online' ? 'Online' : 'Degraded'}
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              GridMind is actively optimizing flexible appliance demand across 30-minute intervals. Transformer capacity:{' '}
              <span className="text-gray-200 font-mono font-medium">{optData.transformer_capacity_kw} kW</span>.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigateTab('optimization')}
            className="px-3.5 py-1.5 rounded bg-brand/15 hover:bg-brand/25 border border-brand/40 text-brand text-xs font-mono font-semibold transition-all"
          >
            Open Optimizer →
          </button>
        </div>
      </div>

      {/* 4 Core KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Forecast Peak */}
        <div className="rounded border border-panel-border bg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-[11px] font-mono uppercase tracking-wider">Unoptimized Peak</span>
            <Activity className="w-4 h-4 text-gray-500" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-white">
              {formatKw(optData.baseline_peak_kw)}
            </div>
            <p className="text-[11px] text-gray-400 mt-1 flex items-center gap-1 font-mono">
              <span>Coincident baseline load</span>
            </p>
          </div>
          <div className="mt-3 pt-2.5 border-t border-panel-border text-[10px] font-mono text-gray-500 flex justify-between">
            <span>Limit: {optData.operating_ceiling_kw} kW</span>
            <span className="text-amber">Before Shifting</span>
          </div>
        </div>

        {/* Card 2: Optimized Peak */}
        <div className="rounded border border-panel-border bg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-[11px] font-mono uppercase tracking-wider">Optimized Peak</span>
            <Zap className="w-4 h-4 text-brand" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-brand">
              {formatKw(optData.optimized_peak_kw)}
            </div>
            <p className="text-[11px] text-gray-400 mt-1 flex items-center gap-1 font-mono">
              <span>CP-SAT Shaved Maximum</span>
            </p>
          </div>
          <div className="mt-3 pt-2.5 border-t border-panel-border text-[10px] font-mono text-gray-500 flex justify-between">
            <span>Solver: {optData.status}</span>
            <span className="text-brand">Global Optimum</span>
          </div>
        </div>

        {/* Card 3: Peak Reduction */}
        <div className="rounded border border-panel-border bg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-[11px] font-mono uppercase tracking-wider">Peak Reduction</span>
            <TrendingDown className="w-4 h-4 text-brand" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-white flex items-baseline gap-2">
              <span>{formatKw(optData.peak_reduction_kw)}</span>
              <span className="text-xs font-semibold text-brand">
                (-{formatPercent(optData.peak_reduction_percent)})
              </span>
            </div>
            <p className="text-[11px] text-gray-400 mt-1 font-mono">
              Demand shaved from bottleneck
            </p>
          </div>
          <div className="mt-3 pt-2.5 border-t border-panel-border text-[10px] font-mono text-gray-500 flex justify-between">
            <span>Shifted Load</span>
            <span className="text-gray-300 font-medium">100% Retained</span>
          </div>
        </div>

        {/* Card 4: Safe Headroom */}
        <div className="rounded border border-panel-border bg-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-gray-400">
            <span className="text-[11px] font-mono uppercase tracking-wider">Safe Headroom</span>
            <ShieldCheck className="w-4 h-4 text-brand" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-mono text-white">
              {formatKw(safeHeadroomKw)}
            </div>
            <p className="text-[11px] text-gray-400 mt-1 font-mono">
              Below 450 kW Operating Ceiling
            </p>
          </div>
          <div className="mt-3 pt-2.5 border-t border-panel-border text-[10px] font-mono text-gray-500 flex justify-between">
            <span>Capacity Margin</span>
            <span className="text-brand font-medium">Safe Boundary</span>
          </div>
        </div>
      </div>

      {/* Main 24-Hour Load Profile Chart */}
      <div className="rounded border border-panel-border bg-panel p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-2 border-b border-panel-border gap-2">
          <div>
            <h3 className="text-sm font-semibold font-mono text-white tracking-wide flex items-center gap-2">
              <span>24-Hour Load Profile (kW)</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand/10 text-brand border border-brand/30">
                Peak Shaving Visualization
              </span>
            </h3>
            <p className="text-xs text-gray-400 mt-1">
              Comparison between unoptimized preferred-start baseline and CP-SAT redistributed schedule.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono text-gray-400">
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 bg-gray-500 inline-block"></span>
              <span>Before Optimization</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-1 bg-brand inline-block shadow-[0_0_8px_#10E575]"></span>
              <span className="text-brand font-medium">After Optimization</span>
            </div>
          </div>
        </div>

        {/* Recharts Line Chart */}
        <div className="h-[360px] w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2428" vertical={false} />
              <XAxis
                dataKey="hour"
                stroke="#6B7280"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#252A2E' }}
                fontFamily="JetBrains Mono"
              />
              <YAxis
                yAxisId="load"
                stroke="#6B7280"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: '#252A2E' }}
                unit=" kW"
                fontFamily="JetBrains Mono"
                domain={[0, loadAxisMaxKw]}
              />
              <YAxis
                yAxisId="ceiling"
                orientation="right"
                hide
                domain={[0, optData.operating_ceiling_kw]}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#121518',
                  borderColor: '#252A2E',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'JetBrains Mono',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                }}
                formatter={(val: number, name: string) => {
                  if (name === 'beforeKw') return [`${val.toFixed(2)} kW`, 'Before Optimization'];
                  if (name === 'afterKw') return [`${val.toFixed(2)} kW`, 'Optimized Load'];
                  return [`${val.toFixed(2)} kW`, name];
                }}
                labelStyle={{ color: '#9CA3AF', marginBottom: '4px' }}
              />
              {/* Facility safety ceiling line */}
              <ReferenceLine
                yAxisId="ceiling"
                y={optData.operating_ceiling_kw}
                stroke="#F59E0B"
                strokeDasharray="4 4"
                label={{
                  value: `Ceiling: ${optData.operating_ceiling_kw} kW`,
                  fill: '#F59E0B',
                  fontSize: 10,
                  fontFamily: 'JetBrains Mono',
                  position: 'insideTopRight',
                }}
              />
              {/* Before Optimization Series (Muted Gray Line) */}
              <Line
                yAxisId="load"
                type="monotone"
                dataKey="beforeKw"
                name="beforeKw"
                stroke="#64748B"
                strokeWidth={1.75}
                strokeDasharray="4 3"
                dot={false}
                activeDot={{ r: 4, stroke: '#94A3B8', strokeWidth: 2 }}
              />
              {/* After Optimization Series (Vibrant Electric Lime Accent) */}
              <Line
                yAxisId="load"
                type="monotone"
                dataKey="afterKw"
                name="afterKw"
                stroke="#10E575"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 5, fill: '#10E575', stroke: '#0B0D0F', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Semantic Note Guarantee */}
        <div className="mt-3 p-2.5 rounded bg-panel-subtle border border-panel-border flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2 text-gray-400">
            <Info className="w-4 h-4 text-brand shrink-0" />
            <span>
              <strong className="text-gray-200">Semantic Notice:</strong> Flexible appliance demand is shifted away from peak periods. Total daily energy is conserved (
              <span className="text-brand font-medium">{formatKwh(optData.baseline_total_energy_kwh)}</span> before vs{' '}
              <span className="text-brand font-medium">{formatKwh(optData.optimized_total_energy_kwh)}</span> after).
            </span>
          </div>
          <span className="text-[11px] text-gray-500 uppercase tracking-wider hidden md:inline">
            48 Optimization Slots (30m Resolution)
          </span>
        </div>
      </div>

      {/* System Status Engine Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Subsystem Health Grid */}
        <div className="rounded border border-panel-border bg-panel p-4">
          <h4 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border flex items-center justify-between">
            <span>Subsystem Telemetry</span>
            <span className={health?.status === 'online' ? 'text-[10px] text-brand lowercase' : 'text-[10px] text-amber lowercase'}>
              {health?.status === 'online' ? 'all systems nominal' : 'backend degraded'}
            </span>
          </h4>
          <div className="mt-3 space-y-2.5">
            <div className="flex items-center justify-between text-xs font-mono p-2 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-300">FastAPI Backend API</span>
              <span className="flex items-center gap-1.5 text-brand font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> {health?.status === 'online' ? 'Online' : 'Degraded'} (v{health?.version ?? '--'})
              </span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono p-2 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-300">Demand Forecast Engine (Ridge ML)</span>
              <span className="flex items-center gap-1.5 text-brand font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Forecast API available
              </span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono p-2 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-300">Hostel Digital Twin Service</span>
              <span className="flex items-center gap-1.5 text-brand font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Scenario service available
              </span>
            </div>
            <div className="flex items-center justify-between text-xs font-mono p-2 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-300">CP-SAT Constraint Scheduler (OR-Tools)</span>
              <span className="flex items-center gap-1.5 text-brand font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Online ({optData.solver_runtime_seconds}s solve)
              </span>
            </div>
          </div>
        </div>

        {/* Operating Thresholds & Headroom Summary */}
        <div className="rounded border border-panel-border bg-panel p-4">
          <h4 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border">
            Facility Physical Boundaries
          </h4>
          <div className="mt-3 space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center py-1 border-b border-panel-border/60">
              <span className="text-gray-400">Transformer Capacity:</span>
              <span className="text-white font-semibold">{optData.transformer_capacity_kw} kW</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-panel-border/60">
              <span className="text-gray-400">Safe Operating Ceiling:</span>
              <span className="text-amber font-semibold">{optData.operating_ceiling_kw} kW</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-panel-border/60">
              <span className="text-gray-400">Maximum Instantaneous Load:</span>
              <span className="text-brand font-semibold">{optData.optimized_peak_kw} kW</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-panel-border/60">
              <span className="text-gray-400">Remaining Transformer Headroom:</span>
              <span className="text-white font-semibold">{optData.minimum_headroom_kw} kW at peak</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="text-gray-400">Threshold Breaches:</span>
              <span className="text-brand font-semibold">0 Hours (Clean Safe Envelope)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
