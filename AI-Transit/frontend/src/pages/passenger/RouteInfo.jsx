import { useState, useEffect } from 'react';
import { getRoutes } from '../../api/client';
import { Map, MapPin, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';

function RouteCardSkeleton() {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 animate-pulse">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 bg-slate-200 rounded-lg" />
        <div className="flex-1">
          <div className="h-5 bg-slate-200 rounded w-3/4 mb-2" />
          <div className="h-4 bg-slate-200 rounded w-1/2" />
        </div>
      </div>
      <div className="space-y-3">
        <div className="h-4 bg-slate-200 rounded w-full" />
        <div className="h-16 bg-slate-200 rounded" />
      </div>
    </div>
  );
}

export default function RouteInfo() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchRoutes = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getRoutes(0, 100);
      setRoutes(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to fetch routes:', err);
      setError(err.message || 'Failed to load routes');
      setRoutes([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRoutes();
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Route Information Directory</h2>
        <p className="text-slate-500 mt-1">Browse all available transit lines.</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => <RouteCardSkeleton key={i} />)}
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-red-800 mb-2">Unable to load routes</h3>
          <p className="text-red-600 text-sm mb-4">{error}</p>
          <button
            onClick={fetchRoutes}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      ) : routes.length === 0 ? (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-12 text-center">
          <Map className="w-16 h-16 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-700 mb-2">No routes available</h3>
          <p className="text-slate-500 text-sm mb-4">There are currently no routes in the system.</p>
          <button
            onClick={fetchRoutes}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {routes.map((route, idx) => (
            <div key={idx} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition-shadow">
              <div className="flex items-center space-x-3 mb-4">
                <div className="bg-primary/10 p-2.5 rounded-lg text-primary">
                  <Map className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-slate-800">{route.name || `Route ${route.route_id}`}</h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-start text-sm text-slate-600">
                  <MapPin className="w-4 h-4 mr-2 mt-0.5 text-slate-400 shrink-0" />
                  <span><span className="font-semibold text-slate-700">ID:</span> {route.route_id}</span>
                </div>
                <p className="text-sm text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
                  {route.description || "No description provided by backend."}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
