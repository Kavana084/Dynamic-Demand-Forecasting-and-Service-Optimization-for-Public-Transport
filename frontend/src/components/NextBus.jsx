import { Bus, MapPin, Clock, Navigation } from 'lucide-react';

export default function NextBus({ 
  routeId, 
  routeName, 
  destination, 
  etaMinutes, 
  liveBuses
}) {
  const nextBus = liveBuses?.[0] || {};
  const busNumber = nextBus.bus_id || 'KA-07-F-4206';
  const busStatus = nextBus.status || 'In Transit';
  const currentLocation = nextBus.current_location || 'Approaching';
  return (
    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl p-5 shadow-lg text-white">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold flex items-center gap-2">
          <Bus className="w-4 h-4" />
          Next Bus
        </h3>
        <span className="text-xs bg-white/20 px-2 py-1 rounded-full">Live</span>
      </div>

      {/* Route Number */}
      <div className="mb-4">
        <div className="text-3xl font-extrabold">{routeName || routeId || '500D'}</div>
        <div className="text-sm text-white/80 flex items-center gap-1 mt-1">
          <MapPin className="w-3 h-3" />
          {destination || 'Majestic'}
        </div>
      </div>

      {/* ETA */}
      <div className="bg-white/10 rounded-xl p-4 mb-4 backdrop-blur-sm">
        <div className="text-xs text-white/70 mb-1">Arriving in</div>
        <div className="text-4xl font-extrabold">{etaMinutes || 4} min</div>
      </div>

      {/* Bus Details */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-white/70">Bus Number</span>
          <span className="font-semibold">{busNumber}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-white/70">Status</span>
          <span className="font-semibold flex items-center gap-1">
            <Navigation className="w-3 h-3" />
            {busStatus}
          </span>
        </div>
      </div>
    </div>
  );
}
