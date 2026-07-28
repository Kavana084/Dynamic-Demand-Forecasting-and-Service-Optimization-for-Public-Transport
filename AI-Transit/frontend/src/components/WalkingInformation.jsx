import { Footprints, MapPin, Clock } from 'lucide-react';

export default function WalkingInformation({ 
  source,
  distanceKm,
  etaMinutes
}) {
  // Estimate walking time (assuming average walking speed of 5 km/h)
  const walkingTimeMinutes = distanceKm ? Math.round((distanceKm / 5) * 60) : 5;
  const walkingDistanceKm = distanceKm || 0.5;
  const arrivalTime = new Date(Date.now() + walkingTimeMinutes * 60000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
          <Footprints className="w-4 h-4 text-emerald-500" />
          Walking Information
        </h3>
      </div>

      <div className="space-y-3">
        {/* Walking Time */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-500" />
            <span className="text-xs text-slate-600 font-medium">Walking Time</span>
          </div>
          <span className="text-sm font-bold text-slate-800">{walkingTimeMinutes} min</span>
        </div>

        {/* Walking Distance */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-slate-500" />
            <span className="text-xs text-slate-600 font-medium">Walking Distance</span>
          </div>
          <span className="text-sm font-bold text-slate-800">{walkingDistanceKm.toFixed(1)} km</span>
        </div>

        {/* Estimated Arrival at Stop */}
        <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-xl border border-emerald-100">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-emerald-500" />
            <span className="text-xs text-emerald-700 font-medium">Arrive at Stop</span>
          </div>
          <span className="text-sm font-bold text-emerald-800">{arrivalTime}</span>
        </div>

        {/* Origin Stop */}
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
          <div className="text-xs text-slate-500 font-medium mb-1">From</div>
          <div className="text-sm font-semibold text-slate-800">{source}</div>
        </div>
      </div>
    </div>
  );
}
