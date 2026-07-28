import { useState, useEffect, useMemo } from 'react';
import { Route, Search, Filter, AlertTriangle } from 'lucide-react';
import { getRoutes } from '../api/client';

export default function RouteAnalytics() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchRoutes = async () => {
      try {
        const data = await getRoutes(0, 1000);
        setRoutes(data || []);
      } catch (err) {
        setError(err.message || 'Failed to fetch routes');
      } finally {
        setLoading(false);
      }
    };
    fetchRoutes();
  }, []);

  const filteredRoutes = useMemo(() => {
    return routes.filter(r => 
      r.route_id?.toLowerCase().includes(searchTerm.toLowerCase()) || 
      r.name?.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [routes, searchTerm]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center">
            <Route className="w-6 h-6 mr-2 text-primary" />
            Route Analytics
          </h2>
          <p className="text-sm text-slate-500 mt-1">Manage and analyze all active transit routes</p>
        </div>
        
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search routes..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary focus:border-transparent w-full md:w-64 transition-all"
          />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start">
          <AlertTriangle className="w-5 h-5 mr-3 mt-0.5 shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Route ID</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Route Name / Description</th>
                <th className="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {loading ? (
                <tr>
                  <td colSpan="3" className="py-8 text-center">
                    <div className="inline-block animate-spin w-6 h-6 border-2 border-slate-300 border-t-primary rounded-full"></div>
                    <p className="text-slate-500 mt-2 text-sm">Loading routes...</p>
                  </td>
                </tr>
              ) : filteredRoutes.length === 0 ? (
                <tr>
                  <td colSpan="3" className="py-12 text-center text-slate-500">
                    <Route className="w-12 h-12 mx-auto text-slate-200 mb-3" />
                    <p>No routes found.</p>
                  </td>
                </tr>
              ) : (
                filteredRoutes.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="py-4 px-6 text-sm font-bold text-slate-800">{row.route_id}</td>
                    <td className="py-4 px-6 text-sm text-slate-600">{row.name || row.description || 'Auto-discovered route'}</td>
                    <td className="py-4 px-6">
                      <span className="bg-emerald-50 text-emerald-600 text-xs font-bold px-3 py-1 rounded-full">Active</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {!loading && (
          <div className="bg-slate-50 py-3 px-6 border-t border-slate-100 flex items-center justify-between text-sm text-slate-500">
            <span>Showing {filteredRoutes.length} routes</span>
          </div>
        )}
      </div>
    </div>
  );
}
