import React from 'react';
import { CheckCircle2, Navigation, Clock, Activity, Users, ArrowRight, Trophy, Info } from 'lucide-react';

export default function RouteComparison({
  candidates,
  selectedRouteId,
  onSelectRoute,
  executiveMode
}) {
  if (!candidates || candidates.length === 0) return null;

  // The first candidate in the sorted array is the recommended one
  const recommendedCandidate = candidates[0];

  const getTrafficColor = (t) => {
    const tLower = t?.toLowerCase();
    if (tLower === 'high' || tLower === 'heavy') return 'text-red-600';
    if (tLower === 'medium') return 'text-orange-500';
    return 'text-emerald-600';
  };

  const generateExplanation = (candidate) => {
    const reasons = [];
    
    // Find min values among all candidates
    const minTime = Math.min(...candidates.map(c => c.travel_time));
    const minTransfers = Math.min(...candidates.map(c => c.transfer_count));
    
    if (candidate.travel_time === minTime) {
      reasons.push('Lowest travel time');
    }
    
    const trafficL = candidate.traffic.toLowerCase();
    if (trafficL === 'low') {
      reasons.push('Low traffic conditions');
    } else if (trafficL === 'medium') {
      reasons.push('Manageable traffic conditions');
    }
    

    if (candidate.transfer_count === 0) {
      reasons.push('Direct route (no transfers)');
    } else if (candidate.transfer_count === minTransfers) {
      reasons.push(`Fewest transfers (${candidate.transfer_count})`);
    }

    // Ensure we have at least something
    if (reasons.length === 0) {
      reasons.push('Best overall balance of time, transfers, and comfort');
    }
    
    return reasons;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 px-1">
        <Navigation className="w-5 h-5 text-indigo-600" />
        <h2 className="text-lg font-bold text-slate-800">Multi-Route Planning & Recommendation</h2>
      </div>

      {/* Recommended Banner */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100 rounded-2xl p-5 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 opacity-10">
          <Trophy className="w-24 h-24 text-indigo-600" />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="flex-1 space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-bold">
              <Trophy className="w-3.5 h-3.5" /> AI Recommended
            </div>
            <h3 className="text-xl font-bold text-slate-800">
              {recommendedCandidate.name} ({recommendedCandidate.route_id})
            </h3>
            
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-700">Recommended because:</p>
              <ul className="space-y-1">
                {generateExplanation(recommendedCandidate).map((reason, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm text-slate-600">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> {reason}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          
          <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-100 min-w-[140px] text-center">
            <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Score</p>
            <p className="text-4xl font-extrabold text-indigo-600">{recommendedCandidate.recommendation_score}</p>
            <p className="text-xs text-slate-500 mt-1">out of 100</p>
          </div>
        </div>

        {/* Executive Mode Breakdown */}
        {executiveMode && (
          <div className="mt-4 pt-4 border-t border-indigo-100/50">
            <p className="text-xs font-bold text-indigo-800 mb-2 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" /> Executive Analytics: Score Breakdown (Penalties)
            </p>
            <div className="flex flex-wrap gap-4 text-xs">
              <div className="bg-white/60 px-3 py-1.5 rounded-lg">
                <span className="text-slate-500">Travel Time:</span> <span className="font-semibold text-red-500">-{recommendedCandidate.score_breakdown.time}</span>
              </div>
              <div className="bg-white/60 px-3 py-1.5 rounded-lg">
                <span className="text-slate-500">Traffic:</span> <span className="font-semibold text-red-500">-{recommendedCandidate.score_breakdown.traffic}</span>
              </div>

              <div className="bg-white/60 px-3 py-1.5 rounded-lg">
                <span className="text-slate-500">Transfers:</span> <span className="font-semibold text-red-500">-{recommendedCandidate.score_breakdown.transfers}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {candidates.map((cand) => {
          const isSelected = cand.id === selectedRouteId;
          const isRecommended = cand.id === recommendedCandidate.id;
          
          return (
            <div 
              key={cand.id}
              className={`relative rounded-2xl border transition-all ${
                isSelected 
                  ? 'border-indigo-500 shadow-md ring-1 ring-indigo-500' 
                  : 'border-slate-200 bg-white hover:border-indigo-300 hover:shadow-sm'
              }`}
            >
              {isRecommended && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-indigo-500 text-white text-[10px] font-bold px-3 py-0.5 rounded-full shadow-sm">
                  TOP PICK
                </div>
              )}
              
              <div className="p-5">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h4 className={`font-bold ${isSelected ? 'text-indigo-700' : 'text-slate-800'}`}>
                      {cand.name}
                    </h4>
                    <p className="text-xs text-slate-400">Score: {cand.recommendation_score}</p>
                  </div>
                </div>

                <div className="space-y-2 mb-5">
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500 flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" /> Time</span>
                    <span className="font-bold text-slate-800">{cand.travel_time} min</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500 flex items-center gap-1.5"><Navigation className="w-3.5 h-3.5" /> Distance</span>
                    <span className="font-bold text-slate-800">{cand.distance_km} km</span>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span className="text-slate-500 flex items-center gap-1.5"><Activity className="w-3.5 h-3.5" /> Transfers</span>
                    <span className="font-bold text-slate-800">{cand.transfer_count}</span>
                  </div>
                </div>

                <button
                  onClick={() => onSelectRoute(cand.id)}
                  className={`w-full py-2 rounded-lg text-sm font-semibold transition-colors ${
                    isSelected 
                      ? 'bg-indigo-50 text-indigo-700' 
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {isSelected ? 'Currently Viewing' : 'View Route'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Comparison Table */}
      <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 uppercase text-xs font-semibold">
              <tr>
                <th className="px-5 py-3">Metric</th>
                {candidates.map(c => (
                  <th key={c.id} className="px-5 py-3">
                    <div className="flex items-center gap-1.5">
                      {c.name}
                      {c.id === recommendedCandidate.id && <Trophy className="w-3.5 h-3.5 text-indigo-500" />}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr className="hover:bg-slate-50/50">
                <td className="px-5 py-3 font-medium text-slate-500">ETA</td>
                {candidates.map(c => <td key={c.id} className="px-5 py-3 font-bold text-slate-800">{c.travel_time} min</td>)}
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-5 py-3 font-medium text-slate-500">Distance</td>
                {candidates.map(c => <td key={c.id} className="px-5 py-3 font-bold text-slate-800">{c.distance_km} km</td>)}
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-5 py-3 font-medium text-slate-500">Transfers</td>
                {candidates.map(c => <td key={c.id} className="px-5 py-3 font-bold text-slate-800">{c.transfer_count}</td>)}
              </tr>

              <tr className="hover:bg-slate-50/50">
                <td className="px-5 py-3 font-medium text-slate-500">Traffic</td>
                {candidates.map(c => <td key={c.id} className={`px-5 py-3 font-bold ${getTrafficColor(c.traffic)}`}>{c.traffic}</td>)}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
