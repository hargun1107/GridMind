import React, { useState, useEffect } from 'react';
import {
  SlidersHorizontal,
  Flame,
  Shirt,
  Smartphone,
  Clock,
  Zap,
  Info,
  Layers,
} from 'lucide-react';
import { api } from '@/api/client';
import { OptimizationResponse } from '@/api/types';
import { ErrorBanner } from '@/components/common/ErrorBanner';
import { LoadingCard } from '@/components/common/LoadingCard';

interface ApplianceConfigMeta {
  key: string;
  name: string;
  icon: any;
  quantity: number;
  unitPowerKw: number;
  runtimeHours: number;
  window: string;
  maxSimultaneous: number;
  color: string;
}

const APPLIANCE_SPECS: ApplianceConfigMeta[] = [
  {
    key: 'geyser',
    name: 'Water Heaters / Geysers',
    icon: Flame,
    quantity: 120,
    unitPowerKw: 2.0,
    runtimeHours: 0.5,
    window: '05:00 → 22:00',
    maxSimultaneous: 60,
    color: '#10E575',
  },
  {
    key: 'washing_machine',
    name: 'Common Laundry Machines',
    icon: Shirt,
    quantity: 20,
    unitPowerKw: 0.7,
    runtimeHours: 1.0,
    window: '08:00 → 23:00',
    maxSimultaneous: 10,
    color: '#0AA852',
  },
  {
    key: 'device_charging',
    name: 'Personal Device & EV Chargers',
    icon: Smartphone,
    quantity: 300,
    unitPowerKw: 0.1,
    runtimeHours: 2.0,
    window: '00:00 → 24:00',
    maxSimultaneous: 150,
    color: '#4EFA9D',
  },
];

