import { Footprints, Bus, ArrowRight, MapPin, Clock } from 'lucide-react';

export default function JourneyTimeline({ 
  source, 
  destination, 
  etaMinutes,
  stops,
  transfers 
}) {
  const walkingTimeMinutes = 5; // Estimated walking time
  const now = new Date();
  
  // Calculate arrival times at each stage
  const walkArrival = new Date(now.getTime() + walkingTimeMinutes * 60000);
  const busArrival = new Date(walkArrival.getTime() + etaMinutes * 60000);
  
  const formatTime = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const hasTransfers = transfers && transfers.length > 0;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-500" />
          Journey Timeline
        </h3>
      </div>

      <div className="space-y-0">
        {/* Walk to Stop */}
        <div className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 rounded-full bg-emerald-100 border-2 border-emerald-300 flex items-center justify-center">
              <Footprints className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="w-0.5 h-12 bg-slate-200 mt-2"></div>
          </div>
          <div className="flex-1 pb-4">
            <div className="text-sm font-semibold text-slate-800">Walk to Stop</div>
            <div className="text-xs text-slate-500 mt-1">{source}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-slate-600">Arrive by</span>
              <span className="text-xs font-bold text-emerald-700">{formatTime(walkArrival)}</span>
            </div>
          </div>
        </div>

        {/* Board Bus */}
        <div className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 rounded-full bg-blue-100 border-2 border-blue-300 flex items-center justify-center">
              <Bus className="w-4 h-4 text-blue-600" />
            </div>
            <div className="w-0.5 h-12 bg-slate-200 mt-2"></div>
          </div>
          <div className="flex-1 pb-4">
            <div className="text-sm font-semibold text-slate-800">Board Bus</div>
            <div className="text-xs text-slate-500 mt-1">Route to {destination}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-slate-600">Travel time</span>
              <span className="text-xs font-bold text-blue-700">{etaMinutes} min</span>
            </div>
          </div>
        </div>

        {/* Transfer (if any) */}
        {hasTransfers && (
          <div className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className="w-8 h-8 rounded-full bg-amber-100 border-2 border-amber-300 flex items-center justify-center">
                <ArrowRight className="w-4 h-4 text-amber-600" />
              </div>
              <div className="w-0.5 h-12 bg-slate-200 mt-2"></div>
            </div>
            <div className="flex-1 pb-4">
              <div className="text-sm font-semibold text-slate-800">Transfer</div>
              <div className="text-xs text-slate-500 mt-1">{transfers.length} transfer(s)</div>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-600">Change at</span>
                <span className="text-xs font-bold text-amber-700">Transfer Point</span>
              </div>
            </div>
          </div>
        )}

        {/* Destination */}
        <div className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 rounded-full bg-indigo-100 border-2 border-indigo-300 flex items-center justify-center">
              <MapPin className="w-4 h-4 text-indigo-600" />
            </div>
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-slate-800">Arrive at Destination</div>
            <div className="text-xs text-slate-500 mt-1">{destination}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-slate-600">ETA</span>
              <span className="text-xs font-bold text-indigo-700">{formatTime(busArrival)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Total Journey Time */}
      <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-600 font-medium">Total Journey Time</span>
          <span className="text-sm font-bold text-slate-800">
            {walkingTimeMinutes + etaMinutes} min
          </span>
        </div>
      </div>
    </div>
  );
}
