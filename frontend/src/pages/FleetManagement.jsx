import { useState, useEffect } from 'react';
import { Bus, TrendingUp, AlertTriangle, CheckCircle, BarChart3 } from 'lucide-react';
import { getDashboardData } from '../api/client';
import clsx from 'clsx';

export default function FleetManagement() {
  const [fleetData, setFleetData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchFleetData = async () => {
      try {
        const data = await getDashboardData();
        // Extract fleet summary from the main dashboard payload
        if (data && data.fleetSummary) {
          setFleetData(data.fleetSummary);
        } else {
          throw new Error("Fleet data unavailable in dashboard payload");
        }
      } catch (err) {
        setError("Failed to load fleet metrics from backend.");
      } finally {
        setLoading(false);
      }
    };
    fetchFleetData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-primary rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !fleetData) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-6 py-4 rounded-2xl flex items-start max-w-3xl mx-auto mt-8 shadow-sm">
        <AlertTriangle className="w-6 h-6 mr-4 mt-0.5 shrink-0" />
        <div>
          <h3 className="font-bold">Error Loading Fleet Management</h3>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Fleet Management</h1>
          <p className="text-slate-500 mt-2">Live monitoring of bus allocations and overall utilization.</p>
        </div>
        <div className="theme-surface px-4 py-2 rounded-xl flex items-center">
          <span className="w-2.5 h-2.5 bg-primary rounded-full animate-pulse mr-2"></span>
          <span className="text-sm font-semibold text-slate-600">Live Sync</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="theme-kpi-card flex items-center">
          <div className="bg-primary/10 w-14 h-14 rounded-full flex items-center justify-center mr-4">
            <Bus className="w-7 h-7 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Total Available</p>
            <p className="text-3xl font-bold text-slate-800">{fleetData.available?.toLocaleString()}</p>
          </div>
        </div>
        <div className="theme-kpi-card flex items-center">
          <div className="bg-primary/10 w-14 h-14 rounded-full flex items-center justify-center mr-4">
            <CheckCircle className="w-7 h-7 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Active Allocation</p>
            <p className="text-3xl font-bold text-slate-800">{fleetData.optimizedAllocation?.toLocaleString()}</p>
          </div>
        </div>
        <div className="theme-kpi-card flex items-center">
          <div className="bg-primary/10 w-14 h-14 rounded-full flex items-center justify-center mr-4">
            <TrendingUp className="w-7 h-7 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Utilization</p>
            <div className="flex items-baseline">
              <p className="text-3xl font-bold text-slate-800">{fleetData.utilization}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Allocations Table */}
      <div className="theme-section-card">
        <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
          <BarChart3 className="w-5 h-5 mr-2 text-primary" />
          Current Route Allocations
        </h3>
        
        {fleetData.allocations && fleetData.allocations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Route ID</th>
                  <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Buses Allocated</th>
                  <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {fleetData.allocations.map((alloc, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 text-sm font-semibold text-slate-800">{alloc.route}</td>
                    <td className="py-3 px-4 text-sm text-center">
                      <span className="bg-primary/10 text-primary font-bold py-1 px-3 rounded-full">
                        {alloc.buses}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={clsx(
                        "text-xs font-bold px-2 py-1 rounded-md",
                        alloc.buses > 10 ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"
                      )}>
                        {alloc.buses > 10 ? "High Volume" : "Optimal"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500">
            No route allocations found in current live data.
          </div>
        )}
      </div>
    </div>
  );
}
