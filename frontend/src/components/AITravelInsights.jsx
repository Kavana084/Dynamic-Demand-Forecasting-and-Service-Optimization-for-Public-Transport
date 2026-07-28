import { Clock, Users, AlertTriangle, TrendingUp, Lightbulb } from 'lucide-react';

export default function AITravelInsights({ 
  peakStatus, 
  demandConfidence,
  etaMinutes,
  serviceFrequency,
  weather,
  traffic,
  delayRisk = 'Low' // Assuming passed from parent or backend if applicable, else defaults to Low if not sent
}) {
  const getRouteReliability = () => {
    // Use confidence score directly
    if (demandConfidence) {
      return Math.round(parseFloat(demandConfidence) * 100);
    }
    return null;
  };

  const getBestTimeToTravel = () => {
    if (peakStatus?.toLowerCase().includes('peak')) {
      return 'In 30 minutes (after peak)';
    }
    return 'Now';
  };

  const getSmartRecommendation = () => {
    const bestTime = getBestTimeToTravel();
    const headway = serviceFrequency?.headway_minutes || 15;

    if (delayRisk === 'High') {
      return 'Expect delays due to current conditions. Consider alternative routes if available.';
    }
    if (delayRisk === 'Low') {
      return `Great time to travel! Next bus arrives in approximately ${headway} minutes.`;
    }
    if (bestTime === 'Now') {
      return 'Leave within the next 5 minutes to catch the next bus.';
    }
    return 'Route is running normally. Safe travels!';
  };

  const routeReliability = getRouteReliability();
  const bestTime = getBestTimeToTravel();
  const smartRecommendation = getSmartRecommendation();
  let delayColor = 'text-emerald-600 bg-emerald-50 border-emerald-200';
  if (delayRisk === 'Medium') delayColor = 'text-amber-600 bg-amber-50 border-amber-200';
  if (delayRisk === 'High') delayColor = 'text-red-600 bg-red-50 border-red-200';



  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-indigo-500" />
          AI Travel Insights
        </h3>
        <span className="text-xs text-slate-400">Live</span>
      </div>

      <div className="space-y-3">
        {/* Best Time to Travel */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-500" />
            <span className="text-xs text-slate-600 font-medium">Best time to travel</span>
          </div>
          <span className="text-sm font-bold text-slate-800">{bestTime}</span>
        </div>

        {/* Delay Risk */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-blue-500" />
            <span className="text-xs text-slate-600 font-medium">Delay Risk</span>
          </div>
          <span className={`text-sm font-bold px-2 py-1 rounded-lg border ${delayColor}`}>
            {delayRisk}
          </span>
        </div>

        {/* Route Reliability */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-blue-500" />
            <span className="text-xs text-slate-600 font-medium">Route Reliability</span>
          </div>
          <span className="text-sm font-bold text-slate-800">{routeReliability ? `${routeReliability}%` : 'N/A'}</span>
        </div>

        {/* Smart Recommendation */}
        <div className="p-3 bg-indigo-50 rounded-xl border border-indigo-100 mt-2">
          <p className="text-sm text-indigo-900 font-medium leading-relaxed">
            💡 {smartRecommendation}
          </p>
        </div>
      </div>
    </div>
  );
}
