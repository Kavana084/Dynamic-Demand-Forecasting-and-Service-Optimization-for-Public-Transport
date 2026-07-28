import { useState } from 'react';
import { Play, Settings, BarChart3, CheckCircle, AlertTriangle } from 'lucide-react';
import { optimizeFleet } from '../api/client';
import BeforeAfterBar from '../components/charts/BeforeAfterBar';
import clsx from 'clsx';

export default function OptimizeFleet() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  
  const [formData, setFormData] = useState({
    bus_capacity: 50,
    max_buses_per_route: 15,
    cost_per_bus: 200.0,
    penalty_unmet_demand: 5.0
  });

  const handleRunOptimization = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await optimizeFleet(formData);
      setResults(data);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Optimization solver failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Controls */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 transition-all">
        <h2 className="text-xl font-bold text-slate-800 mb-1 flex items-center">
          <Settings className="w-5 h-5 mr-2 text-primary" /> 
          Service Frequency Engine
        </h2>
        <p className="text-sm text-slate-500 mb-6">Run the MILP solver to compute optimal <strong>service frequency levels</strong> per route based on aggregated passenger demand. This is a city-level batch operation — not per-request dispatch.</p>
        
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-start">
            <AlertTriangle className="w-5 h-5 mr-3 mt-0.5 shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        <div className="flex flex-wrap items-end gap-6">
          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-2">Bus Capacity</label>
            <input 
              type="number" 
              value={formData.bus_capacity} 
              onChange={e => setFormData({...formData, bus_capacity: parseInt(e.target.value)})}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary focus:border-transparent transition-all" 
            />
          </div>
          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-2">Max Buses / Route</label>
            <input 
              type="number" 
              value={formData.max_buses_per_route} 
              onChange={e => setFormData({...formData, max_buses_per_route: parseInt(e.target.value)})}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary focus:border-transparent transition-all" 
            />
          </div>
          <div className="flex-1 min-w-[150px]">
            <label className="block text-xs font-semibold text-slate-600 mb-2">Cost / Bus ($)</label>
            <input 
              type="number" 
              value={formData.cost_per_bus} 
              onChange={e => setFormData({...formData, cost_per_bus: parseFloat(e.target.value)})}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary focus:border-transparent transition-all" 
            />
          </div>
          <button 
            onClick={handleRunOptimization}
            disabled={loading}
            className="bg-primary hover:bg-[#5a4cdb] text-white px-8 py-2.5 rounded-lg font-medium shadow-sm shadow-primary/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-70 disabled:cursor-not-allowed h-[42px]"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Execute Solver</span>
              </>
            )}
          </button>
        </div>
      </div>

      {results && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4">
          {/* Results Table */}
          <div className="xl:col-span-2 bg-white rounded-xl shadow-sm border border-slate-100 p-6 overflow-hidden">
            <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center">
              <BarChart3 className="w-5 h-5 mr-2 text-primary" />
              Route Allocations
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100">
                    <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Route</th>
                    <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Priority</th>
                    <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Predicted Demand</th>
                    <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Allocated Buses</th>
                    <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Recommended Freq</th>
                    <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-center">Unserved Demand</th>
                    <th className="py-3 px-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Load Factor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {results.allocated_buses?.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4">
                        <div className="text-sm font-semibold text-slate-800">{row.route_name}</div>
                      </td>
                      <td className="py-3 px-4 text-sm text-center">
                        <span className={clsx("py-1 px-3 rounded-full text-xs font-bold", 
                          row.priority === 'HIGH' ? "bg-red-100 text-red-700" :
                          row.priority === 'MEDIUM' ? "bg-amber-100 text-amber-700" :
                          "bg-emerald-100 text-emerald-700"
                        )}>
                          {row.priority}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600 text-center">{Math.round(row.predicted_demand).toLocaleString()}</td>
                      <td className="py-3 px-4 text-sm font-bold text-primary text-center">
                        <span className="bg-indigo-50 text-indigo-700 py-1 px-3 rounded-full">{row.assigned_buses}</span>
                      </td>
                      <td className="py-3 px-4 text-sm text-slate-600 text-center font-medium">
                        {row.recommended_frequency}
                      </td>
                      <td className="py-3 px-4 text-sm text-center">
                        <span className={clsx("font-medium", row.unmet_demand > 0 ? "text-red-500" : "text-emerald-500")}>
                          {Math.round(row.unmet_demand)}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
                            <div 
                              className={clsx("h-full rounded-full transition-all duration-1000", 
                                row.utilization_percent > 85 ? "bg-red-500" : 
                                row.utilization_percent > 60 ? "bg-emerald-500" : "bg-amber-500"
                              )}
                              style={{ width: `${Math.min(100, row.utilization_percent)}%` }}
                            />
                          </div>
                          <span className="text-xs font-bold text-slate-600">{row.utilization_percent.toFixed(1)}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Sidebar / Summary */}
          <div className="space-y-6">
            {/* Optimization Summary */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
              <h3 className="text-sm font-bold text-slate-800 mb-4 uppercase tracking-wider">Optimization Summary</h3>
              <div className="space-y-4">
                <div className="flex justify-between text-sm items-center">
                  <span className="text-slate-500">Total Passengers</span>
                  <span className="font-bold text-slate-800 text-lg">{Math.round(results.summary?.total_passengers_served || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm items-center">
                  <span className="text-slate-500">Total Buses Allocated</span>
                  <span className="font-bold text-primary bg-indigo-50 px-2 py-0.5 rounded text-lg">{results.summary?.total_buses_used || 0}</span>
                </div>
                <div className="flex justify-between text-sm items-center pb-4 border-b border-slate-100">
                  <span className="text-slate-500">Total Unmet Demand</span>
                  <span className={clsx("font-bold text-lg", results.summary?.total_unmet_demand > 0 ? "text-red-500" : "text-emerald-500")}>
                    {Math.round(results.summary?.total_unmet_demand || 0).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between text-sm items-center">
                  <span className="text-slate-500">Estimated Daily Cost</span>
                  <span className="font-bold text-slate-800 text-lg">${(results.summary?.total_cost || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center text-sm pt-2">
                  <span className="text-slate-800 font-medium">Overall Efficiency</span>
                  <span className="bg-emerald-100 text-emerald-700 font-bold px-4 py-1.5 rounded-full text-base">
                    {results.summary?.overall_efficiency_percent?.toFixed(1) || 0}%
                  </span>
                </div>
              </div>
            </div>

            {/* Priority Distribution */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
              <h3 className="text-sm font-bold text-slate-800 mb-4">Priority Distribution</h3>
              <div className="flex items-center space-x-2 h-12 w-full rounded-lg overflow-hidden">
                {['HIGH', 'MEDIUM', 'LOW'].map(level => {
                  const count = results.allocated_buses?.filter(r => r.priority === level).length || 0;
                  const total = results.allocated_buses?.length || 1;
                  const percentage = (count / total) * 100;
                  if (count === 0) return null;
                  return (
                    <div 
                      key={level}
                      style={{ width: `${percentage}%` }}
                      className={clsx(
                        "h-full flex items-center justify-center text-xs font-bold text-white transition-all",
                        level === 'HIGH' ? "bg-red-500" : level === 'MEDIUM' ? "bg-amber-500" : "bg-emerald-500"
                      )}
                      title={`${level}: ${count} Routes`}
                    >
                      {percentage > 15 ? `${count} ${level}` : count}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Demand Ranking */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
              <h3 className="text-sm font-bold text-slate-800 mb-4">Top 5 Demand Ranking</h3>
              <div className="space-y-4">
                {[...(results.allocated_buses || [])]
                  .sort((a, b) => b.predicted_demand - a.predicted_demand)
                  .slice(0, 5)
                  .map((route, i) => {
                    const maxDemand = Math.max(...(results.allocated_buses?.map(r => r.predicted_demand) || [1]));
                    const width = `${(route.predicted_demand / maxDemand) * 100}%`;
                    return (
                      <div key={route.route_id} className="relative pt-1">
                        <div className="flex justify-between items-center mb-1 text-xs">
                          <span className="font-semibold text-slate-700 truncate pr-2">{route.route_name}</span>
                          <span className="font-bold text-primary shrink-0">{route.predicted_demand} pax</span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-2">
                          <div className="bg-primary h-2 rounded-full" style={{ width }}></div>
                        </div>
                      </div>
                    );
                  })
                }
              </div>
            </div>

            {/* Status */}
            <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-5 flex items-start space-x-3 shadow-sm">
              <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-emerald-800 mb-1">Frequency Schedule Computed</h4>
                <p className="text-xs text-emerald-700 leading-relaxed">
                  The MILP solver computed optimal service frequency levels for all routes. The schedule engine will apply these as frequency targets.
                </p>
                {results.cached && (
                  <p className="text-xs text-emerald-600/70 mt-2 italic">* Results loaded from recent cache.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
