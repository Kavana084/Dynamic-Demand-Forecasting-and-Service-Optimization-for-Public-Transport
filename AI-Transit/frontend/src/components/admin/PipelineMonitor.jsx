import React, { useState, useEffect } from 'react';
import { Database, Activity, GitCommit, RefreshCw } from 'lucide-react';

export default function PipelineMonitor() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchValidation = async () => {
    try {
      const token = localStorage.getItem('token') || localStorage.getItem('access_token');
      const res = await fetch('/api/admin/pipeline/validation', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setData(await res.json());
        setLastRefreshed(new Date().toLocaleTimeString());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchValidation();
    const interval = setInterval(fetchValidation, 10000); // 10s auto-refresh
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) return <div className="p-8 text-center text-slate-500 animate-pulse font-medium">Loading Pipeline Data...</div>;

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status) => {
    switch(status) {
      case 'healthy': return 'text-emerald-700 bg-emerald-50 border-emerald-200';
      case 'partial': return 'text-blue-700 bg-blue-50 border-blue-200';
      case 'empty': return 'text-slate-600 bg-slate-50 border-slate-200';
      case 'degraded': return 'text-amber-700 bg-amber-50 border-amber-200';
      case 'unavailable': return 'text-red-700 bg-red-50 border-red-200';
      default: return 'text-slate-600 bg-slate-50 border-slate-200';
    }
  };

  const StatusBadge = ({ status }) => (
    <span className={`px-2 py-1 rounded-md text-xs font-bold uppercase tracking-wider border ${getStatusColor(status)} shadow-sm`}>
      {status || 'Unknown'}
    </span>
  );

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mt-8 transition-all hover:shadow-md">
      <div className="p-5 border-b border-slate-100 flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-50/50 space-y-3 md:space-y-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-100 text-indigo-700 rounded-lg">
            <Database className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-bold text-slate-800 tracking-tight">Pipeline Monitor</h2>
        </div>
        <div className="flex items-center space-x-4 text-xs text-slate-500">
          <div className="flex items-center space-x-1.5 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-500" />
            <span className="font-medium">Last checked: {lastRefreshed}</span>
          </div>
          {data && <StatusBadge status={data.overall_status} />}
        </div>
      </div>
      
      <div className="p-6 bg-white">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Data Stores */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center border-b border-slate-100 pb-2">
              <Database className="w-3.5 h-3.5 mr-1.5" /> Data Records
            </h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { label: 'Journey History', data: data?.journey_history },
                { label: 'Demand History', data: data?.demand_history },
                { label: 'Prediction Records', data: data?.prediction_records },
                { label: 'Optimization Results', data: data?.optimization_results },
              ].map((item, idx) => (
                <div key={idx} className="flex flex-col p-4 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white hover:border-indigo-100 hover:shadow-sm transition-all group">
                  <span className="text-slate-500 text-sm font-medium mb-2 group-hover:text-indigo-600 transition-colors">{item.label}</span>
                  <div className="flex justify-between items-end mt-auto">
                    <span className="text-2xl font-bold text-slate-800">{item.data?.count?.toLocaleString() || 0}</span>
                    <StatusBadge status={item.data?.status} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline Jobs */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center border-b border-slate-100 pb-2">
              <Activity className="w-3.5 h-3.5 mr-1.5" /> Last Runs
            </h3>
            
            <div className="space-y-3">
              {[
                { label: 'Aggregation', time: data?.aggregation_last_run, icon: Activity },
                { label: 'Forecasting', time: data?.forecasting_last_run, icon: GitCommit },
                { label: 'Optimization', time: data?.optimization_last_run, icon: Database },
              ].map((item, idx) => {
                const Icon = item.icon;
                return (
                  <div key={idx} className="flex items-center space-x-4 p-4 rounded-xl border border-slate-100 bg-white hover:border-indigo-100 hover:shadow-sm transition-all group">
                    <div className="w-10 h-10 rounded-full bg-slate-50 group-hover:bg-indigo-50 flex items-center justify-center transition-colors">
                      <Icon className="w-5 h-5 text-slate-400 group-hover:text-indigo-600 transition-colors" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-800">{item.label}</div>
                      <div className="text-xs font-medium text-slate-500 mt-0.5">{formatDate(item.time)}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
