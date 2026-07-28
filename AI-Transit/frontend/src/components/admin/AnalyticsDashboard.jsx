import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import clsx from 'clsx';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { BarChart3, RefreshCw, AlertCircle, Sparkles, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import StickyFilterBar from './StickyFilterBar';
import EmptyStatePanel from './EmptyStatePanel';

function isoToday() {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}
function isoLast7Days() {
  const d = new Date();
  d.setDate(d.getDate() - 7);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}


export default function AnalyticsDashboard() {
  const location = useLocation();
  const initialRoute = location.state?.route || 'All Routes';
  const [filters, setFilters] = useState(() => ({
    dateFrom: location.state?.filters?.dateFrom || '',
    dateTo: location.state?.filters?.dateTo || '',
    route: initialRoute,
  }));

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const [forecastHistory, setForecastHistory] = useState([]);
  const [summaryData, setSummaryData] = useState(null);
  const [distributionData, setDistributionData] = useState([]);
  const [peakHourData, setPeakHourData] = useState([]);
  const [routeRankingData, setRouteRankingData] = useState([]);

  const fetchData = async () => {
    setError('');
    try {
      const token = localStorage.getItem('access_token') || localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const params = new URLSearchParams();
      if (filters.dateFrom) params.set('date_from', filters.dateFrom);
      if (filters.dateTo) params.set('date_to', filters.dateTo);
      const qs = params.toString() ? `?${params.toString()}` : '';

      const [forecastRes, demandRes, distRes, peakRes, rankingRes] = await Promise.all([
        fetch(`/api/admin/forecast-history${qs}`, { headers }),
        fetch(`/api/admin/analytics/demand${qs}`, { headers }),
        fetch(`/api/admin/analytics/demand-distribution${qs}`, { headers }),
        fetch(`/api/admin/analytics/peak-hour${qs}`, { headers }),
        fetch(`/api/admin/analytics/route-ranking${qs}`, { headers })
      ]);

      if (!forecastRes.ok) throw new Error('Forecast history unavailable.');
      const forecast = await forecastRes.json();
      setForecastHistory(Array.isArray(forecast) ? forecast : []);

      if (demandRes.ok) {
        const demand = await demandRes.json();
        setSummaryData(demand.summary);
      }

      if (distRes.ok) {
        setDistributionData(await distRes.json());
      }

      if (peakRes.ok) {
        setPeakHourData(await peakRes.json());
      }

      if (rankingRes.ok) {
        setRouteRankingData(await rankingRes.json());
      }

      setLastRefreshed(new Date());
    } catch (e) {
      setError(e.message || 'Demand analytics are temporarily unavailable.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      setLoading(true);
      fetchData();
    }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.dateFrom, filters.dateTo]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData();
    }, 30000);
    return () => clearInterval(interval);
  }, [filters.dateFrom, filters.dateTo]);

  const lastRefreshedLabel = useMemo(() => {
    if (!lastRefreshed) return null;
    return lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }, [lastRefreshed]);

  const routeOptions = useMemo(() => {
    const map = new Map();
    forecastHistory.forEach((f) => {
      if (f.route_id) {
        const displayName = f.route_short_name || f.route_id;
        map.set(f.route_id, displayName);
      }
    });
    return ['All Routes', ...Array.from(map.values()).sort()];
  }, [forecastHistory]);

  const filteredForecast = useMemo(() => {
    if (filters.route === 'All Routes') return forecastHistory;
    return forecastHistory.filter((f) => {
      const displayName = f.route_short_name || f.route_id;
      return displayName === filters.route;
    });
  }, [forecastHistory, filters.route]);

  const historicalSeries = useMemo(() => {
    return filteredForecast.map((f) => {
      const t = f.target_timestamp ? new Date(f.target_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
      const predicted = Number(f.predicted_passengers || 0);
      const conf = typeof f.confidence_score === 'number' ? f.confidence_score : null;
      const band = conf == null ? null : predicted * (1 - conf) * 0.25;
      return {
        t,
        predicted,
        lower: band == null ? null : Math.max(0, predicted - band),
        upper: band == null ? null : predicted + band,
      };
    });
  }, [filteredForecast]);

  const handleExport = () => {
    let csv = 'Route,Predicted Demand,Allocated Buses,Utilization,Occupancy,Crowd Level,Demand Trend,Last Updated\n';
    routeRankingData.forEach(r => {
      csv += `${r.route_short_name},${r.predicted_demand},${r.allocated_buses},${r.utilization}%,${r.occupancy}%,${r.crowd_level},${r.demand_trend},${r.last_updated}\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `demand-analytics-${isoToday()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getCrowdBadgeColor = (level) => {
    if (level.includes('Low')) return 'bg-green-100 text-green-800 border-green-200';
    if (level.includes('Moderate')) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    if (level.includes('Busy')) return 'bg-orange-100 text-orange-800 border-orange-200';
    if (level.includes('Crowded')) return 'bg-red-100 text-red-800 border-red-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getAllocationBadgeColor = (status) => {
    if (status === 'Optimal') return 'bg-blue-100 text-blue-800 border-blue-200';
    if (status === 'Over Allocated') return 'bg-purple-100 text-purple-800 border-purple-200';
    if (status === 'Under Allocated') return 'bg-pink-100 text-pink-800 border-pink-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  if (loading && !summaryData) {
    return (
      <div className="space-y-6 animate-pulse">
         <div className="h-16 bg-surface border border-border rounded-2xl w-full"></div>
         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(6)].map((_, i) => <div key={i} className="h-24 bg-surface border border-border rounded-xl w-full"></div>)}
         </div>
         <div className="h-80 bg-surface border border-border rounded-2xl w-full"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-danger/30 bg-danger/10 p-6 text-danger shadow-st-sm">
        <p className="font-semibold text-ink">Demand analytics are temporarily unavailable.</p>
        <p className="mt-1 text-sm text-muted">{error}</p>
        <button className="mt-4 theme-button-secondary st-focusable py-2 px-3 text-xs" onClick={fetchData}>
          Retry
        </button>
      </div>
    );
  }

  const generatedDateLabel = summaryData?.last_forecast_time 
    ? new Date(summaryData.last_forecast_time).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true })
    : 'Unknown';

  return (
    <div className="space-y-6">
      <StickyFilterBar
        filters={filters}
        onChange={(next) => setFilters((p) => ({ ...p, ...next }))}
        onRefresh={fetchData}
        onExport={handleExport}
        lastRefreshedLabel={lastRefreshedLabel}
      />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between px-2">
        <div className="flex items-center gap-2 flex-wrap">
          <BarChart3 className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-bold text-ink">Demand Analytics Dashboard</h3>
          <span className="ml-2 text-sm font-medium text-muted bg-surface px-2 py-1 rounded-md border border-border">
            Data Window: {filters.dateFrom || 'Last 7 Days'} &rarr; {filters.dateTo || 'Today'}
          </span>
        </div>
      </div>

      {/* 6 Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider">Forecast Records</p>
          <p className="mt-2 text-2xl font-extrabold text-ink">{summaryData?.forecast_records?.toLocaleString() || 0}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider">Active Routes</p>
          <p className="mt-2 text-2xl font-extrabold text-ink">{summaryData?.active_routes?.toLocaleString() || 0}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider">Total Predicted Passengers</p>
          <p className="mt-2 text-2xl font-extrabold text-ink">{summaryData?.total_predicted_passengers?.toLocaleString() || 0}</p>
        </div>
        <div className="rounded-xl border border-border bg-surface shadow-st-sm p-5 flex flex-col justify-between hover:shadow-md transition-shadow">
          <p className="text-xs font-semibold text-muted uppercase tracking-wider">Forecast Generated</p>
          <p className="mt-2 text-lg font-bold text-ink">{generatedDateLabel}</p>
        </div>
      </div>

      {/* Route Filter */}
      <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-5 flex items-center">
          <div className="flex-1">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted mb-2">Search Route</div>
            <input 
              list="routes-datalist" 
              className="theme-input st-focusable h-10 w-full max-w-sm"
              value={filters.route}
              onChange={(e) => setFilters((p) => ({ ...p, route: e.target.value }))}
              placeholder="Type to search routes..."
            />
            <datalist id="routes-datalist">
              {routeOptions.map((r) => <option key={r} value={r} />)}
            </datalist>
          </div>
      </div>

      {/* Forecast Trend Chart */}
      <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-6">
        <h3 className="text-sm font-bold text-ink mb-4">Forecast Demand vs Time</h3>
        <div className="h-[320px]">
          {historicalSeries.length === 0 ? (
            <EmptyStatePanel variant="data" title="No forecast data available" description="ForecastHistory table is empty for the selected route/date." />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historicalSeries}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--st-divider)" />
                <XAxis dataKey="t" tickLine={false} axisLine={false} tick={{ fill: 'var(--st-muted-2)', fontSize: 10 }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--st-muted-2)', fontSize: 10 }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid var(--st-border)', background: 'var(--st-surface)', color: 'var(--st-ink)', boxShadow: 'var(--st-shadow-sm)' }} />
                <Area type="monotone" dataKey="upper" stroke="transparent" fill="color-mix(in srgb, var(--st-primary) 18%, transparent)" />
                <Area type="monotone" dataKey="lower" stroke="transparent" fill="var(--st-surface)" />
                <Line type="monotone" dataKey="predicted" stroke="var(--st-primary)" strokeWidth={2.6} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Distribution and Peak Hour Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-6">
          <h3 className="text-sm font-bold text-ink mb-4">Demand Distribution by Route</h3>
          <div className="h-[280px]">
            {distributionData.length === 0 ? (
              <EmptyStatePanel variant="data" title="No data" description="No distribution data found." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distributionData} margin={{ left: -20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--st-divider)" />
                  <XAxis dataKey="route_short_name" tickLine={false} axisLine={false} tick={{ fill: 'var(--st-muted-2)', fontSize: 10 }} angle={-45} textAnchor="end" />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--st-muted-2)', fontSize: 10 }} />
                  <Tooltip cursor={{ fill: 'var(--st-divider)' }} contentStyle={{ borderRadius: 12, border: '1px solid var(--st-border)' }} />
                  <Bar dataKey="predicted_passengers" fill="var(--st-primary)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-6">
          <h3 className="text-sm font-bold text-ink mb-4">Peak Hour Analysis</h3>
          <div className="h-[280px]">
            {peakHourData.length === 0 ? (
              <EmptyStatePanel variant="data" title="No data" description="No peak hour data found." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={peakHourData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--st-divider)" />
                  <XAxis dataKey="hour" tickLine={false} axisLine={false} tick={{ fill: 'var(--st-muted-2)', fontSize: 10 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fill: 'var(--st-muted-2)', fontSize: 10 }} />
                  <Tooltip cursor={{ fill: 'var(--st-divider)' }} contentStyle={{ borderRadius: 12, border: '1px solid var(--st-border)' }} />
                  <Bar dataKey="predicted_passengers" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      

    </div>
  );
}
