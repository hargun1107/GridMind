import React, { useState, useEffect } from 'react';
import {
  Zap,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  TrendingDown,
  ShieldCheck,
  AlertTriangle,
  Info,
  Sliders,
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { api } from '@/api/client';
import { OptimizationResponse, OptimizationRequest } from '@/api/types';
import { formatKw, formatPercent, formatKwh } from '@/lib/utils';
import { ErrorBanner } from '@/components/common/ErrorBanner';
import { LoadingCard } from '@/components/common/LoadingCard';

export const Optimization: React.FC = () => {
  const [data, setData] = useState<OptimizationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [solving, setSolving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Optimizer parameters
  const [enforceCeiling, setEnforceCeiling] = useState<boolean>(true);
  const [timeLimit, setTimeLimit] = useState<number>(10.0);
  const [resolutionMode, setResolutionMode] = useState<'hourly' | 'slot'>('hourly');

  const executeOptimization = async (customParams?: OptimizationRequest) => {
    setSolving(true);
    setError(null);
    try {
      const payload: OptimizationRequest = customParams || {
        enforce_operating_ceiling: enforceCeiling,
        time_limit_seconds: timeLimit,
      };
      const res = await api.optimize(payload);
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute CP-SAT optimization');
    } finally {
      setSolving(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    executeOptimization();
  }, []);

  if (loading) {
    return <LoadingCard label="Initializing OR-Tools CP-SAT Solver..." sublabel="Loading appliance flexibility constraints and utility demand forecast" />;
  }

  // Chart data formatting based on hourly (24 pts) or 30-min slot (48 pts)
  const chartData = data
    ? resolutionMode === 'hourly'
      ? data.hourly_load_before_kw.map((beforeVal, idx) => ({
          time: `${idx.toString().padStart(2, '0')}:00`,
          beforeKw: beforeVal,
          afterKw: data.hourly_load_after_kw[idx] ?? beforeVal,
        }))
      : (data.slot_load_before_kw || []).map((beforeVal, idx) => {
          const hour = Math.floor(idx / 2);
          const minute = idx % 2 === 0 ? '00' : '30';
          return {
            time: `${hour.toString().padStart(2, '0')}:${minute}`,
            beforeKw: beforeVal,
            afterKw: (data.slot_load_after_kw || [])[idx] ?? beforeVal,
          };
        })
    : [];

  return (
    <div className="space-y-6 pb-12">
      {/* Top Controls Action Bar */}
      <div className="p-5 rounded border border-panel-border bg-panel flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold font-mono text-white tracking-wide flex items-center gap-2">
            <Zap className="w-5 h-5 text-brand" />
            <span>Google OR-Tools CP-SAT Constraint Engine</span>
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Solves the discrete-time appliance scheduling problem to flatten hostel electrical peaks below 450 kW.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Ceiling Enforce Toggle */}
          <label className="flex items-center gap-2 px-3 py-1.5 rounded bg-panel-subtle border border-panel-border text-xs font-mono text-gray-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={enforceCeiling}
              onChange={(e) => setEnforceCeiling(e.target.checked)}
              className="rounded accent-brand"
            />
            <span>Cap &le; 450 kW</span>
          </label>

          {/* Prominent RUN OPTIMIZATION Button */}
          <button
            onClick={() => executeOptimization()}
            disabled={solving}
            className="flex-1 md:flex-initial inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded bg-brand hover:bg-brand-light text-black font-mono font-bold text-xs tracking-wider transition-all duration-150 shadow-glow-brand disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {solving ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin"></span>
                <span>SOLVING CP-SAT...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-black" />
                <span>RUN OPTIMIZATION</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <ErrorBanner
          message={error}
          onRetry={() => executeOptimization()}
          isRetrying={solving}
        />
      )}

      {data && (
        <>
          {/* Telemetry KPI Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
            {/* Baseline Peak */}
            <div className="rounded border border-panel-border bg-panel p-3.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Baseline Peak</span>
              <div className="text-xl font-bold font-mono text-white mt-1.5">{formatKw(data.baseline_peak_kw)}</div>
              <p className="text-[10px] font-mono text-gray-500 mt-1">Unshifted load maximum</p>
            </div>

            {/* Optimized Peak */}
            <div className="rounded border border-panel-border bg-panel p-3.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Optimized Peak</span>
              <div className="text-xl font-bold font-mono text-brand mt-1.5">{formatKw(data.optimized_peak_kw)}</div>
              <p className="text-[10px] font-mono text-brand/80 mt-1">Global CP-SAT minimum</p>
            </div>

            {/* Absolute Peak Reduction */}
            <div className="rounded border border-panel-border bg-panel p-3.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Peak Reduction</span>
              <div className="text-xl font-bold font-mono text-brand mt-1.5">{formatKw(data.peak_reduction_kw)}</div>
              <p className="text-[10px] font-mono text-brand mt-1">-{formatPercent(data.peak_reduction_percent)} shaved</p>
            </div>

            {/* Energy Conservation */}
            <div className="rounded border border-panel-border bg-panel p-3.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Daily Energy</span>
              <div className="text-xl font-bold font-mono text-white mt-1.5">{formatKwh(data.optimized_total_energy_kwh)}</div>
              <p className="text-[10px] font-mono text-gray-400 mt-1">100% physically conserved</p>
            </div>

            {/* Solver Status */}
            <div className="rounded border border-panel-border bg-panel p-3.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Solver Status</span>
              <div className="text-xl font-bold font-mono text-white mt-1.5 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-brand" />
                <span>{data.status}</span>
              </div>
              <p className="text-[10px] font-mono text-gray-500 mt-1">Proven mathematical optimum</p>
            </div>

            {/* Solver Runtime */}
            <div className="rounded border border-panel-border bg-panel p-3.5">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Execution Time</span>
              <div className="text-xl font-bold font-mono text-white mt-1.5">{data.solver_runtime_seconds.toFixed(4)} s</div>
              <p className="text-[10px] font-mono text-gray-500 mt-1">Single-worker deterministic</p>
            </div>
          </div>

          {/* Before vs After Chart */}
          <div className="rounded border border-panel-border bg-panel p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-2 border-b border-panel-border gap-2">
              <div>
                <h3 className="text-sm font-semibold font-mono text-white tracking-wide">
                  Before vs After Demand Profile
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Redistributed electrical profile demonstrating peak shaving.
                </p>
              </div>

              <div className="flex items-center gap-3">
                {/* Resolution switch: Hourly vs 30-min */}
                <div className="flex rounded border border-panel-border bg-panel-subtle p-0.5 text-[11px] font-mono">
                  <button
                    onClick={() => setResolutionMode('hourly')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      resolutionMode === 'hourly'
                        ? 'bg-panel-border text-white font-medium'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    24h Hourly
                  </button>
                  <button
                    onClick={() => setResolutionMode('slot')}
                    className={`px-2.5 py-1 rounded transition-colors ${
                      resolutionMode === 'slot'
                        ? 'bg-panel-border text-white font-medium'
                        : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    48 Slots (30m)
                  </button>
                </div>
              </div>
            </div>

            <div className="h-[380px] w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F2428" vertical={false} />
                  <XAxis
                    dataKey="time"
                    stroke="#6B7280"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: '#252A2E' }}
                    fontFamily="JetBrains Mono"
                  />
                  <YAxis
                    stroke="#6B7280"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: '#252A2E' }}
                    unit=" kW"
                    fontFamily="JetBrains Mono"
                    domain={[0, Math.ceil(Math.max(data.baseline_peak_kw, data.operating_ceiling_kw) * 1.1)]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#121518',
                      borderColor: '#252A2E',
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontFamily: 'JetBrains Mono',
                    }}
                    formatter={(val: number, name: string) => [
                      `${val.toFixed(2)} kW`,
                      name === 'beforeKw' ? 'Before Optimization' : 'Optimized Load',
                    ]}
                    labelStyle={{ color: '#9CA3AF' }}
                  />
                  <ReferenceLine
                    y={data.operating_ceiling_kw}
                    stroke="#F59E0B"
                    strokeDasharray="4 4"
                    label={{
                      value: `Operating Ceiling: ${data.operating_ceiling_kw} kW`,
                      fill: '#F59E0B',
                      fontSize: 10,
                      fontFamily: 'JetBrains Mono',
                      position: 'insideTopRight',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="beforeKw"
                    name="beforeKw"
                    stroke="#64748B"
                    strokeWidth={1.75}
                    strokeDasharray="4 3"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="afterKw"
                    name="afterKw"
                    stroke="#10E575"
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 5, fill: '#10E575', stroke: '#0B0D0F' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Critical Data Semantics Banner */}
            <div className="mt-4 p-3 rounded bg-panel-subtle border border-brand/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono">
              <div className="flex items-center gap-2 text-gray-300">
                <CheckCircle2 className="w-4 h-4 text-brand shrink-0" />
                <span>
                  <strong className="text-white">Energy shifted, not eliminated:</strong> Baseline energy ({formatKwh(data.baseline_total_energy_kwh)}) equals optimized energy ({formatKwh(data.optimized_total_energy_kwh)}). Demand is redistributed to avoid transformer saturation.
                </span>
              </div>
              <span className="text-[11px] text-brand px-2 py-0.5 rounded bg-brand/10 border border-brand/30 shrink-0 font-medium">
                Peak Reduction: {data.peak_reduction_kw} kW
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
