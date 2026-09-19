import React, { useState } from 'react';
import {
  FlaskConical,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Flame,
  Shirt,
  Smartphone,
  Users,
  Building,
  Zap,
  Layers,
  TrendingDown,
  Clock,
  ArrowRight,
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
import { api } from '@/api/client';
import { SimulationRequest, SimulationResponse } from '@/api/types';
import { formatKw, formatKwh, formatPercent } from '@/lib/utils';
import { ErrorBanner } from '@/components/common/ErrorBanner';
import { LoadingCard } from '@/components/common/LoadingCard';

const DEFAULT_SCENARIO_INPUTS = {
  total_students: 500,
  baseline_power_kw: 25.0,
  operating_ceiling_kw: 450.0,
  transformer_capacity_kw: 500.0,
  geyser_quantity: 120,
  geyser_max_simultaneous: 60,
  washing_machine_quantity: 20,
  washing_machine_max_simultaneous: 10,
  device_charging_quantity: 300,
  device_charging_max_simultaneous: 150,
};

export const Simulation: React.FC = () => {
  const [params, setParams] = useState(DEFAULT_SCENARIO_INPUTS);
  const [data, setData] = useState<SimulationResponse | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasRun, setHasRun] = useState<boolean>(false);

  const handleInputChange = (field: keyof typeof DEFAULT_SCENARIO_INPUTS, value: string) => {
    const num = parseFloat(value);
    setParams((prev) => ({
      ...prev,
      [field]: isNaN(num) ? 0 : num,
    }));
  };

  const handleReset = () => {
    setParams(DEFAULT_SCENARIO_INPUTS);
    setError(null);
  };

  const runSimulation = async () => {
    setSimulating(true);
    setError(null);
    try {
      const payload: SimulationRequest = {
        total_students: params.total_students,
        baseline_power_kw: params.baseline_power_kw,
        operating_ceiling_kw: params.operating_ceiling_kw,
        transformer_capacity_kw: params.transformer_capacity_kw,
        geyser_quantity: params.geyser_quantity,
        geyser_max_simultaneous: params.geyser_max_simultaneous,
        washing_machine_quantity: params.washing_machine_quantity,
        washing_machine_max_simultaneous: params.washing_machine_max_simultaneous,
        device_charging_quantity: params.device_charging_quantity,
        device_charging_max_simultaneous: params.device_charging_max_simultaneous,
      };

      const res = await api.simulate(payload);
      setData(res);
      setHasRun(true);
    } catch (err: any) {
      setError(err.message || 'Simulation execution failed');
    } finally {
      setSimulating(false);
    }
  };

  // Prepare chart series: Compare reference baseline curve vs simulated curve
  const chartData = data
    ? data.hourly_load_before_kw.map((beforeVal, idx) => ({
        hour: `${idx.toString().padStart(2, '0')}:00`,
        baselineLoadKw: data.hourly_baseline_load_kw[idx] || 0,
        simBeforeKw: beforeVal,
        simAfterKw: data.hourly_load_after_kw[idx] ?? beforeVal,
      }))
    : [];

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner */}
      <div className="p-4 rounded border border-panel-border bg-panel-subtle flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-brand/10 border border-brand/30 text-brand">
            <FlaskConical className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold font-mono text-white tracking-wide">
              What-If Scenario Simulator
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Simulate demographic growth, transformer resizing, and appliance fleet expansions to evaluate electrical bottlenecks.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            disabled={simulating}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-panel-light hover:bg-panel-border border border-panel-border text-xs font-mono text-gray-300 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>
          <button
            onClick={runSimulation}
            disabled={simulating}
            className="flex items-center gap-2 px-5 py-1.5 rounded bg-brand hover:bg-brand-light text-black text-xs font-mono font-bold tracking-wide transition-all shadow-glow-brand disabled:opacity-50"
          >
            {simulating ? (
              <>
                <span className="w-3 h-3 border-2 border-black border-t-transparent rounded-full animate-spin"></span>
                <span>SIMULATING...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-black" />
                <span>RUN SIMULATION</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={runSimulation} isRetrying={simulating} />}

      {/* Parameter Controls Grid */}
      <div className="rounded border border-panel-border bg-panel p-5">
        <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border flex items-center justify-between">
          <span>Configurable Scenario Parameters</span>
          <span className="text-gray-500 text-[10px]">Real-Time What-If Adjustments</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4 text-xs font-mono">
          {/* Facility Controls */}
          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-brand" />
              <span>Resident Students:</span>
            </label>
            <input
              type="number"
              min="1"
              value={params.total_students}
              onChange={(e) => handleInputChange('total_students', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-brand" />
              <span>Constant Baseload (kW):</span>
            </label>
            <input
              type="number"
              min="0"
              step="5"
              value={params.baseline_power_kw}
              onChange={(e) => handleInputChange('baseline_power_kw', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 text-amber" />
              <span>Operating Ceiling (kW):</span>
            </label>
            <input
              type="number"
              min="50"
              step="10"
              value={params.operating_ceiling_kw}
              onChange={(e) => handleInputChange('operating_ceiling_kw', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Building className="w-3.5 h-3.5 text-white" />
              <span>Transformer Rating (kW):</span>
            </label>
            <input
              type="number"
              min="50"
              step="25"
              value={params.transformer_capacity_kw}
              onChange={(e) => handleInputChange('transformer_capacity_kw', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          {/* Geyser Controls */}
          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5 text-brand" />
              <span>Geyser Fleet Quantity:</span>
            </label>
            <input
              type="number"
              min="1"
              value={params.geyser_quantity}
              onChange={(e) => handleInputChange('geyser_quantity', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Flame className="w-3.5 h-3.5 text-brand" />
              <span>Geyser Max Simultaneous:</span>
            </label>
            <input
              type="number"
              min="1"
              value={params.geyser_max_simultaneous}
              onChange={(e) => handleInputChange('geyser_max_simultaneous', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          {/* Washing Machine Controls */}
          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Shirt className="w-3.5 h-3.5 text-brand" />
              <span>Washing Machine Count:</span>
            </label>
            <input
              type="number"
              min="1"
              value={params.washing_machine_quantity}
              onChange={(e) => handleInputChange('washing_machine_quantity', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Shirt className="w-3.5 h-3.5 text-brand" />
              <span>Washer Max Simultaneous:</span>
            </label>
            <input
              type="number"
              min="1"
              value={params.washing_machine_max_simultaneous}
              onChange={(e) => handleInputChange('washing_machine_max_simultaneous', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          {/* Device Charging Controls */}
          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Smartphone className="w-3.5 h-3.5 text-brand" />
              <span>Charging Stations Count:</span>
            </label>
            <input
              type="number"
              min="1"
              value={params.device_charging_quantity}
              onChange={(e) => handleInputChange('device_charging_quantity', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>

          <div className="space-y-1.5 p-3 rounded bg-panel-subtle border border-panel-border">
            <label className="text-gray-400 flex items-center gap-1.5">
              <Smartphone className="w-3.5 h-3.5 text-brand" />
              <span>Charger Max Simultaneous:</span>
            </label>
            <input
              type="number"
              min="1"
              value={params.device_charging_max_simultaneous}
              onChange={(e) => handleInputChange('device_charging_max_simultaneous', e.target.value)}
              className="w-full px-2.5 py-1.5 rounded bg-black/50 border border-panel-border text-white text-xs font-mono focus:border-brand focus:outline-none"
            />
          </div>
        </div>
      </div>

      {!data && !error && (
        <div className="rounded border border-panel-border bg-panel-subtle px-4 py-3">
          <p className="text-xs text-gray-300 font-mono">
            Change hostel population, appliance fleet, or electrical capacity to see how predicted demand and the optimized schedule respond.
          </p>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px] font-mono">
            <div className="border-l-2 border-brand/70 pl-2 text-gray-400">
              <span className="text-brand">↑ Student population</span> — See impact of occupancy growth
            </div>
            <div className="border-l-2 border-brand/70 pl-2 text-gray-400">
              <span className="text-brand">↑ Geyser fleet</span> — Test increased morning demand
            </div>
            <div className="border-l-2 border-amber/70 pl-2 text-gray-400">
              <span className="text-amber">↓ Transformer capacity</span> — Test infrastructure constraints
            </div>
          </div>
        </div>
      )}

      {/* Simulation Results Section */}
      {data && (
        <div className="space-y-6">
          {/* Infeasibility Alert if Solver Infeasible */}
          {!data.is_feasible && (
            <div className="rounded border border-danger/50 bg-danger-dim p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-danger shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold font-mono text-white tracking-wide">
                  SCENARIO INFEASIBLE (Solver: {data.status})
                </h4>
                <p className="text-xs text-gray-300 font-mono mt-1">
                  The requested scenario parameters cannot physically fit within the configured operating ceiling of {data.operating_ceiling_kw} kW and operational windows.
                </p>
                {data.details && (
                  <p className="text-[11px] text-red-300 font-mono mt-2 p-2 rounded bg-black/40 border border-danger/30">
                    {data.details}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Scenario Comparison Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded border border-panel-border bg-panel p-4">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Baseline Peak</span>
              <div className="text-xl font-bold font-mono text-gray-300 mt-1.5">
                {formatKw(data.comparison.baseline_peak_kw)}
              </div>
              <p className="text-[10px] font-mono text-gray-500 mt-1">Default 500-student benchmark</p>
            </div>

            <div className="rounded border border-panel-border bg-panel p-4">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Simulated Peak</span>
              <div className="text-xl font-bold font-mono text-brand mt-1.5">
                {formatKw(data.comparison.simulated_peak_kw)}
              </div>
              <p className="text-[10px] font-mono text-gray-500 mt-1">After CP-SAT load shifting</p>
            </div>

            <div className="rounded border border-panel-border bg-panel p-4">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Peak Difference</span>
              <div className="text-xl font-bold font-mono text-white mt-1.5 flex items-baseline gap-1">
                <span>{data.comparison.peak_difference_kw >= 0 ? `+${data.comparison.peak_difference_kw}` : data.comparison.peak_difference_kw} kW</span>
                <span className="text-xs text-gray-400">({data.comparison.peak_difference_percent}%)</span>
              </div>
              <p className="text-[10px] font-mono text-gray-500 mt-1">vs Reference facility peak</p>
            </div>

            <div className="rounded border border-panel-border bg-panel p-4">
              <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Energy Difference</span>
              <div className="text-xl font-bold font-mono text-white mt-1.5">
                {data.comparison.energy_difference_kwh >= 0 ? `+${data.comparison.energy_difference_kwh}` : data.comparison.energy_difference_kwh} kWh
              </div>
              <p className="text-[10px] font-mono text-gray-500 mt-1">Reflected fleet consumption</p>
            </div>
          </div>

          {/* Before vs After Scenario Load Chart */}
          <div className="rounded border border-panel-border bg-panel p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-2 border-b border-panel-border gap-2">
              <div>
                <h3 className="text-sm font-semibold font-mono text-white tracking-wide">
                  Simulated Scenario Load Profile
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Demand curve showing unoptimized vs CP-SAT optimized demand for the configured parameters.
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono text-gray-400">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-gray-500 inline-block"></span>
                  <span>Simulated Before</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 bg-brand inline-block shadow-[0_0_8px_#10E575]"></span>
                  <span className="text-brand font-medium">Simulated Optimized</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-[#A78BFA] inline-block"></span>
                  <span>Reference Baseline</span>
                </div>
              </div>
            </div>

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
                    stroke="#6B7280"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: '#252A2E' }}
                    unit=" kW"
                    fontFamily="JetBrains Mono"
                    domain={[0, Math.ceil(Math.max(data.simulated_scenario.unoptimized_peak_kw, data.operating_ceiling_kw) * 1.1)]}
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
                      name === 'simBeforeKw' ? 'Simulated Before' : name === 'simAfterKw' ? 'Simulated Optimized' : 'Inflexible Base',
                    ]}
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
                    dataKey="simBeforeKw"
                    name="simBeforeKw"
                    stroke="#64748B"
                    strokeWidth={1.75}
                    strokeDasharray="4 3"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="simAfterKw"
                    name="simAfterKw"
                    stroke="#10E575"
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 5, fill: '#10E575', stroke: '#0B0D0F' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="baselineLoadKw"
                    name="baselineLoadKw"
                    stroke="#A78BFA"
                    strokeWidth={1.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
