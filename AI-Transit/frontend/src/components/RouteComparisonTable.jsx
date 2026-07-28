import { ArrowRight, Clock, Users, Activity, TrendingUp } from 'lucide-react';

export default function RouteComparisonTable({ alternatives }) {
  if (!alternatives || alternatives.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
        <Activity className="w-4 h-4 text-primary" />
        Route Comparison
      </h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-3 px-4 font-semibold text-slate-600">Route</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-600">ETA</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-600">Traffic</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-600">Optimization Score</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-600">Selection Reason</th>
            </tr>
          </thead>
          <tbody>
            {alternatives.map((route, index) => (
              <tr 
                key={route.route_id ||_index} 
                className={`border-b border-slate-100 ${route.is_selected ? 'bg-indigo-50' : ''}`}
              >
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {route.is_selected && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-700 border border-indigo-200">
                        <TrendingUp className="w-3 h-3" />
                        Selected
                      </span>
                    )}
                    <span className="font-medium text-slate-800">{route.route_id || `Route ${index + 1}`}</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-1 text-slate-700">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    {route.eta_minutes || '—'} min
                  </div>
                </td>
                <td className="py-3 px-4">
                  <span className={`font-medium ${
                    route.traffic === 'High' ? 'text-red-600' : 
                    route.traffic === 'Medium' ? 'text-orange-500' : 
                    'text-emerald-600'
                  }`}>
                    {route.traffic || 'Normal'}
                  </span>
                </td>
                <td className="py-3 px-4">
                  <span className={`font-bold ${
                    route.optimization_score >= 80 ? 'text-emerald-600' : 
                    route.optimization_score >= 60 ? 'text-blue-600' : 
                    'text-orange-600'
                  }`}>
                    {route.optimization_score || '—'}/100
                  </span>
                </td>
                <td className="py-3 px-4">
                  <span className="text-xs text-slate-600">{route.selection_reason || '—'}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
