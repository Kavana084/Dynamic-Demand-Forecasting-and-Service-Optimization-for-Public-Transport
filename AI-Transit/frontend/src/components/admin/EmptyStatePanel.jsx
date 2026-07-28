import { AlertTriangle, Database, LineChart } from 'lucide-react';
import clsx from 'clsx';

const iconMap = {
  chart: LineChart,
  data: Database,
  warning: AlertTriangle,
};

export default function EmptyStatePanel({
  title,
  description,
  variant = 'data', // data | chart | warning
  actionLabel,
  onAction,
}) {
  const Icon = iconMap[variant] || Database;
  return (
    <div className="h-full w-full rounded-2xl border border-dashed border-border bg-background/60 p-8 flex flex-col items-center justify-center text-center">
      <div
        className={clsx(
          'w-12 h-12 rounded-2xl flex items-center justify-center mb-4 border shadow-st-sm',
          'bg-surface border-border'
        )}
      >
        <Icon className="w-6 h-6 text-primary" />
      </div>
      <h4 className="text-sm font-bold text-ink">{title}</h4>
      <p className="text-xs text-muted mt-2 max-w-sm">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-5 theme-button-secondary st-focusable py-2 px-3 text-xs"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

