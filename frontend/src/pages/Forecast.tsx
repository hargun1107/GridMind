import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Database,
  BarChart3,
  Calendar,
  Layers,
  CheckCircle2,
  FileText,
  Clock,
  Zap,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { api } from '@/api/client';
import { ForecastResponse, ModelMetricsResponse, ModelInfoResponse } from '@/api/types';
import { formatMw, formatPercent } from '@/lib/utils';
import { ErrorBanner } from '@/components/common/ErrorBanner';
import { LoadingCard } from '@/components/common/LoadingCard';

export const Forecast: React.FC = () => {
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfoResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchForecastData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [forecastRes, metricsRes, infoRes] = await Promise.all([
        api.getForecast(),
        api.getModelMetrics(),
        api.getModelInfo(),
      ]);
      setForecast(forecastRes);
      setMetrics(metricsRes);
      setModelInfo(infoRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load forecasting telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchForecastData();
  }, []);

  if (loading) {
    return <LoadingCard label="Loading Demand Forecast & ML Metrics..." sublabel="Fetching 24h recursive autoregression series from FastAPI" />;
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={fetchForecastData} isRetrying={loading} />;
  }

  if (!forecast || !metrics || !modelInfo) {
    return null;
  }

  const chartData = forecast.forecast.map((pt) => {
    // Format timestamp 'YYYY-MM-DD HH:MM:SS' -> 'HH:00'
    const timeOnly = pt.timestamp.includes(' ') ? pt.timestamp.split(' ')[1].slice(0, 5) : pt.timestamp;
    return {
      timestamp: timeOnly,
      fullTime: pt.timestamp,
      loadMw: pt.predicted_load_mw,
    };
  });

  const peakMw = Math.max(...forecast.forecast.map((p) => p.predicted_load_mw));
  const minMw = Math.min(...forecast.forecast.map((p) => p.predicted_load_mw));

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner Notice */}
      <div className="p-4 rounded border border-panel-border bg-panel-subtle flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-brand/10 border border-brand/30 text-brand">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold font-mono text-white tracking-wide">
              Utility-Scale Transmission Grid Forecast ({forecast.horizon_hours}-Hour Horizon)
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Model: <span className="text-brand font-mono">{metrics.model}</span> | Out-of-sample MAPE:{' '}
              <span className="text-brand font-mono font-medium">{formatPercent(metrics.mape_percent)}</span>
            </p>
          </div>
        </div>
        <div className="text-xs font-mono text-gray-400 flex items-center gap-2">
          <span>Resolution: 1 Hour</span>
          <span className="text-gray-600">•</span>
          <span>Horizon: {forecast.forecast.length} Points</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded border border-panel-border bg-panel p-4">
          <span className="text-[11px] font-mono uppercase tracking-wider text-gray-400">Forecasted Grid Peak</span>
          <div className="text-2xl font-bold font-mono text-brand mt-2">{formatMw(peakMw)}</div>
          <p className="text-[11px] font-mono text-gray-400 mt-1">Regional transmission maximum</p>
        </div>

        <div className="rounded border border-panel-border bg-panel p-4">
          <span className="text-[11px] font-mono uppercase tracking-wider text-gray-400">Forecasted Grid Valley</span>
          <div className="text-2xl font-bold font-mono text-white mt-2">{formatMw(minMw)}</div>
          <p className="text-[11px] font-mono text-gray-400 mt-1">Night dormant base load</p>
        </div>

        <div className="rounded border border-panel-border bg-panel p-4">
          <span className="text-[11px] font-mono uppercase tracking-wider text-gray-400">Mean Absolute Error</span>
          <div className="text-2xl font-bold font-mono text-white mt-2">{formatMw(metrics.mae_mw)}</div>
          <p className="text-[11px] font-mono text-gray-400 mt-1">RMSE: {formatMw(metrics.rmse_mw)}</p>
        </div>

        <div className="rounded border border-panel-border bg-panel p-4">
          <span className="text-[11px] font-mono uppercase tracking-wider text-gray-400">Evaluation Accuracy</span>
          <div className="text-2xl font-bold font-mono text-brand mt-2">{formatPercent(metrics.mape_percent)}</div>
          <p className="text-[11px] font-mono text-gray-400 mt-1">{metrics.test_samples.toLocaleString()} held-out test hours</p>
        </div>
      </div>

      {/* Main Forecast Chart */}
      <div className="rounded border border-panel-border bg-panel p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-2 border-b border-panel-border gap-2">
          <div>
            <h3 className="text-sm font-semibold font-mono text-white tracking-wide flex items-center gap-2">
              <span>Forecasted Transmission Demand ({forecast.unit})</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand/10 text-brand border border-brand/30">
                {modelInfo.data_source}
              </span>
            </h3>
            <p className="text-xs text-gray-400 mt-1">
              Dynamic 24-hour demand trajectory generated via multi-step autoregression.
            </p>
          </div>
          <div className="text-xs font-mono text-gray-400 flex items-center gap-2">
            <span className="w-3 h-1 bg-brand inline-block shadow-[0_0_8px_#10E575]"></span>
            <span>Predicted Load ({forecast.unit})</span>
          </div>
        </div>

        <div className="h-[360px] w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="forecastGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10E575" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10E575" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F2428" vertical={false} />
              <XAxis
                dataKey="timestamp"
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
                unit={` ${forecast.unit}`}
                fontFamily="JetBrains Mono"
                domain={['auto', 'auto']}
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
                formatter={(val: number) => [`${val.toFixed(2)} ${forecast.unit}`, 'Predicted Demand']}
                labelStyle={{ color: '#9CA3AF' }}
              />
              <Area
                type="monotone"
                dataKey="loadMw"
                stroke="#10E575"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#forecastGlow)"
                activeDot={{ r: 5, fill: '#10E575', stroke: '#0B0D0F', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model Information Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded border border-panel-border bg-panel p-5 lg:col-span-2">
          <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border flex items-center justify-between">
            <span>Forecast Model Architecture</span>
            <span className="text-brand text-[11px] lowercase font-normal">{modelInfo.model_type}</span>
          </h3>
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-500 text-[10px] uppercase">Model Algorithm</span>
              <p className="text-white font-medium mt-1">{modelInfo.model_name}</p>
            </div>
            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-500 text-[10px] uppercase">Input Feature Count</span>
              <p className="text-brand font-medium mt-1">{modelInfo.feature_count} Features</p>
            </div>
            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-500 text-[10px] uppercase">Training Samples</span>
              <p className="text-white font-medium mt-1">{modelInfo.training_sample_count.toLocaleString()} Hours</p>
            </div>
            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-500 text-[10px] uppercase">Test Evaluation Samples</span>
              <p className="text-white font-medium mt-1">{modelInfo.test_sample_count.toLocaleString()} Hours</p>
            </div>
            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-500 text-[10px] uppercase">Mean Absolute Error</span>
              <p className="text-white font-medium mt-1">{formatMw(metrics.mae_mw)}</p>
            </div>
            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-500 text-[10px] uppercase">MAPE Error</span>
              <p className="text-brand font-medium mt-1">{formatPercent(metrics.mape_percent)}</p>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-panel-border text-xs text-gray-400 font-mono">
            <p className="text-gray-300 font-semibold mb-1">Feature Engineering Pipeline:</p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {modelInfo.feature_names.map((feat) => (
                <span
                  key={feat}
                  className="px-2 py-0.5 rounded bg-panel-subtle border border-panel-border text-[10px] text-gray-300 font-mono"
                >
                  {feat}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Data Source & Provenance Disclosure */}
        <div className="rounded border border-panel-border bg-panel p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border">
              Data Provenance & Disclosure
            </h3>
            <div className="mt-4 space-y-3 text-xs font-mono">
              <div>
                <span className="text-gray-500 text-[10px] uppercase">Electricity Grid Source:</span>
                <p className="text-gray-200 mt-0.5">{modelInfo.data_source}</p>
              </div>
              <div className="pt-2 border-t border-panel-border/60">
                <span className="text-gray-500 text-[10px] uppercase">Weather Series Note:</span>
                <p className="text-amber mt-0.5">{modelInfo.weather_data_provenance}</p>
              </div>
              <div className="pt-2 border-t border-panel-border/60">
                <span className="text-gray-500 text-[10px] uppercase">Historical Period:</span>
                <p className="text-gray-300 mt-0.5">
                  {modelInfo.training_period.start.slice(0, 10)} → {modelInfo.test_period.end.slice(0, 10)}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 p-2.5 rounded bg-panel-subtle border border-panel-border text-[11px] font-mono text-gray-400">
            ✓ Full zero-lookahead autoregressive testing verified.
          </div>
        </div>
      </div>
    </div>
  );
};
