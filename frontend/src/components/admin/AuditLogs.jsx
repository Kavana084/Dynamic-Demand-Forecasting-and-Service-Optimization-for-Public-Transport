import { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import { Download, Search, Filter, X, ShieldCheck } from 'lucide-react';
import EmptyStatePanel from './EmptyStatePanel';

const MODULES = [
  'User Administration',
  'Demand Analytics',
  'Fleet Optimization',
  'Data Quality & Pipeline',
  'Overview & AI',
  'Passenger Portal',
];

const STATUSES = ['success', 'failed'];

function StatusPill({ value }) {
  const v = String(value || '').toLowerCase();
  const tone =
    v === 'success' ? 'success' :
      v === 'failed' ? 'danger' :
        'warning';
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold border',
        tone === 'success'
          ? 'bg-success/10 text-success border-success/25'
          : tone === 'danger'
            ? 'bg-danger/10 text-danger border-danger/25'
            : 'bg-warning/10 text-warning border-warning/25'
      )}
    >
      <span className="w-2 h-2 rounded-full bg-current" />
      {v ? v.toUpperCase() : 'UNKNOWN'}
    </span>
  );
}

function toCsv(rows) {
  const safe = (v) => `"${String(v ?? '').replaceAll('"', '""')}"`;
  const header = ['timestamp', 'user', 'action', 'module', 'status'];
  const lines = [
    header.join(','),
    ...rows.map((r) => header.map((k) => safe(r[k])).join(',')),
  ];
  return lines.join('\n');
}

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState(null);

  const [filters, setFilters] = useState(() => ({
    q: '',
    module: '',
    status: '',
    dateFrom: '',
    dateTo: '',
  }));

  const token = useMemo(
    () => localStorage.getItem('access_token') || localStorage.getItem('token'),
    []
  );

  const fetchLogs = async () => {
    setLoading(true);
    setError('');
    try {
      const qs = new URLSearchParams();
      if (filters.q) qs.set('q', filters.q);
      if (filters.module) qs.set('module', filters.module);
      if (filters.status) qs.set('status', filters.status);
      if (filters.dateFrom) qs.set('date_from', filters.dateFrom);
      if (filters.dateTo) qs.set('date_to', filters.dateTo);
      qs.set('limit', '500');

      const res = await fetch(`/api/admin/audit-logs?${qs.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => '');
        throw new Error(txt || 'Audit records are temporarily unavailable.');
      }

      const data = await res.json();
      setLogs(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message || 'Audit records are temporarily unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const hasFilters = !!(filters.q || filters.module || filters.status || filters.dateFrom || filters.dateTo);

  const exportCsv = () => {
    const csv = toCsv(logs);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `smart-transit-audit-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-3 text-muted">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-primary" />
        <span className="text-sm font-semibold">Loading audit records…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-danger/30 bg-danger/10 p-6 shadow-st-sm">
        <p className="font-semibold text-ink">Audit records are temporarily unavailable.</p>
        <p className="mt-1 text-sm text-muted">{error}</p>
        <button className="mt-4 theme-button-secondary st-focusable py-2 px-3 text-xs" onClick={fetchLogs}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted mb-1">
                <Search className="h-3.5 w-3.5" />
                <span>Search</span>
              </div>
              <input
                className="theme-input st-focusable h-10"
                value={filters.q}
                onChange={(e) => setFilters((p) => ({ ...p, q: e.target.value }))}
                placeholder="Action, user, module…"
              />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted mb-1">
                <Filter className="h-3.5 w-3.5" />
                <span>Module</span>
              </div>
              <select
                className="theme-input st-focusable h-10"
                value={filters.module}
                onChange={(e) => setFilters((p) => ({ ...p, module: e.target.value }))}
              >
                <option value="">All modules</option>
                {MODULES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted mb-1">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>Status</span>
              </div>
              <select
                className="theme-input st-focusable h-10"
                value={filters.status}
                onChange={(e) => setFilters((p) => ({ ...p, status: e.target.value }))}
              >
                <option value="">All</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s.toUpperCase()}</option>)}
              </select>
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted mb-1">
                <span>From</span>
              </div>
              <input
                type="date"
                className="theme-input st-focusable h-10"
                value={filters.dateFrom}
                onChange={(e) => setFilters((p) => ({ ...p, dateFrom: e.target.value }))}
              />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted mb-1">
                <span>To</span>
              </div>
              <input
                type="date"
                className="theme-input st-focusable h-10"
                value={filters.dateTo}
                onChange={(e) => setFilters((p) => ({ ...p, dateTo: e.target.value }))}
              />
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap justify-between">
            <div className="text-xs text-muted">
              {logs.length} record{logs.length !== 1 ? 's' : ''}{hasFilters ? ' (filtered)' : ''}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={exportCsv}
                className="theme-button-secondary st-focusable py-2 px-3 gap-2 text-xs"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </button>
              <button
                type="button"
                onClick={fetchLogs}
                className="theme-button-primary st-focusable py-2 px-3 gap-2 text-xs"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      {logs.length === 0 ? (
        <EmptyStatePanel
          variant="data"
          title={hasFilters ? 'No matching audit records' : 'No audit records yet'}
          description={hasFilters
            ? 'Try broadening filters or selecting a wider date range.'
            : 'Audit trails appear here when users are created, roles updated, scope changed, or other admin actions occur.'}
        />
      ) : (
        <div className="rounded-2xl border border-border bg-surface shadow-st-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-left">
              <thead className="bg-background text-muted text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3 font-semibold">Timestamp</th>
                  <th className="px-6 py-3 font-semibold">User</th>
                  <th className="px-6 py-3 font-semibold">Action</th>
                  <th className="px-6 py-3 font-semibold">Module</th>
                  <th className="px-6 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((l) => (
                  <tr
                    key={l.id}
                    className="hover:bg-background/60 cursor-pointer"
                    onClick={() => setSelected(l)}
                  >
                    <td className="px-6 py-3 text-sm text-ink whitespace-nowrap">
                      {l.timestamp ? new Date(l.timestamp).toLocaleString() : '—'}
                    </td>
                    <td className="px-6 py-3 text-sm font-semibold text-ink">{l.user || '—'}</td>
                    <td className="px-6 py-3 text-sm text-ink">{l.action || '—'}</td>
                    <td className="px-6 py-3 text-sm text-muted">{l.module || '—'}</td>
                    <td className="px-6 py-3"><StatusPill value={l.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail drawer */}
      {selected && (
        <div className="fixed inset-0 z-50">
          <div
            className="absolute inset-0 bg-black/35"
            onClick={() => setSelected(null)}
            aria-hidden="true"
          />
          <div className="absolute right-0 top-0 h-full w-full max-w-[520px] bg-surface border-l border-border shadow-st-md">
            <div className="px-6 py-5 border-b border-border flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-[11px] uppercase tracking-wider font-semibold text-muted">Audit detail</p>
                <h3 className="mt-1 text-base font-bold text-ink truncate">{selected.action || 'Audit event'}</h3>
                <p className="mt-1 text-xs text-muted">
                  {selected.timestamp ? new Date(selected.timestamp).toLocaleString() : '—'}
                </p>
              </div>
              <button
                type="button"
                className="st-focusable rounded-lg border border-border bg-background p-2 text-muted hover:text-ink"
                onClick={() => setSelected(null)}
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto h-[calc(100%-74px)]">
              <div className="rounded-2xl border border-border bg-background/50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs text-muted">Status</div>
                  <StatusPill value={selected.status} />
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-xs text-muted">Actor</div>
                    <div className="font-semibold text-ink">{selected.user || '—'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Module</div>
                    <div className="font-semibold text-ink">{selected.module || '—'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Target</div>
                    <div className="font-semibold text-ink">{selected.target_user || '—'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">IP address</div>
                    <div className="font-mono text-xs text-ink">{selected.ip_address || '—'}</div>
                  </div>
                </div>
              </div>

              {selected.detail ? (
                <div className="rounded-2xl border border-border bg-surface p-4">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted">Detail</div>
                  <p className="mt-2 text-sm text-ink">{selected.detail}</p>
                </div>
              ) : null}

              {(selected.previous_value || selected.new_value) ? (
                <div className="rounded-2xl border border-border bg-surface p-4">
                  <div className="text-xs font-semibold uppercase tracking-wider text-muted">Change</div>
                  <div className="mt-3 grid grid-cols-1 gap-3">
                    <div className="rounded-xl border border-border bg-background/60 p-3">
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">Previous</div>
                      <div className="mt-1 text-sm text-ink break-words">{selected.previous_value || '—'}</div>
                    </div>
                    <div className="rounded-xl border border-border bg-background/60 p-3">
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-muted">New</div>
                      <div className="mt-1 text-sm text-ink break-words">{selected.new_value || '—'}</div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
