import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingCardProps {
  label?: string;
  sublabel?: string;
  minHeight?: string;
}

export const LoadingCard: React.FC<LoadingCardProps> = ({
  label = 'Computing telemetry from backend...',
  sublabel = 'Executing neural feature pipeline & CP-SAT solver',
  minHeight = 'min-h-[260px]',
}) => {
  return (
    <div
      className={`rounded border border-panel-border bg-panel flex flex-col items-center justify-center p-8 text-center ${minHeight}`}
    >
      <div className="relative">
        <Loader2 className="w-8 h-8 text-brand animate-spin" />
        <div className="absolute inset-0 rounded-full blur-md bg-brand/20 -z-10"></div>
      </div>
      <p className="mt-4 text-xs font-mono font-medium text-white tracking-wide">{label}</p>
      <p className="mt-1 text-[11px] font-mono text-gray-500">{sublabel}</p>
    </div>
  );
};
