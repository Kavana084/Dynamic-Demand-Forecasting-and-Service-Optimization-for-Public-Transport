import { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, Clock, Zap, Brain, Users } from 'lucide-react';

export default function AITransitIntelligence({ routeId, currentDemand, forecastDemand, peakStatus, demandConfidence }) {
  // Calculate demand trend from current and forecast demand
  const getDemandTrend = () => {
    if (currentDemand === undefined || forecastDemand === undefined) return null;
    
    if (forecastDemand > currentDemand * 1.1) return 'increasing';
    if (forecastDemand < currentDemand * 0.9) return 'decreasing';
    return 'stable';
  };

  const demandTrend = getDemandTrend();
  const lastUpdated = new Date().toLocaleTimeString();

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
          <Brain className="w-4 h-4 text-indigo-500" />
          AI Transit Intelligence
        </h3>
        <span className="text-xs text-slate-400">Last updated: {lastUpdated}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {/* Current Passenger Demand */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-blue-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Current Demand</p>
          </div>
          <p className="text-xl font-extrabold text-slate-800">
            {currentDemand !== undefined ? currentDemand : 'Loading...'}
          </p>
        </div>

        {/* Forecast Passenger Demand */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-indigo-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Forecast Demand</p>
          </div>
          <p className="text-xl font-extrabold text-slate-800">
            {forecastDemand !== undefined ? forecastDemand : '—'}
          </p>
        </div>

        {/* Demand Trend */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            {demandTrend === 'increasing' ? (
              <TrendingUp className="w-4 h-4 text-red-500" />
            ) : demandTrend === 'decreasing' ? (
              <TrendingDown className="w-4 h-4 text-emerald-500" />
            ) : (
              <Activity className="w-4 h-4 text-blue-500" />
            )}
            <p className="text-xs text-slate-500 font-semibold uppercase">Demand Trend</p>
          </div>
          <p className="text-lg font-extrabold text-slate-800 capitalize">
            {demandTrend || 'Stable'}
          </p>
        </div>

        {/* Forecast Model */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-4 h-4 text-indigo-500" />
            <p className="text-xs text-indigo-600 font-semibold uppercase">Forecast Model</p>
          </div>
          <p className="text-lg font-extrabold text-indigo-700">CatBoost</p>
        </div>

        {/* Peak/Off-Peak Status */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-amber-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Peak Status</p>
          </div>
          <p className="text-lg font-extrabold text-slate-800 capitalize">
            {peakStatus || 'Unknown'}
          </p>
        </div>

        {/* Prediction Confidence */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-emerald-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Confidence</p>
          </div>
          <p className="text-lg font-extrabold text-slate-800">
            {demandConfidence && demandConfidence !== 'Unavailable' ? demandConfidence : '—'}
          </p>
        </div>
      </div>
    </div>
  );
}
