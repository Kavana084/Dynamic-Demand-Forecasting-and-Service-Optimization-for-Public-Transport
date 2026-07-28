import { CheckCircle2, AlertTriangle, XCircle, Clock, Cloud, Wrench } from 'lucide-react';

export default function ServiceStatus({ 
  traffic, 
  weather, 
  etaMinutes,
  delayMinutes = 0
}) {
  const getServiceStatus = () => {
    // Determine service status based on traffic, weather, and delay
    const hasHeavyTraffic = traffic?.toLowerCase().includes('heavy');
    const hasBadWeather = weather?.toLowerCase().includes('rain') || weather?.toLowerCase().includes('storm');
    const hasSignificantDelay = delayMinutes > 10;

    if (hasSignificantDelay && (hasHeavyTraffic || hasBadWeather)) {
      return { status: 'Major Delay', color: 'red', icon: XCircle };
    }
    if (hasSignificantDelay || hasHeavyTraffic) {
      return { status: 'Minor Delay', color: 'amber', icon: AlertTriangle };
    }
    if (hasBadWeather) {
      return { status: 'Minor Delay', color: 'amber', icon: Cloud };
    }
    return { status: 'Running Normally', color: 'emerald', icon: CheckCircle2 };
  };

  const getDelayReason = () => {
    const reasons = [];
    if (traffic?.toLowerCase().includes('heavy')) {
      reasons.push('heavy traffic');
    }
    if (weather?.toLowerCase().includes('rain')) {
      reasons.push('rain');
    }
    if (weather?.toLowerCase().includes('storm')) {
      reasons.push('storm');
    }
    if (delayMinutes > 0 && reasons.length === 0) {
      reasons.push('operational delays');
    }
    return reasons.length > 0 ? reasons.join(', ') : null;
  };

  const statusInfo = getServiceStatus();
  const StatusIcon = statusInfo.icon;
  const delayReason = getDelayReason();
  const lastUpdated = new Date().toLocaleTimeString();

  const statusColors = {
    emerald: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    red: 'bg-red-50 border-red-200 text-red-700',
  };

  const iconColors = {
    emerald: 'text-emerald-500',
    amber: 'text-amber-500',
    red: 'text-red-500',
  };

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-2xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-blue-800 flex items-center gap-2">
          <StatusIcon className={`w-4 h-4 ${iconColors[statusInfo.color]}`} />
          Service Status
        </h3>
        <span className="text-xs text-blue-500">Updated {lastUpdated}</span>
      </div>

      {/* Status Badge */}
      <div className={`flex items-center gap-2 px-4 py-3 rounded-xl border ${statusColors[statusInfo.color]} mb-4`}>
        <StatusIcon className={`w-5 h-5 ${iconColors[statusInfo.color]}`} />
        <span className="text-lg font-bold capitalize">{statusInfo.status}</span>
      </div>

      {/* Delay Information */}
      {delayMinutes > 0 && (
        <div className="bg-white rounded-xl p-4 border border-blue-100 mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-blue-600 font-medium">Delay Duration</span>
            <span className="text-sm font-bold text-blue-900">{delayMinutes} min</span>
          </div>
          {delayReason && (
            <div className="flex items-center gap-2 mt-2">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              <span className="text-xs text-blue-600">Reason: {delayReason}</span>
            </div>
          )}
        </div>
      )}

      {/* Conditions */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-xl p-3 border border-blue-100">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-3 h-3 text-blue-500" />
            <span className="text-xs text-blue-600 font-medium">ETA</span>
          </div>
          <span className="text-sm font-bold text-blue-900">{etaMinutes} min</span>
        </div>
        <div className="bg-white rounded-xl p-3 border border-blue-100">
          <div className="flex items-center gap-2 mb-1">
            <Cloud className="w-3 h-3 text-blue-500" />
            <span className="text-xs text-blue-600 font-medium">Weather</span>
          </div>
          <span className="text-sm font-bold text-blue-900 capitalize">
            {weather?.split(',')[0] || 'Clear'}
          </span>
        </div>
      </div>
    </div>
  );
}
