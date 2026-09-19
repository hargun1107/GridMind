import React, { useState, useEffect } from 'react';
import {
  Database,
  Cpu,
  CheckCircle2,
  AlertCircle,
  FileText,
  Layers,
  ArrowRight,
  ShieldAlert,
  GitBranch,
  Terminal,
} from 'lucide-react';
import { api } from '@/api/client';
import { ModelMetricsResponse, ModelInfoResponse } from '@/api/types';
import { formatMw, formatPercent } from '@/lib/utils';
import { ErrorBanner } from '@/components/common/ErrorBanner';
import { LoadingCard } from '@/components/common/LoadingCard';

export const Model: React.FC = () => {
  const [metrics, setMetrics] = useState<ModelMetricsResponse | null>(null);
  const [info, setInfo] = useState<ModelInfoResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchModelData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [mRes, iRes] = await Promise.all([
        api.getModelMetrics(),
        api.getModelInfo(),
      ]);
      setMetrics(mRes);
      setInfo(iRes);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve model telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModelData();
  }, []);

  if (loading) {
    return <LoadingCard label="Loading Model Telemetry & Audit Logs..." sublabel="Reading serialized model metadata and evaluation artifacts" />;
  }

  if (error) {
    return <ErrorBanner message={error} onRetry={fetchModelData} isRetrying={loading} />;
  }

  if (!metrics || !info) {
    return null;
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Architecture Summary Banner */}
      <div className="p-5 rounded border border-panel-border bg-panel-subtle">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded bg-brand/10 border border-brand/30 text-brand mt-0.5 shrink-0">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold font-mono text-white tracking-wide">
              Engineering Architecture & Methodology
            </h2>
            <p className="text-xs text-gray-300 mt-1 leading-relaxed font-mono">
              GridMind combines machine-learning demand forecasting with constraint-based optimization for appliance scheduling.
              Machine learning predicts near-future electrical demand, while Google OR-Tools CP-SAT provides deterministic mathematical guarantees for circuit protection and peak shaving.
            </p>
          </div>
        </div>
      </div>

      {/* Model Verification Metrics */}
      <div>
        <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 mb-3">
          Verified Out-of-Sample Evaluation Metrics
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded border border-panel-border bg-panel p-4">
            <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Model Family</span>
            <div className="text-lg font-bold font-mono text-white mt-1.5">{metrics.model}</div>
            <p className="text-[10px] font-mono text-gray-500 mt-1">L2 Regularized Linear Estimator</p>
          </div>

          <div className="rounded border border-panel-border bg-panel p-4">
            <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Mean Absolute Error</span>
            <div className="text-lg font-bold font-mono text-brand mt-1.5">{formatMw(metrics.mae_mw)}</div>
            <p className="text-[10px] font-mono text-gray-500 mt-1">Average hourly forecast deviation</p>
          </div>

          <div className="rounded border border-panel-border bg-panel p-4">
            <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Root Mean Squared Error</span>
            <div className="text-lg font-bold font-mono text-white mt-1.5">{formatMw(metrics.rmse_mw)}</div>
            <p className="text-[10px] font-mono text-gray-500 mt-1">Penalizes large peak deviations</p>
          </div>

          <div className="rounded border border-panel-border bg-panel p-4">
            <span className="text-[10px] font-mono uppercase tracking-wider text-gray-400">Mean Absolute Percentage Error</span>
            <div className="text-lg font-bold font-mono text-brand mt-1.5">{formatPercent(metrics.mape_percent)}</div>
            <p className="text-[10px] font-mono text-gray-500 mt-1">Evaluated on {metrics.test_samples.toLocaleString()} test hours</p>
          </div>
        </div>
      </div>

      {/* Pipeline Technical Walkthrough */}
      <div className="rounded border border-panel-border bg-panel p-5">
        <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border">
          End-to-End Computational Pipeline
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
          <div className="p-3 rounded bg-panel-subtle border border-panel-border space-y-1.5">
            <div className="flex items-center justify-between text-brand text-xs font-mono font-semibold">
              <span>01. DATA INGESTION</span>
              <span className="text-[10px] text-gray-500">PJM Grid</span>
            </div>
            <p className="text-[11px] text-gray-400 font-mono">
              {info.data_source}
            </p>
          </div>

          <div className="p-3 rounded bg-panel-subtle border border-panel-border space-y-1.5">
            <div className="flex items-center justify-between text-brand text-xs font-mono font-semibold">
              <span>02. ML FORECASTING</span>
                <span className="text-[10px] text-gray-500">{info.feature_count} Features</span>
            </div>
            <p className="text-[11px] text-gray-400 font-mono">
              Generates 24-hour demand predictions using cyclical trigonometric calendar encodings, historical lags (1h, 24h, 168h), and rolling statistics.
            </p>
          </div>

          <div className="p-3 rounded bg-panel-subtle border border-panel-border space-y-1.5">
            <div className="flex items-center justify-between text-brand text-xs font-mono font-semibold">
              <span>03. DIGITAL TWIN</span>
              <span className="text-[10px] text-gray-500">Scaling</span>
            </div>
            <p className="text-[11px] text-gray-400 font-mono">
              Maps utility-scale MW down to residential kW preserving diurnal waking momentum while adding scheduled inflexible facility loads.
            </p>
          </div>

          <div className="p-3 rounded bg-panel-subtle border border-panel-border space-y-1.5">
            <div className="flex items-center justify-between text-brand text-xs font-mono font-semibold">
              <span>04. CP-SAT SOLVER</span>
              <span className="text-[10px] text-gray-500">OR-Tools</span>
            </div>
            <p className="text-[11px] text-gray-400 font-mono">
              Discretizes 24h into 48 half-hour slots and solves integer constraints to shave peaks below the 450 kW operating ceiling.
            </p>
          </div>
        </div>
      </div>

      {/* Feature Matrix & Data Provenance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Feature Matrix */}
        <div className="rounded border border-panel-border bg-panel p-5">
          <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border flex items-center justify-between">
            <span>Model Feature Schema</span>
            <span className="text-brand text-xs">{info.feature_count} Input Dimensions</span>
          </h3>

          <div className="mt-3 flex flex-wrap gap-1.5 max-h-[220px] overflow-y-auto p-1">
            {info.feature_names.map((name, i) => (
              <span
                key={i}
                className="px-2 py-1 rounded bg-panel-subtle border border-panel-border text-[11px] font-mono text-gray-300"
              >
                {name}
              </span>
            ))}
          </div>

          <div className="mt-4 pt-3 border-t border-panel-border text-[11px] font-mono text-gray-500 flex justify-between">
            <span>Training samples: {info.training_sample_count.toLocaleString()}</span>
            <span>Test samples: {info.test_sample_count.toLocaleString()}</span>
          </div>
        </div>

        {/* Data Provenance & Ethics Disclosures */}
        <div className="rounded border border-panel-border bg-panel p-5">
          <h3 className="text-xs font-semibold font-mono uppercase tracking-wider text-gray-400 pb-3 border-b border-panel-border">
            Data Provenance & Governance Disclosures
          </h3>

          <div className="mt-3 space-y-3 text-xs font-mono">
            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-brand font-semibold text-[11px]">Real External Electricity Data:</span>
              <p className="text-gray-300 mt-1 leading-relaxed">
                {info.data_source}
              </p>
            </div>

            <div className="p-3 rounded bg-panel-subtle border border-amber/30">
              <span className="text-amber font-semibold text-[11px]">Synthetic Development Weather Series:</span>
              <p className="text-gray-300 mt-1 leading-relaxed">
                {info.weather_data_provenance}
              </p>
            </div>

            <div className="p-3 rounded bg-panel-subtle border border-panel-border">
              <span className="text-gray-400 font-semibold text-[11px]">Synthetic Configurable Hostel Model:</span>
              <p className="text-gray-300 mt-1 leading-relaxed">
                Hostel electrical infrastructure parameters and appliance flexibility profiles are based on synthetic university engineering assumptions for reproducible hackathon benchmarking.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
