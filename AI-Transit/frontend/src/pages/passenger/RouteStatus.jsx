import { useState, useEffect } from 'react';
import { getDashboardData } from '../../api/client';
import { Bus, Clock, Users, CheckCircle, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';

function RouteStatusSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 animate-pulse">
      <div className="flex items-center space-x-4">
        <div className="w-12 h-12 bg-slate-200 rounded-full" />
        <div className="flex-1 space-y-2">
          <div className="h-5 bg-slate-200 rounded w-1/3" />
          <div className="h-4 bg-slate-200 rounded w-1/2" />
        </div>
      </div>
    </div>
  );
}

export default function RouteStatus() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchStatus = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getDashboardData();
      if (data && data.fleetSummary && data.fleetSummary.allocations) {
        setRoutes(data.fleetSummary.allocations);
      } else {
        setRoutes([]);
      }
    } catch (err) {
      console.error('Failed to fetch route status:', err);
      setError(err.message || 'Failed to load route status');
      setRoutes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Route Status</h2>
          <p className="text-slate-500 mt-1">Operational availability and predicted demand statuses.</p>
        </div>
        <button
          onClick={fetchStatus}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => <RouteStatusSkeleton key={i} />)}
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-red-800 mb-2">Unable to load route status</h3>
          <p className="text-red-600 text-sm mb-4">{error}</p>
          <button
            onClick={fetchStatus}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      ) : routes.length === 0 ? (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-12 text-center">
          <Bus className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-700 mb-2">No route data available</h3>
          <p className="text-slate-500 text-sm mb-4">There are currently no operational routes to display.</p>
          <button
            onClick={fetchStatus}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {routes.map((route, idx) => (
            <div key={idx} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:shadow-md">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center shrink-0">
                  <Bus className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-800">{route.route}</h3>
                  <div className="flex items-center text-sm text-slate-500 mt-1 space-x-3">
                    <span className="flex items-center"><Clock className="w-3.5 h-3.5 mr-1" /> Active</span>
                    <span className="flex items-center"><Users className="w-3.5 h-3.5 mr-1" /> {route.buses} buses allocated</span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end">
                {route.buses >= 10 ? (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-700">
                    <AlertCircle className="w-3.5 h-3.5 mr-1" />
                    High Demand Expected
                  </span>
                ) : (
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">
                    <CheckCircle className="w-3.5 h-3.5 mr-1" />
                    Normal Operations
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
