import { useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import EmptyStatePanel from './EmptyStatePanel';
import StickyFilterBar from './StickyFilterBar';

function isoToday() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

export default function OptimizationInsights() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [optimizations, setOptimizations] = useState([]);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [filters, setFilters] = useState(() => ({
    dateFrom: isoToday(),
    dateTo: isoToday(),
  }));

  const fetchOptimizations = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const params = new URLSearchParams();
      if (filters.dateFrom) params.set('date_from', filters.dateFrom);
      if (filters.dateTo) params.set('date_to', filters.dateTo);
      const qs = params.toString() ? `?${params.toString()}` : '';

      const res = await fetch(`/api/admin/optimization/results${qs}`, { headers });

      if (!res.ok) throw new Error('Fleet optimization data is temporarily unavailable.');
      const data = await res.json();
      setOptimizations(Array.isArray(data) ? data : []);
      setLastRefreshed(new Date());
    } catch (e) {
      setError(e.message || 'Fleet optimization data is temporarily unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOptimizations();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      fetchOptimizations();
    }, 250);
    return () => clearTimeout(t);
  }, [filters.dateFrom, filters.dateTo]);

  const lastRefreshedLabel = useMemo(() => {
    if (!lastRefreshed) return null;
    return lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, [lastRefreshed]);

  const handleExport = () => {
    const exportData = optimizations.map(row => ({
      route_short_name: row.route_short_name || row.route_name || row.route_id,
      predicted_demand: row.predicted_demand,
      allocated_buses: row.allocated_buses,
      utilization: row.utilization,
      unserved_demand: row.unserved_demand,
      timestamp: row.timestamp
    }));
    const payload = { filters, optimizations: exportData, generated_at: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fleet-optimization-${isoToday()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-3 text-muted">
        <RefreshCw className="w-5 h-5 animate-spin text-primary" />
        <span className="text-sm font-semibold">Loading fleet optimization data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-danger/30 bg-danger/10 p-6 shadow-st-sm">
        <p className="font-semibold text-ink">Fleet optimization data is temporarily unavailable.</p>
        <p className="mt-1 text-sm text-muted">{error}</p>
        <button className="mt-4 theme-button-secondary st-focusable py-2 px-3 text-xs" onClick={fetchOptimizations}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <StickyFilterBar
        filters={filters}
        onChange={setFilters}
        onRefresh={fetchOptimizations}
        onExport={handleExport}
        lastRefreshedLabel={lastRefreshedLabel}
      />

      <div className="rounded-2xl border border-border bg-surface shadow-st-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-border">
          <h3 className="text-sm font-bold text-ink">Optimization Results</h3>
          <p className="text-xs text-muted mt-0.5">Database records from OptimizationResult table.</p>
        </div>

        {optimizations.length === 0 ? (
          <div className="p-6">
            <EmptyStatePanel
              variant="data"
              title="No optimization data available"
              description="Run the optimization pipeline to populate the OptimizationResult table."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left">
              <thead className="bg-background text-muted text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3 font-semibold">Bus Route</th>
                  <th className="px-6 py-3 font-semibold text-right">Predicted Demand</th>
                  <th className="px-6 py-3 font-semibold text-right">Allocated Buses</th>
                  <th className="px-6 py-3 font-semibold text-right">Utilization</th>
                  <th className="px-6 py-3 font-semibold text-right">Unserved Demand</th>
                  <th className="px-6 py-3 font-semibold">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {optimizations.map((row) => (
                  <tr key={`${row.route_id}-${row.timestamp}`} className="hover:bg-background/60">
                    <td className="px-6 py-3 font-semibold text-ink">{row.route_short_name || row.route_name || row.route_id}</td>
                    <td className="px-6 py-3 text-right text-ink">{Number(row.predicted_demand || 0).toLocaleString()}</td>
                    <td className="px-6 py-3 text-right text-ink">{row.allocated_buses}</td>
                    <td className="px-6 py-3 text-right text-ink">{row.utilization != null ? `${row.utilization.toFixed(1)}%` : '—'}</td>
                    <td className="px-6 py-3 text-right text-ink">{Number(row.unserved_demand || 0).toLocaleString()}</td>
                    <td className="px-6 py-3 text-xs text-muted">
                      {row.timestamp ? new Date(row.timestamp).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
