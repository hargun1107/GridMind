import React from 'react';
import { AlertTriangle, RefreshCw, Terminal } from 'lucide-react';

interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'Backend Connection Error',
  message,
  onRetry,
  isRetrying,
}) => {
  return (
    <div className="rounded-lg border border-danger/40 bg-danger-dim p-4 my-4">
      <div className="flex items-start gap-3.5">
        <div className="p-2 rounded bg-danger/20 border border-danger/40 text-danger shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-white font-mono tracking-wide flex items-center gap-2">
            <span>{title}</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-danger/30 text-red-200 border border-danger/40 uppercase">
              ERR_DISCONNECTED
            </span>
          </h3>
          <p className="text-xs text-gray-300 mt-1 font-mono leading-relaxed">
            {message}
          </p>

          <div className="mt-3 p-2 rounded bg-black/40 border border-panel-border text-[11px] font-mono text-gray-400 flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-brand" />
            <span>Ensure the backend server is running:</span>
            <code className="text-brand bg-brand/10 px-1.5 py-0.5 rounded">
              .venv\Scripts\uvicorn backend.app.main:app --port 8000
            </code>
          </div>

          {onRetry && (
            <div className="mt-3">
              <button
                onClick={onRetry}
                disabled={isRetrying}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded bg-panel-light hover:bg-panel-border border border-panel-border text-xs font-mono font-medium text-white transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin text-brand' : ''}`} />
                <span>Retry Connection</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