export const Appliances: React.FC = () => {
  const [data, setData] = useState<OptimizationResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredSlot, setHoveredSlot] = useState<{ app: string; slot: number; count: number } | null>(null);

  const fetchSchedule = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.optimize();
      setData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load appliance schedule');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  if (loading) {
    return <LoadingCard label="Loading Appliance Schedule Matrix..." sublabel="Extracting 48 discrete CP-SAT decision variables" />;
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={fetchSchedule} isRetrying={loading} />;
  }

  if (!data || !data.appliance_schedule) {
    return null;
  }

  // Generate 48 half-hour labels
  const timeSlots = Array.from({ length: 48 }, (_, i) => {
    const hour = Math.floor(i / 2);
    const min = i % 2 === 0 ? '00' : '30';
    return `${hour.toString().padStart(2, '0')}:${min}`;
  });

  // Calculate color intensity helper
  const getSlotColor = (count: number, max: number, baseColor: string) => {
    if (count === 0) return 'bg-[#15191D] border-panel-border/40';
    const ratio = count / max;
    if (ratio <= 0.33) return 'bg-[#0AA852]/40 border-[#10E575]/50 text-white';
    if (ratio <= 0.7) return 'bg-[#10E575]/75 border-[#10E575] text-black font-semibold';
    return 'bg-[#10E575] border-[#4EFA9D] text-black font-bold shadow-[0_0_8px_rgba(16,229,117,0.5)]';
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Notice */}
      <div className="p-4 rounded border border-panel-border bg-panel-subtle flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-brand/10 border border-brand/30 text-brand">
            <SlidersHorizontal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold font-mono text-white tracking-wide">
              Discrete Appliance Scheduling Heatmap
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              48 half-hour slots across the 24-hour horizon. Each cell represents active units during that 30-minute interval.
            </p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs font-mono text-gray-400">
          <span className="text-[11px] text-gray-500 uppercase">Activity:</span>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#15191D] border border-panel-border"></span>
            <span>Idle</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#0AA852]/40 border border-[#10E575]/50"></span>
            <span>Low</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#10E575]/75 border border-[#10E575]"></span>
            <span>Medium</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[#10E575] border border-[#4EFA9D]"></span>
            <span>Max</span>
          </div>
        </div>
      </div>

      {/* Main Heatmap Matrix */}
      <div className="rounded border border-panel-border bg-panel p-5 overflow-x-auto">
        <div className="min-w-[860px]">
          {/* Timeline Time Labels Header */}
          <div className="grid grid-cols-[180px_repeat(48,1fr)] gap-1 pb-2 border-b border-panel-border text-[9px] font-mono text-gray-500">
            <span className="text-xs font-medium text-gray-400 pl-1">APPLIANCE FLEET</span>
            {timeSlots.map((slot, i) => (
              <span
                key={i}
                className={`text-center ${i % 4 === 0 ? 'text-gray-300 font-semibold' : 'text-transparent'}`}
                title={slot}
              >
                {i % 4 === 0 ? slot.slice(0, 2) : ''}
              </span>
            ))}
          </div>

          {/* Rows for each appliance category */}
          <div className="space-y-3 pt-3">
            {APPLIANCE_SPECS.map((spec) => {
              const Icon = spec.icon;
              const schedule = data.appliance_schedule[spec.key] || Array(48).fill(0);
              const maxUnits = spec.maxSimultaneous;
              const totalActiveSlots = schedule.reduce((acc, v) => acc + v, 0);

              return (
                <div key={spec.key} className="space-y-1">
                  <div className="grid grid-cols-[180px_repeat(48,1fr)] gap-1 items-center">
                    {/* Row Label */}
                    <div className="flex items-center gap-2 pr-2">
                      <div className="p-1 rounded bg-panel-subtle border border-panel-border text-brand shrink-0">
                        <Icon className="w-3.5 h-3.5" />
                      </div>
                      <div className="truncate">
                        <p className="text-xs font-semibold text-white font-mono truncate">{spec.name}</p>
                        <p className="text-[10px] text-gray-500 font-mono">
                          {spec.quantity} units • Max {spec.maxSimultaneous}/slot
                        </p>
                      </div>
                    </div>

                    {/* 48 Slots */}
                    {schedule.map((count, slotIdx) => (
                      <div
                        key={slotIdx}
                        onMouseEnter={() => setHoveredSlot({ app: spec.name, slot: slotIdx, count })}
                        onMouseLeave={() => setHoveredSlot(null)}
                        className={`h-9 rounded-sm border flex items-center justify-center text-[10px] font-mono transition-transform hover:scale-110 cursor-pointer ${getSlotColor(
                          count,
                          maxUnits,
                          spec.color
                        )}`}
                        title={`${spec.name} at ${timeSlots[slotIdx]}: ${count} active units`}
                      >
                        {count > 0 && <span className="truncate">{count}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Tooltip detail bar */}
          <div className="mt-4 pt-3 border-t border-panel-border flex items-center justify-between text-xs font-mono text-gray-400">
            {hoveredSlot ? (
              <span className="text-brand flex items-center gap-2">
                <Clock className="w-3.5 h-3.5" />
                <span>
                  <strong>{hoveredSlot.app}</strong> at <strong>{timeSlots[hoveredSlot.slot]}</strong>: {hoveredSlot.count} active units drawing{' '}
                  {(
                    hoveredSlot.count *
                    (APPLIANCE_SPECS.find((s) => s.name === hoveredSlot.app)?.unitPowerKw || 1)
                  ).toFixed(1)}{' '}
                  kW
                </span>
              </span>
            ) : (
              <span className="text-gray-500 flex items-center gap-2">
                <Info className="w-3.5 h-3.5" /> Hover over any 30-minute slot cell to inspect instantaneous active unit count and power draw.
              </span>
            )}

            <span className="text-gray-500">Interval granularity: 30 minutes (&Delta;t = 0.5h)</span>
          </div>
        </div>
      </div>

      {/* Appliance Fleet Constraint Cards */}
      <div>
        <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 mb-3">
          Configured Operational Constraints
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {APPLIANCE_SPECS.map((spec) => {
            const Icon = spec.icon;
            const dailyEnergyKwh = spec.quantity * spec.unitPowerKw * spec.runtimeHours;

            return (
              <div key={spec.key} className="rounded border border-panel-border bg-panel p-4 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-panel-border">
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-brand" />
                    <span className="text-xs font-bold font-mono text-white">{spec.name}</span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-brand/10 text-brand border border-brand/30">
                    {spec.quantity} Units
                  </span>
                </div>

                <div className="space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between text-gray-400">
                    <span>Power per Unit:</span>
                    <span className="text-gray-200">{spec.unitPowerKw} kW</span>
                  </div>
                  <div className="flex justify-between text-gray-400">
                    <span>Run Cycle Duration:</span>
                    <span className="text-gray-200">{spec.runtimeHours} h ({spec.runtimeHours * 60}m)</span>
                  </div>
                  <div className="flex justify-between text-gray-400">
                    <span>Operating Window:</span>
                    <span className="text-gray-200">{spec.window}</span>
                  </div>
                  <div className="flex justify-between text-gray-400">
                    <span>Simultaneous Unit Cap:</span>
                    <span className="text-brand font-semibold">{spec.maxSimultaneous} max</span>
                  </div>
                  <div className="flex justify-between text-gray-400 pt-1 border-t border-panel-border/60">
                    <span>Fleet Daily Work:</span>
                    <span className="text-white font-semibold">{dailyEnergyKwh.toFixed(1)} kWh</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
