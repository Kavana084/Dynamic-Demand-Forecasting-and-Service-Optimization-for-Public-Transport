import { useEffect, useState, useRef } from 'react';
import {
  Users,
  Route,
  TrendingUp,
  Bus,
  RefreshCw,
  Search,
  ArrowRight,
  Navigation,
  Activity,
  AlertTriangle
} from 'lucide-react';
import clsx from 'clsx';
import client, { planTrip, getStops } from '../../api/client';

export default function AdminDashboard() {
  const [stops, setStops] = useState([]);
  const [stopsLoading, setStopsLoading] = useState(true);
  const [journeyFormData, setJourneyFormData] = useState({ source_id: '', destination_id: '' });
  const [journeyResult, setJourneyResult] = useState(null);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [journeyError, setJourneyError] = useState('');
  const abortControllerRef = useRef(null);

  const [dashboardData, setDashboardData] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);

  const loadDashboard = async () => {
    try {
      const response = await client.get('/api/admin/dashboard/bootstrap');
      setDashboardData(response.sections);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setDashboardLoading(false);
    }
  };

  const loadStops = async () => {
    setStopsLoading(true);
    try {
      const response = await getStops();
      let rawStops = [];
      if (Array.isArray(response)) rawStops = response;
      else if (Array.isArray(response?.stops)) rawStops = response.stops;
      else if (Array.isArray(response?.data)) rawStops = response.data;
      else if (Array.isArray(response?.results)) rawStops = response.results;
      
      const normalizedStops = Array.from(
        new Map(
          rawStops
            .map((stop) => {
              const stopId = String(stop?.stop_id ?? stop?.id ?? '').trim();
              const stopName = String(stop?.stop_name ?? stop?.name ?? stop?.stop_id ?? 'Unknown stop').trim();
              if (!stopId) return null;
              return [stopId, { ...stop, stop_id: stopId, stop_name: stopName }];
            })
            .filter(Boolean)
        ).values()
      ).sort((a, b) => a.stop_name.localeCompare(b.stop_name));

      setStops(normalizedStops);
    } catch (err) {
      console.error('Failed to load stops', err);
    } finally {
      setStopsLoading(false);
    }
  };

  useEffect(() => {
    loadStops();
    loadDashboard();
  }, []);

  const handlePlanJourney = async (e) => {
    e.preventDefault();
    if (!journeyFormData.source_id || !journeyFormData.destination_id || journeyFormData.source_id === journeyFormData.destination_id) return;
    
    setJourneyLoading(true);
    setJourneyError('');
    setJourneyResult(null);
    
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    
    try {
      const data = await planTrip(journeyFormData, abortControllerRef.current.signal);
      if (data.success === false) { 
        setJourneyError(data.message || 'No route found'); 
        return; 
      }
      setJourneyResult(data);
      // Refresh dashboard to update Allocated Buses card with new optimization results
      loadDashboard();
    } catch (err) {
      if (err.name === 'AbortError') return;
      if (err.status === 404) setJourneyError(`Route not found: ${err.message}`);
      else setJourneyError(`Failed to plan trip: ${err.message}`);
    } finally {
      setJourneyLoading(false);
    }
  };

  const renderJourneyDetails = () => {
    if (!journeyResult) return null;
    
    // Display actual route names from the backend instead of internal route IDs
    const routeId = journeyResult.route_id || 'Unknown Route';
    
    const sourceStopName = stops.find(s => String(s.stop_id) === journeyFormData.source_id)?.stop_name || '';
    const destStopName = stops.find(s => String(s.stop_id) === journeyFormData.destination_id)?.stop_name || '';

    // Crowd Level Card details
    const crowdLevel = journeyResult.crowd_level || 'Unknown';
    const predictedDemand = journeyResult.predicted_demand || 0;
    const occupancyPercent = journeyResult.occupancy_percent || 0;
    const peakStatus = journeyResult.context?.peak_status || journeyResult.peak_status || 'Unknown';
    
    // Fleet Optimization Card details
    const requiredBuses = journeyResult.required_buses || 0;
    const availableBuses = journeyResult.allocated_buses || journeyResult.current_fleet || 0;
    const busCapacity = journeyResult.bus_capacity || 50;
    
    // Fix allocated buses calculation: ceiling of predicted demand / bus capacity
    let calculatedAllocatedBuses = Math.ceil(predictedDemand / busCapacity);
    let optimizationStatus = 'Optimal';
    
    if (availableBuses < requiredBuses) {
      calculatedAllocatedBuses = availableBuses;
      optimizationStatus = 'Limited Availability';
    } else if (calculatedAllocatedBuses < requiredBuses) {
      // If we need more buses than the raw demand/capacity dictates (e.g. for frequency)
      // but we have them available, we allocate the required amount.
       calculatedAllocatedBuses = requiredBuses;
    }

    if (optimizationStatus === 'Optimal' && calculatedAllocatedBuses > availableBuses) {
        optimizationStatus = `Allocate ${calculatedAllocatedBuses - availableBuses} more buses`;
    }

    return (
      <div className="mt-6 space-y-6">
        {/* Route Analysis Summary */}
        <div className="rounded-2xl border border-border bg-surface shadow-st-sm p-6">
          <div className="flex items-center gap-2 mb-4 text-primary">
            <Navigation className="w-5 h-5" />
            <h4 className="text-sm font-bold text-ink">Route Analysis Summary</h4>
          </div>
          
          <div>
            <h5 className="text-lg font-bold text-ink mb-1">{routeId}</h5>
            <div className="flex items-center gap-2 text-sm text-muted">
              <span>{sourceStopName}</span>
              <ArrowRight className="w-4 h-4" />
              <span>{destStopName}</span>
            </div>
          </div>
        </div>

        {/* Analytics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Crowd Level */}
          <div className="rounded-2xl border-2 border-emerald-500/30 bg-emerald-50 shadow-md p-6">
            <div className="flex items-center gap-2 mb-4 text-emerald-700">
              <Users className="w-6 h-6" />
              <h4 className="text-base font-extrabold">Crowd Level</h4>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b border-emerald-200 pb-2">
                <span className="text-sm font-semibold text-emerald-800">Crowd Level</span>
                <span className="text-lg font-bold text-emerald-900">{crowdLevel}</span>
              </div>
              <div className="flex justify-between items-center border-b border-emerald-200 pb-2">
                <span className="text-sm font-semibold text-emerald-800">Predicted Passenger Demand</span>
                <span className="text-lg font-bold text-emerald-900">{predictedDemand}</span>
              </div>
              <div className="flex justify-between items-center border-b border-emerald-200 pb-2">
                <span className="text-sm font-semibold text-emerald-800">Occupancy Percentage</span>
                <span className="text-lg font-bold text-emerald-900">{occupancyPercent}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-semibold text-emerald-800">Peak Status</span>
                <span className="text-lg font-bold text-emerald-900">{peakStatus}</span>
              </div>
            </div>
          </div>

          {/* Fleet Optimization */}
          <div className="rounded-2xl border-2 border-indigo-500/30 bg-indigo-50 shadow-md p-6">
            <div className="flex items-center gap-2 mb-4 text-indigo-700">
              <Bus className="w-6 h-6" />
              <h4 className="text-base font-extrabold">Fleet Optimization</h4>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b border-indigo-200 pb-2">
                <span className="text-sm font-semibold text-indigo-800">Required Buses</span>
                <span className="text-lg font-bold text-indigo-900">{requiredBuses}</span>
              </div>
              <div className="flex justify-between items-center border-b border-indigo-200 pb-2">
                <span className="text-sm font-semibold text-indigo-800">Allocated Buses</span>
                <span className="text-lg font-bold text-indigo-900">{calculatedAllocatedBuses}</span>
              </div>
              <div className="flex justify-between items-center border-b border-indigo-200 pb-2">
                <span className="text-sm font-semibold text-indigo-800">Available Buses</span>
                <span className="text-lg font-bold text-indigo-900">{availableBuses}</span>
              </div>
              <div className="flex justify-between items-center border-b border-indigo-200 pb-2">
                <span className="text-sm font-semibold text-indigo-800">Bus Capacity</span>
                <span className="text-lg font-bold text-indigo-900">{busCapacity}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-semibold text-indigo-800">Optimization Status</span>
                <span className={clsx("text-lg font-bold", optimizationStatus.includes('Action') || optimizationStatus.includes('Limited') || optimizationStatus.includes('Allocate') ? "text-amber-600" : "text-emerald-600")}>
                  {optimizationStatus}
                </span>
              </div>
            </div>
          </div>

          {/* Total Routes */}
          <div className="rounded-2xl border-2 border-purple-500/30 bg-purple-50 shadow-md p-6">
            <div className="flex items-center gap-2 mb-4 text-purple-700">
              <Route className="w-6 h-6" />
              <h4 className="text-base font-extrabold">Total Routes</h4>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b border-purple-200 pb-2">
                <span className="text-sm font-semibold text-purple-800">Total Routes</span>
                <span className="text-lg font-bold text-purple-900">{(kpis.total_routes || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm font-semibold text-purple-800">Route ID</span>
                <span className="text-lg font-bold text-purple-900">{routeId}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const kpis = dashboardData?.kpis || {};
  const fleetSummary = dashboardData?.fleetSummary || {};

  const kpiCards = [
    {
      key: 'forecast',
      title: 'Forecasted Demand',
      value: (kpis.forecasted_demand || 0).toLocaleString(),
      icon: TrendingUp,
    },
    {
      key: 'buses',
      title: 'Allocated Buses',
      value: (kpis.allocated_buses || 0).toLocaleString(),
      icon: Bus,
    },
  ];

  return (
    <div className="space-y-8">
      {/* Overview KPIs */}
      {!dashboardLoading && dashboardData && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {kpiCards.map((c) => (
            <div key={c.key} className="rounded-2xl border border-border bg-surface shadow-st-sm p-6 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-muted uppercase tracking-wider">{c.title}</p>
                <p className="mt-2 text-3xl font-extrabold text-ink">{c.value}</p>
              </div>
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center bg-primary/10 text-primary">
                <c.icon className="w-6 h-6" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Route Simulation / Demand Analysis Integration */}
      <div className="mt-8">
        <div className="flex items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-sm font-bold text-ink">Operational Demand Analysis</h3>
            <p className="text-xs text-muted mt-0.5">Analyze live passenger demand and fleet requirements between any two stops.</p>
          </div>
          <Activity className="h-5 w-5 text-muted" />
        </div>
        
        <form onSubmit={handlePlanJourney} className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs font-bold text-muted uppercase mb-2 block">Source</label>
            <select
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm font-medium text-ink focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
              value={journeyFormData.source_id}
              onChange={e => setJourneyFormData(p => ({ ...p, source_id: e.target.value }))}
              disabled={stopsLoading}
            >
              <option value="">{stopsLoading ? 'Loading stops...' : 'Select Source Stop'}</option>
              {stops.map(s => (
                <option key={`src-${s.stop_id}`} value={s.stop_id} disabled={String(s.stop_id) === journeyFormData.destination_id}>
                  {s.stop_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs font-bold text-muted uppercase mb-2 block">Destination</label>
            <select
              className="w-full bg-background border border-border rounded-xl px-4 py-3 text-sm font-medium text-ink focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
              value={journeyFormData.destination_id}
              onChange={e => setJourneyFormData(p => ({ ...p, destination_id: e.target.value }))}
              disabled={stopsLoading}
            >
              <option value="">{stopsLoading ? 'Loading stops...' : 'Select Destination Stop'}</option>
              {stops.map(s => (
                <option key={`dst-${s.stop_id}`} value={s.stop_id} disabled={String(s.stop_id) === journeyFormData.source_id}>
                  {s.stop_name}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={journeyLoading || !journeyFormData.source_id || !journeyFormData.destination_id}
            className="theme-button-primary px-6 py-3 rounded-xl flex items-center justify-center gap-2 h-[46px] min-w-[140px] disabled:opacity-50"
          >
            {journeyLoading ? (
              <><RefreshCw className="w-4 h-4 animate-spin" /> Checking...</>
            ) : (
              <><Search className="w-4 h-4" /> Check Demand</>
            )}
          </button>
        </form>
        
        {journeyError && (
          <div className="mt-4 p-3 rounded-xl bg-danger/10 border border-danger/20 text-danger text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> {journeyError}
          </div>
        )}
        
        {renderJourneyDetails()}
      </div>
    </div>
  );
}
