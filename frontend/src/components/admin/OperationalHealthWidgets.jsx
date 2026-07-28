import { Activity, Database, ShieldCheck, AlertTriangle, Clock } from 'lucide-react';
import clsx from 'clsx';

function StatusPill({ status, label }) {
  const normalized = (status || '').toLowerCase();
  // Three colour slots:
  //   green  → service operating normally
  //   yellow → degraded / partial / warning — needs attention but not failing
  //   grey   → unknown / empty / no-data — neutral: no records yet, not an error
  //   red    → critical / any other explicit failure
  const color =
    normalized === 'healthy' || normalized === 'online'
      ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/25'
      : normalized === 'warning' || normalized === 'degraded' || normalized === 'partial'
        ? 'bg-amber-500/10 text-amber-500 border-amber-500/25'
        : normalized === 'unknown' || normalized === 'empty' || normalized === 'no-data'
          ? 'bg-slate-500/10 text-slate-400 border-slate-500/25'
          : 'bg-red-500/10 text-red-500 border-red-500/25';
  return (
    <span className={clsx('inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold border', color)}>
      <span className="w-2 h-2 rounded-full bg-current" />
      {label || status}
    </span>
  );
}

function Tile({ icon: Icon, label, value, sub, status }) {
  return (
    <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
          <p className="mt-2 text-2xl font-extrabold text-ink leading-none">{value}</p>
          {sub ? <p className="mt-2 text-xs text-muted">{sub}</p> : null}
        </div>
        <div
          className="w-10 h-10 rounded-2xl flex items-center justify-center border border-border bg-background"
          aria-hidden="true"
        >
          <Icon className="w-5 h-5 text-primary" />
        </div>
      </div>
      {status ? <div className="mt-4"><StatusPill status={status} /></div> : null}
    </div>
  );
}

export default function OperationalHealthWidgets({
  pipelineStatus,
  dataQualityScore,
  systemHealth,
  lastRunLabel,
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
      <Tile
        icon={Activity}
        label="Pipeline health"
        value={pipelineStatus?.label || '—'}
        sub={lastRunLabel ? `Last run: ${lastRunLabel}` : '—'}
        status={pipelineStatus?.status}
      />
      <Tile
        icon={Database}
        label="Data quality score"
        value={dataQualityScore != null ? `${Math.round(dataQualityScore)}%` : '—'}
        sub="Completeness, accuracy, freshness"
        status={dataQualityScore != null ? (dataQualityScore >= 90 ? 'Healthy' : dataQualityScore >= 75 ? 'Warning' : 'Critical') : null}
      />
      <Tile
        icon={ShieldCheck}
        label="Service health"
        value={systemHealth?.statusLabel || '—'}
        sub={systemHealth?.message || '—'}
        status={systemHealth?.status}
      />
      <Tile
        icon={Clock}
        label="Operational window"
        value={systemHealth?.windowLabel || 'Today'}
        sub="Filters apply across modules"
      />
    </div>
  );
}

