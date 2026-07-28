import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer } from 'recharts';
import { Loader2, Activity, Bus, TrendingUp, AlertTriangle, CheckCircle, BarChart3, Users, Cloud, Navigation } from 'lucide-react';
import client from "/src/api/client.js";

export default function DemandForecastingFleetOptimization() {
  const [data, setData] = useState(null);
  const [pipelineValid, setPipelineValid] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch pipeline validation to apply safeguards
        const token = localStorage.getItem('token') || localStorage.getItem('access_token');
        const valRes = await fetch('/api/admin/pipeline/validation', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (valRes.ok) {
          const valData = await valRes.json();
          setPipelineValid(valData);
        }

        const response = await fetch('http://localhost:8000/api/admin/fleet-optimization');
        if (!response.ok) throw new Error('Failed to fetch fleet optimization data');
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return (
    <div className="flex justify-center items-center h-64 text-slate-500">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
      <span className="ml-3 font-medium">Loading Optimization Data...</span>
    </div>
  );

  if (error) return (
    <div className="p-4 bg-red-50 text-red-600 rounded-lg border border-red-200">
      ⚠️ Error: {error}
    </div>
  );

  // Use actual demand trend data from backend if available
  const demandTrend = Array.isArray(data?.demand_trend) ? data.demand_trend : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Demand Forecasting & Fleet Optimization</h1>
          <p className="text-slate-500 text-sm mt-1">Operational analytics and AI-driven fleet recommendations.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Demand Analytics */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-indigo-500" />
            <h2 className="text-lg font-bold text-slate-800">Demand Analytics</h2>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Predicted Demand</p>
              <p className="text-2xl font-extrabold text-indigo-700 mt-1">{data?.predicted_demand}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Confidence</p>
              <p className="text-2xl font-extrabold text-emerald-600 mt-1">{data?.demand_confidence}%</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Peak Status</p>
              <p className="text-lg font-bold text-amber-600 mt-1 uppercase">{data?.peak_status || 'N/A'}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Weather Impact</p>
              <p className="text-sm font-bold text-slate-700 mt-1 flex items-center gap-1">
                <Cloud className="w-4 h-4 text-sky-500" /> {data?.weather_impact || 'N/A'}
              </p>
            </div>
          </div>
          <div className="h-48 mt-4 flex items-center justify-center border border-dashed border-slate-200 rounded-xl bg-slate-50">
            {demandTrend.length === 0 ? (
              <p className="text-slate-500 font-medium">No demand trend data available yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={demandTrend}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="hour" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Line type="monotone" dataKey="demand" stroke="#6366f1" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Fleet Optimization */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Bus className="w-5 h-5 text-emerald-500" />
            <h2 className="text-lg font-bold text-slate-800">Fleet Optimization</h2>
          </div>
          
          {/* AI Recommendation Alert */}
          <div className={`mb-6 p-4 rounded-xl border ${data?.fleet_gap > 0 ? 'bg-red-50 border-red-200 text-red-800' : data?.fleet_gap < 0 ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-blue-50 border-blue-200 text-blue-800'}`}>
            <div className="flex items-start gap-3">
              {data?.fleet_gap > 0 ? <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-red-600" /> : <CheckCircle className="w-5 h-5 shrink-0 mt-0.5 text-emerald-600" />}
              <div>
                <h3 className="font-bold text-sm uppercase tracking-wider mb-1">AI Recommendation</h3>
                <p className="text-sm">{data?.recommendation}</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 flex-1 content-start">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-center">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Required Fleet</p>
              <p className="text-3xl font-extrabold text-slate-800 mt-2">{data?.required_fleet}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-center">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Available Fleet</p>
              <p className="text-3xl font-extrabold text-slate-800 mt-2">{data?.available_fleet}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-center">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Fleet Gap</p>
              <p className={`text-3xl font-extrabold mt-2 ${data?.fleet_gap > 0 ? 'text-red-600' : data?.fleet_gap < 0 ? 'text-emerald-600' : 'text-slate-600'}`}>
                {data?.fleet_gap > 0 ? `+${data?.fleet_gap}` : data?.fleet_gap}
              </p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-center">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Utilization</p>
              <p className="text-3xl font-extrabold text-indigo-600 mt-2">{data?.fleet_utilization}%</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Route Analytics */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Navigation className="w-5 h-5 text-sky-500" />
            <h2 className="text-lg font-bold text-slate-800">Route Analytics</h2>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 hover:bg-slate-50 rounded-lg transition-colors border border-transparent hover:border-slate-100">
              <span className="text-sm font-medium text-slate-600">Route Efficiency</span>
              <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded">{data?.route_efficiency != null ? `${data.route_efficiency}%` : 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center p-3 hover:bg-slate-50 rounded-lg transition-colors border border-transparent hover:border-slate-100">
              <span className="text-sm font-medium text-slate-600">Average Delay</span>
              <span className="text-sm font-bold text-amber-600 bg-amber-50 px-2 py-1 rounded">{data?.average_delay != null ? `${data.average_delay} min` : 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center p-3 hover:bg-slate-50 rounded-lg transition-colors border border-transparent hover:border-slate-100">
              <span className="text-sm font-medium text-slate-600">ETA Accuracy</span>
              <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded">{data?.eta_accuracy != null ? `${data.eta_accuracy}%` : 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center p-3 hover:bg-slate-50 rounded-lg transition-colors border border-transparent hover:border-slate-100">
              <span className="text-sm font-medium text-slate-600">Transfer Analysis</span>
              <span className="text-sm font-bold text-slate-700 bg-slate-100 px-2 py-1 rounded">{data?.avg_transfers != null ? `${data.avg_transfers} avg transfers` : 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Operational KPIs */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-fuchsia-500" />
            <h2 className="text-lg font-bold text-slate-800">Operational KPIs & Health</h2>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Buses</p>
              <p className="text-2xl font-extrabold text-slate-800 mt-1">{data?.active_buses != null ? data.active_buses.toLocaleString() : 'N/A'}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Passengers Today</p>
              <p className="text-2xl font-extrabold text-slate-800 mt-1">{data?.passengers_today != null ? data.passengers_today.toLocaleString() : 'N/A'}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Peak Route</p>
              <p className="text-sm font-bold text-slate-800 mt-2 truncate">{data?.peak_route || 'N/A'}</p>
            </div>
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">System Health</p>
              <div className="flex items-center gap-1.5 mt-2">
                <span className={`w-2.5 h-2.5 rounded-full ${data?.system_health === 'optimal' ? 'bg-emerald-500 animate-pulse' : data?.system_health === 'warning' ? 'bg-amber-500' : 'bg-red-500'}`} />
                <span className={`text-sm font-bold ${data?.system_health === 'optimal' ? 'text-emerald-700' : data?.system_health === 'warning' ? 'text-amber-700' : 'text-red-700'}`}>{data?.system_health || 'N/A'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
