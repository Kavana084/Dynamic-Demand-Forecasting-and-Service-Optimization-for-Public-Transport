import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  HardDrive,
  Network,
  Server,
  Waypoints,
} from 'lucide-react';
import { getAlerts, getGraphDiagnostics, getSystemMetrics } from '../../api/client';

function MetricTile({ icon: Icon, label, value, hint }) {
  return (
    <div className="theme-kpi-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="mt-3 text-3xl font-bold text-slate-900">{value}</p>
          {hint ? <p className="mt-2 text-sm text-slate-500">{hint}</p> : null}
        </div>
        <div className="theme-icon-chip">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function SystemMonitoring() {
  const [metrics, setMetrics] = useState(null);
  const [graph, setGraph] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const [metricsData, graphData, alertsData] = await Promise.all([
          getSystemMetrics(),
          getGraphDiagnostics(),
          getAlerts(),
        ]);
        if (!active) return;
        setMetrics(metricsData);
        setGraph(graphData);
        setAlerts(Array.isArray(alertsData) ? alertsData : []);
        setError('');
      } catch (err) {
        if (!active) return;
        setError(err.message || 'Unable to load system monitoring data.');
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    load();
    const interval = setInterval(load, 30000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const backendStatus = useMemo(() => {
    if (error) return 'Degraded';
    if (metrics && graph) return 'Online';
    return 'Checking';
  }, [error, metrics, graph]);

  if (loading) {
    return <div className="text-sm text-slate-500">Loading system monitoring...</div>;
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <MetricTile
          icon={Waypoints}
          label="Node Count"
          value={graph?.total_nodes ?? 0}
          hint="Routing graph nodes"
        />
        <MetricTile
          icon={Network}
          label="Edge Count"
          value={graph?.total_edges ?? 0}
          hint="Routing graph edges"
        />
        <MetricTile
          icon={Server}
          label="Backend Status"
          value={backendStatus}
          hint="Based on live API reachability"
        />
        <MetricTile
          icon={AlertTriangle}
          label="Active Alerts"
          value={alerts.length}
          hint="Current alert feed size"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="theme-section-card">
          <h3 className="text-lg font-semibold text-slate-900">Routing Graph Statistics</h3>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Disconnected Nodes</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{graph?.disconnected_node_count ?? 0}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Self Loops</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{graph?.self_loop_count ?? 0}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">SCC Count</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{graph?.scc_count ?? 0}</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Cycle Components</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{graph?.sccs_with_cycles ?? 0}</p>
            </div>
          </div>
        </section>

        <section className="theme-section-card">
          <h3 className="text-lg font-semibold text-slate-900">Cache Statistics</h3>
          <div className="mt-6 rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5">
            <div className="flex items-center gap-3">
              <HardDrive className="h-5 w-5 text-slate-500" />
              <div>
                <p className="text-sm font-medium text-slate-900">Cache metrics unavailable</p>
                <p className="mt-1 text-sm text-slate-500">
                  No cache-statistics field is exposed by the current monitoring endpoints.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">CPU Usage</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{metrics?.cpu_usage?.toFixed?.(1) ?? 0}%</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Memory Usage</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{metrics?.memory_usage?.toFixed?.(1) ?? 0}%</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Disk Usage</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{metrics?.disk_usage?.toFixed?.(1) ?? 0}%</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">Active Threads</p>
              <p className="mt-2 text-2xl font-bold text-slate-900">{metrics?.active_threads ?? 0}</p>
            </div>
          </div>
        </section>
      </div>

      <section className="theme-section-card">
        <div className="flex items-center gap-3">
          <Activity className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold text-slate-900">Active Alerts</h3>
        </div>
        <div className="mt-5 space-y-3">
          {alerts.map((alert, index) => (
            <div key={`${alert.title}-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{alert.title}</p>
                  <p className="mt-1 text-sm text-slate-500">{alert.message}</p>
                </div>
                <div className="shrink-0 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  {alert.severity}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
