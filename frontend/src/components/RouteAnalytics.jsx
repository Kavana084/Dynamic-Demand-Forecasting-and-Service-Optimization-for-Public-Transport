import React, { useMemo } from 'react';
import {
  Activity, ShieldAlert, Clock, BarChart2,
  AlertTriangle, CheckCircle, TrendingUp, TrendingDown,
  Navigation, AlertOctagon, Info
} from 'lucide-react';

function getDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

function StatBadge({ label, value, color = 'blue' }) {
  const colors = {
    blue:   { bg: 'bg-blue-50',   border: 'border-blue-100',   text: 'text-blue-700',   label: 'text-blue-500'   },
    green:  { bg: 'bg-emerald-50', border: 'border-emerald-100', text: 'text-emerald-700', label: 'text-emerald-500' },
    purple: { bg: 'bg-purple-50', border: 'border-purple-100', text: 'text-purple-700', label: 'text-purple-500' },
    orange: { bg: 'bg-orange-50', border: 'border-orange-100', text: 'text-orange-700', label: 'text-orange-500' },
    red:    { bg: 'bg-red-50', border: 'border-red-100', text: 'text-red-700', label: 'text-red-500' },
  };
  const c = colors[color] || colors.blue;
  return (
    <div className={`${c.bg} ${c.border} border rounded-xl p-4 flex flex-col items-center text-center`}>
      <p className={`text-xs font-semibold uppercase tracking-wider ${c.label} mb-1`}>{label}</p>
      <p className={`text-2xl font-extrabold ${c.text}`}>{value}</p>
    </div>
  );
}

