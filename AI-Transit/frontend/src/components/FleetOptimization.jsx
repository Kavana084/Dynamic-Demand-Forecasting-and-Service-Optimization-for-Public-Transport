import { Bus, Clock, TrendingUp, Zap, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function FleetOptimization({ 
  currentFleet, 
  recommendedFleet, 
  additionalBuses, 
  currentFrequency, 
  optimizedFrequency, 
  fleetUtilization, 
  optimizationStatus, 
  expectedWaitingTime 
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
          <Bus className="w-4 h-4 text-primary" />
          Fleet Optimization
        </h3>
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
          optimizationStatus === 'Optimized' 
            ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
            : optimizationStatus === 'Needs Adjustment'
            ? 'bg-amber-100 text-amber-700 border border-amber-200'
            : 'bg-slate-100 text-slate-600 border border-slate-200'
        }`}>
          {optimizationStatus === 'Optimized' ? (
            <CheckCircle2 className="w-3 h-3" />
          ) : (
            <AlertTriangle className="w-3 h-3" />
          )}
          {optimizationStatus || 'Unknown'}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Current Fleet Allocation */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Bus className="w-4 h-4 text-slate-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Current Fleet</p>
          </div>
          <p className="text-xl font-extrabold text-slate-800">
            {currentFleet !== undefined ? currentFleet : '—'}
          </p>
        </div>

        {/* Recommended Fleet Allocation */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Bus className="w-4 h-4 text-indigo-500" />
            <p className="text-xs text-indigo-600 font-semibold uppercase">Recommended</p>
          </div>
          <p className="text-xl font-extrabold text-indigo-700">
            {recommendedFleet !== undefined ? recommendedFleet : '—'}
          </p>
        </div>

        {/* Additional Buses Required */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-blue-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Additional Buses</p>
          </div>
          <p className="text-xl font-extrabold text-slate-800">
            {additionalBuses !== undefined ? additionalBuses : '—'}
          </p>
        </div>

        {/* Fleet Utilization */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-emerald-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Utilization</p>
          </div>
          <p className="text-xl font-extrabold text-slate-800">
            {fleetUtilization !== undefined ? `${Math.round(fleetUtilization)}%` : '—'}
          </p>
        </div>

        {/* Current Service Frequency */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-slate-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Current Freq</p>
          </div>
          <p className="text-xl font-extrabold text-slate-800">
            {currentFrequency !== undefined ? `${currentFrequency} min` : '—'}
          </p>
        </div>

        {/* Optimized Service Frequency */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-indigo-500" />
            <p className="text-xs text-indigo-600 font-semibold uppercase">Optimized Freq</p>
          </div>
          <p className="text-xl font-extrabold text-indigo-700">
            {optimizedFrequency !== undefined ? `${optimizedFrequency} min` : '—'}
          </p>
        </div>

        {/* Expected Waiting Time */}
        <div className="bg-slate-50 border border-slate-100 rounded-xl p-4 col-span-2">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-amber-500" />
            <p className="text-xs text-slate-500 font-semibold uppercase">Expected Wait Time</p>
          </div>
          <p className="text-xl font-extrabold text-slate-800">
            {expectedWaitingTime !== undefined ? `${expectedWaitingTime} min` : '—'}
          </p>
        </div>
      </div>
    </div>
  );
}