export default function RouteAnalytics({
  result,
  wsData,
  initialEta,
  currentEta,
  resolvedIndex
}) {
  const traffic = wsData?.traffic ?? result?.context?.traffic ?? 'Medium';
  const trafficLower = traffic.toLowerCase();
  const rawOccupancy = wsData?.occupancy_percent ?? result?.occupancy_percent ?? 0;
  const occupancy = Math.max(0, Math.min(100, rawOccupancy));
  if (rawOccupancy > 100 || rawOccupancy < 0) {
    console.warn(`[Analytics Warning] Occupancy out of bounds: ${rawOccupancy}. Clamped to ${occupancy}.`);
  }
  const transferCount = result?.transfers?.length || 0;
  const routePath = result?.route_path || [];

  // --- 1. Route Health Score ---
  const healthScore = useMemo(() => {
    let score = 100;
    
    // Traffic penalty
    if (trafficLower === 'medium') score -= 10;
    if (trafficLower === 'high' || trafficLower === 'heavy') score -= 25;

    // Occupancy penalty
    if (occupancy > 50 && occupancy <= 80) score -= 5;
    if (occupancy > 80) score -= 15;

    // Transfers penalty
    score -= (5 * transferCount);

    // ETA Increase penalty
    if (initialEta !== null && currentEta > initialEta) {
      score -= (currentEta - initialEta);
    }

    const finalScore = Math.max(0, Math.min(100, score));
    if (score > 100 || score < 0) {
      console.warn(`[Analytics Warning] Health score out of bounds: ${score}. Clamped to ${finalScore}.`);
    }
    return finalScore;
  }, [trafficLower, occupancy, transferCount, initialEta, currentEta]);

  const healthLabel = useMemo(() => {
    if (healthScore >= 90) return { text: 'Excellent', color: 'green' };
    if (healthScore >= 75) return { text: 'Good', color: 'blue' };
    if (healthScore >= 60) return { text: 'Moderate', color: 'orange' };
    return { text: 'Congested', color: 'red' };
  }, [healthScore]);

  // --- 2. Delay Prediction ---
  const delayProbability = useMemo(() => {
    if (wsData?.delay_minutes !== undefined) {
       return Math.min(100, Math.round((wsData.delay_minutes / Math.max(1, currentEta)) * 100));
    }
    if (initialEta === null) return 0;
    const rawDelay = Math.abs(currentEta - initialEta) * 5;
    const prob = Math.max(0, Math.min(100, rawDelay));
    if (rawDelay > 100) {
      console.warn(`[Analytics Warning] Delay probability out of bounds: ${rawDelay}. Clamped to 100.`);
    }
    return prob;
  }, [initialEta, currentEta, wsData?.delay_minutes]);

  const expectedArrival = useMemo(() => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + currentEta);
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, [currentEta]);

  // --- 3. Transfer Risk ---
  const transferRisk = useMemo(() => {
    if (transferCount === 0) return { level: 'Low', color: 'green' };
    if (transferCount === 1) {
      if (trafficLower === 'low') return { level: 'Low', color: 'green' };
      if (trafficLower === 'medium') return { level: 'Medium', color: 'orange' };
      return { level: 'High', color: 'red' };
    }
    // 2+ transfers
    if (trafficLower === 'medium' || trafficLower === 'high' || trafficLower === 'heavy') {
      return { level: 'High', color: 'red' };
    }
    return { level: 'Medium', color: 'orange' };
  }, [transferCount, trafficLower]);

  // --- 4. Transit Performance Dashboard (KPIs) ---
  const journeyEfficiency = 100 - delayProbability;
  const routeReliability = healthScore;
  const demandLoad = occupancy;
  const trafficPressure = trafficLower === 'high' || trafficLower === 'heavy' ? 90 : trafficLower === 'medium' ? 60 : 20;

  // --- 5. Segment Analytics ---
  const nextSegments = useMemo(() => {
    const segments = [];
    // Display next 3 segments starting from resolvedIndex
    for (let i = resolvedIndex; i < Math.min(resolvedIndex + 3, routePath.length - 1); i++) {
      const stop1 = routePath[i];
      const stop2 = routePath[i+1];
      const dist = getDistance(stop1.lat, stop1.lon, stop2.lat, stop2.lon).toFixed(2);
      segments.push({
        from: stop1.stop_name,
        to: stop2.stop_name,
        distance: dist,
        trafficImpact: traffic
      });
    }
    return segments;
  }, [resolvedIndex, routePath, traffic]);

  // --- 6. Route Insights ---
  const insights = useMemo(() => {
    const lines = [];
    const etaDiff = initialEta !== null ? initialEta - currentEta : 0;
    
    if (etaDiff > 0) {
      lines.push('Traffic conditions improving.');
      lines.push(`ETA reduced by ${etaDiff} minutes.`);
    }

    if (trafficLower === 'high' || trafficLower === 'heavy') {
      lines.push('Congestion detected on upcoming route segments.');
    }
    if (transferRisk.level === 'Low') {
      lines.push('Transfer operations currently stable.');
    }
    return lines.slice(0, 4);
  }, [initialEta, currentEta, occupancy, trafficLower, transferRisk.level]);

  // --- 7. Predictive Alerts ---
  const alerts = [];
  if (trafficLower === 'high' || trafficLower === 'heavy') {
    alerts.push('High congestion expected ahead.');
  }
  if (delayProbability > 40) {
    alerts.push('Potential service delay detected.');
  }


  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 px-1">
        <Activity className="w-5 h-5 text-indigo-600" />
        <h2 className="text-lg font-bold text-slate-800">Executive Analytics Dashboard</h2>
      </div>

      {/* Predictive Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert, idx) => (
            <div key={idx} className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-xl">
              <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
              <p className="text-sm font-bold text-red-700">{alert}</p>
            </div>
          ))}
        </div>
      )}

      {/* Top Row: Health, Delay, Transfer */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Route Health Score */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col items-center justify-center">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Route Health Score</p>
          <div className="flex items-end gap-1 mb-1">
            <span className={`text-4xl font-extrabold ${
              healthLabel.color === 'green' ? 'text-emerald-600' :
              healthLabel.color === 'blue' ? 'text-blue-600' :
              healthLabel.color === 'orange' ? 'text-orange-600' : 'text-red-600'
            }`}>
              {healthScore}
            </span>
            <span className="text-slate-400 font-bold mb-1">/ 100</span>
          </div>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
            healthLabel.color === 'green' ? 'bg-emerald-100 text-emerald-700' :
            healthLabel.color === 'blue' ? 'bg-blue-100 text-blue-700' :
            healthLabel.color === 'orange' ? 'bg-orange-100 text-orange-700' : 'bg-red-100 text-red-700'
          }`}>
            {healthLabel.text}
          </span>
        </div>

        {/* Delay Prediction */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col items-center justify-center text-center">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Delay Forecast</p>
          <div className="flex flex-col gap-2 w-full">
            <div className="bg-orange-50 rounded-lg p-2 border border-orange-100">
              <p className="text-xs text-orange-400">Predicted Delay</p>
              <p className="text-lg font-bold text-orange-700">{wsData?.delay_minutes !== undefined ? `${wsData.delay_minutes} min` : '--'}</p>
            </div>
            <div className="bg-indigo-50 rounded-lg p-2 border border-indigo-100">
              <p className="text-xs text-indigo-400">Prediction Confidence</p>
              <p className="text-lg font-bold text-indigo-700">{wsData?.eta_confidence !== undefined ? `${Math.round(wsData.eta_confidence * 100)}%` : '--'}</p>
            </div>
          </div>
        </div>

        {/* Transfer Risk */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 flex flex-col items-center justify-center">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Transfer Risk</p>
          <ShieldAlert className={`w-8 h-8 mb-2 ${
            transferRisk.color === 'green' ? 'text-emerald-500' :
            transferRisk.color === 'orange' ? 'text-orange-500' : 'text-red-500'
          }`} />
          <span className={`text-xl font-extrabold ${
            transferRisk.color === 'green' ? 'text-emerald-600' :
            transferRisk.color === 'orange' ? 'text-orange-600' : 'text-red-600'
          }`}>
            {transferRisk.level}
          </span>
        </div>
      </div>

      {/* Second Row: KPI Dashboard */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5">
        <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-primary" /> Transit Performance Dashboard
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatBadge label="Journey Efficiency" value={`${Math.round(journeyEfficiency)}%`} color="blue" />
          <StatBadge label="Route Reliability" value={`${healthScore}%`} color="green" />
          <StatBadge label="Traffic Pressure" value={`${trafficPressure}%`} color={trafficPressure > 60 ? 'red' : 'orange'} />
        </div>
      </div>

      {/* Third Section: Segment Analytics */}
      {nextSegments.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
            <Navigation className="w-4 h-4 text-emerald-500" /> Segment Analytics
          </h3>
          <div className="space-y-3">
            {nextSegments.map((seg, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 bg-slate-50 border border-slate-100 rounded-xl gap-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-slate-700">{seg.from}</span>
                  <span className="text-slate-400">→</span>
                  <span className="text-sm font-bold text-slate-700">{seg.to}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  <div className="bg-white px-3 py-1 rounded-md border border-slate-200 text-slate-600">
                    <span className="text-slate-400 mr-1">Distance:</span>
                    <span className="font-bold">{seg.distance} km</span>
                  </div>
                  <div className="bg-white px-3 py-1 rounded-md border border-slate-200 text-slate-600">
                    <span className="text-slate-400 mr-1">Traffic Impact:</span>
                    <span className={`font-bold ${
                      seg.trafficImpact.toLowerCase() === 'high' || seg.trafficImpact.toLowerCase() === 'heavy' ? 'text-red-500' :
                      seg.trafficImpact.toLowerCase() === 'medium' ? 'text-orange-500' : 'text-emerald-500'
                    }`}>{seg.trafficImpact}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Fourth Section: Route Insights */}
      {insights.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-2xl p-5">
          <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
            <Info className="w-4 h-4 text-blue-500" /> Route Insights
          </h3>
          <ul className="space-y-2">
            {insights.map((insight, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                <span className="text-sm text-slate-600">{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
