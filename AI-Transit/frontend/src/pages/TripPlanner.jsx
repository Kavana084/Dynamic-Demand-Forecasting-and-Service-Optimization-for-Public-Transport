import React, { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  MapPin, Search, ArrowLeftRight, Loader2,
  AlertTriangle, ChevronDown, ChevronUp,
  Navigation, CheckCircle2,
  ArrowRight, GitBranch,
  Bus, Clock, Zap, CreditCard, Shield, Smile, Star
} from 'lucide-react';
import { planTrip, getStops } from '../api/client';
import RouteMap from '../components/RouteMap';

// ─────────────────────────────────────────
// Helper: passenger-friendly crowd level

// ─────────────────────────────────────────
// Helper: passenger-friendly crowd level

// ─── Occupancy Gauge SVG removed ────────────────────────────────────────────────

// ─── Timeline Stop Item ────────────────────────────────────────────────────────
function TimelineStop({ stop, time, isFirst, isLast, isTransfer, index, isHighlighted }) {
  const dotColor = isFirst ? '#16A34A' : isLast ? '#EF4444' : isTransfer ? '#F59E0B' : '#2563EB';
  return (
    <div className="timeline-stop relative flex gap-3 group" style={{ paddingBottom: isLast ? 0 : 16 }}>
      {/* Line */}
      {!isLast && (
        <div
          className="absolute left-[15px] top-8"
          style={{
            width: 2,
            bottom: 0,
            background: `linear-gradient(to bottom, ${dotColor}55, rgba(148,163,184,0.2))`,
            borderRadius: 2,
          }}
        />
      )}
      {/* Dot */}
      <div className="relative z-10 flex-shrink-0 mt-1" style={{ width: 30 }}>
        <div
          style={{
            width: 30,
            height: 30,
            borderRadius: '50%',
            background: dotColor,
            border: `3px solid ${isHighlighted ? '#fff' : 'transparent'}`,
            boxShadow: isHighlighted ? `0 0 0 3px ${dotColor}55` : `0 2px 6px ${dotColor}44`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {isFirst && <MapPin size={12} color="#fff" />}
          {isLast && <Navigation size={12} color="#fff" />}
          {isTransfer && !isFirst && !isLast && <GitBranch size={10} color="#fff" />}
          {!isFirst && !isLast && !isTransfer && (
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />
          )}
        </div>
      </div>
      {/* Content */}
      <div className="flex-1 pb-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="font-semibold"
            style={{
              fontSize: 13,
              color: isFirst ? '#16A34A' : isLast ? '#EF4444' : isHighlighted ? '#2563EB' : 'var(--st-ink)',
            }}
          >
            {stop}
          </span>
          {isFirst && (
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold" style={{ background: 'rgba(22,163,74,0.15)', color: '#16A34A' }}>
              Start
            </span>
          )}
          {isLast && (
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold" style={{ background: 'rgba(239,68,68,0.15)', color: '#EF4444' }}>
              End
            </span>
          )}
          {isTransfer && !isFirst && !isLast && (
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold" style={{ background: 'rgba(245,158,11,0.15)', color: '#F59E0B' }}>
              Transfer
            </span>
          )}
        </div>
        {time && (
          <span style={{ fontSize: 11, color: 'var(--st-muted)' }}>{time}</span>
        )}
        {isFirst && <p style={{ fontSize: 11, color: 'var(--st-muted)', marginTop: 2 }}>Board your bus here</p>}
        {isLast && <p style={{ fontSize: 11, color: 'var(--st-muted)', marginTop: 2 }}>Get down here</p>}
      </div>
    </div>
  );
}

// ─── Stat Card ─────────────────────────────────────────────────────────────────
function GlanceCard({ icon, label, value, sub, color = '#2563EB' }) {
  return (
    <div
      className="glance-card rounded-2xl p-4 flex flex-col gap-2"
      style={{
        background: 'var(--st-card-bg)',
        border: '1px solid var(--st-card-border)',
        boxShadow: 'var(--st-shadow-sm)',
        transition: 'all 0.2s',
      }}
    >
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center text-base"
        style={{ background: `${color}18`, color }}
      >
        {icon}
      </div>
      <div>
        <p style={{ fontSize: 11, color: 'var(--st-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {label}
        </p>
        <p style={{ fontSize: 20, fontWeight: 800, color: 'var(--st-ink)', lineHeight: 1.2 }}>{value}</p>
        {sub && <p style={{ fontSize: 11, color: 'var(--st-muted)', marginTop: 2 }}>{sub}</p>}
      </div>
    </div>
  );
}

// ─── Section Header ────────────────────────────────────────────────────────────
function SectionHeader({ icon, title, badge }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div
        className="w-8 h-8 rounded-xl flex items-center justify-center"
        style={{ background: 'rgba(37,99,235,0.12)', color: '#2563EB', fontSize: 16 }}
      >
        {icon}
      </div>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--st-ink)' }}>{title}</h2>
      {badge && (
        <span
          className="px-2 py-0.5 rounded-full text-xs font-semibold ml-1"
          style={{ background: 'rgba(37,99,235,0.12)', color: '#2563EB' }}
        >
          {badge}
        </span>
      )}
    </div>
  );
}

// ─── Main Component ────────────────────────────────────────────────────────────
export default function TripPlanner() {
  const [stops, setStops] = useState([]);
  const [formData, setFormData] = useState({ source_id: '', destination_id: '' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stopsLoading, setStopsLoading] = useState(true);
  const [stopsError, setStopsError] = useState('');
  const [error, setError] = useState('');
  const [timelineExpanded, setTimelineExpanded] = useState(true);
  const [selectedAlt, setSelectedAlt] = useState(null);
  

  const currentRouteIdRef = useRef(null);
  const abortControllerRef = useRef(null);
  const searchRef = useRef(null);
  const location = useLocation();

  // ── Load stops ───────────────────────────────────────────────────────────────
  const extractStopsPayload = (response) => {
    if (Array.isArray(response)) return response;
    if (Array.isArray(response?.stops)) return response.stops;
    if (Array.isArray(response?.data)) return response.data;
    if (Array.isArray(response?.results)) return response.results;
    if (Array.isArray(response?.items)) return response.items;
    return [];
  };

  const loadStops = async () => {
    setStopsLoading(true);
    setStopsError('');
    try {
      const response = await getStops();
      const rawStops = extractStopsPayload(response);
      const normalizedStops = Array.from(
        new Map(
          rawStops
            .map((stop) => {
              const stopId = String(stop?.stop_id ?? stop?.id ?? '').trim();
              const stopName = String(stop?.stop_name ?? stop?.name ?? stop?.stop_id ?? stop?.id ?? 'Unknown stop').trim();
              if (!stopId) return null;
              return [stopId, { ...stop, stop_id: stopId, stop_name: stopName }];
            })
            .filter(Boolean)
        ).values()
      ).sort((a, b) => a.stop_name.localeCompare(b.stop_name));

      setStops(normalizedStops);
      if (normalizedStops.length === 0) setStopsError('No stops available right now. Please try again.');
    } catch (err) {
      setStops([]);
      setStopsError('Unable to load stops.');
    } finally {
      setStopsLoading(false);
    }
  };

  useEffect(() => { loadStops(); }, []);

  useEffect(() => {
    currentRouteIdRef.current = result?.route_id;
  }, [result?.route_id]);

  // ── Pre-fill from Route History ──────────────────────────────────────────────
  useEffect(() => {
    const prefill = location.state?.prefill;
    if (prefill) {
      setFormData((prev) => ({
        ...prev,
        ...(prefill.source_id ? { source_id: prefill.source_id } : {}),
        ...(prefill.destination_id ? { destination_id: prefill.destination_id } : {}),
      }));
    }
  }, [location.state]);

  // ── Swap Locations ───────────────────────────────────────────────────────────
  const handleSwap = () => {
    setFormData((prev) => ({
      source_id: prev.destination_id,
      destination_id: prev.source_id,
    }));
  };

  // ── Submit ───────────────────────────────────────────────────────────────────
  const isValid = formData.source_id && formData.destination_id && formData.source_id !== formData.destination_id;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isValid) return;
    console.log("FORM_DATA", formData);
    setLoading(true);
    setError('');
    setResult(null);
    setSelectedAlt(null);
    if (abortControllerRef.current) abortControllerRef.current.abort();
    abortControllerRef.current = new AbortController();
    try {
      console.log("DEBUG_TRIP_PLANNER: Search request payload", formData);
      const data = await planTrip(formData, abortControllerRef.current.signal);
      console.log("API_RESPONSE", data);
      console.log("DEBUG_TRIP_PLANNER: Route API response", data);
      console.log("FULL_ROUTE_RESPONSE", data);
      console.log("DURATION_FIELD", data.duration);
      console.log("ETA_MINUTES_FIELD", data.eta_minutes);
      console.log("ALL_TIME_FIELDS", {
        duration: data.duration,
        eta_minutes: data.eta_minutes,
        total_time: data.total_time,
        journey_time: data.journey_time,
        travel_time: data.travel_time
      });
      console.log("NEXT_ARRIVALS_DEBUG", {
        service_frequency: data.service_frequency,
        next_arrivals: data.service_frequency?.next_arrivals,
        next_arrivals_count: data.service_frequency?.next_arrivals?.length || 0,
      });
      if (data.success === false) { setError(data.message || 'No route found'); return; }

      // ── Phase 0: Pre-flight route_path diagnostic ─────────────────────────
      const rp = data.route_path || [];
      console.group("ROUTE_PATH_DIAGNOSTIC");
      console.log("ROUTE_PATH (full)", rp);
      console.log("ROUTE_GEOMETRY", data.route_geometry); // expected undefined from current backend
      console.log("Length comparison", {
        route_path_length: rp.length,
        stops_length: (data.stops || []).length,
        total_stops: data.total_stops,
      });
      // Duplicate stop detection
      const stopIdCounts = rp.reduce((acc, s) => {
        acc[s.stop_id] = (acc[s.stop_id] || 0) + 1;
        return acc;
      }, {});
      const duplicates = Object.entries(stopIdCounts).filter(([, count]) => count > 1);
      if (duplicates.length > 0) {
        console.warn("DUPLICATE_STOPS_IN_ROUTE_PATH", duplicates);
      } else {
        console.log("No duplicate stops detected in route_path");
      }
      // Null coordinate check
      const nullCoordStops = rp.filter(s => s.lat == null || s.lon == null);
      if (nullCoordStops.length > 0) {
        console.warn("NULL_COORD_STOPS", nullCoordStops);
      } else {
        console.log("All route_path stops have valid lat/lon");
      }
      console.groupEnd();
      // ─────────────────────────────────────────────────────────────────────

      setResult(data);
    } catch (err) {
      console.error("DEBUG_TRIP_PLANNER: Error during trip planning", err);
      if (err.name === 'AbortError') return;
      if (err.status === 404) setError(`Route not found: ${err.message}`);
      else setError(`Failed to plan trip: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // ── Derived values ───────────────────────────────────────────────────────────

  // Prefer backend total_stops > route_path length > stops array length
  const totalStops = result?.total_stops ?? result?.route_path?.length ?? result?.stops?.length ?? 0;
  const transferCount = result?.transfers?.length || 0;
  const distanceKm = result?.total_distance_km || result?.distance_km || 0;
  
  // Travel time: try multiple field names with proper parsing
  let etaMin = result?.eta_min ?? result?.estimated_travel_time ?? 0;
  
  // Fallback calculation if backend returns 0 but distance > 0
  if (etaMin === 0 && distanceKm > 0) {
    etaMin = Math.round(distanceKm * 5); // Rough estimate: 5 min per km
  }
  
  console.log("FRONTEND_TRAVEL_TIME_DEBUG", {
    backend_eta_minutes: result?.eta_minutes,
    backend_duration: result?.duration,
    backend_total_time: result?.total_time,
    backend_journey_time: result?.journey_time,
    backend_travel_time: result?.travel_time,
    parsed_etaMin: etaMin,
    distanceKm: distanceKm
  });

  const fare = result?.fare || result?.fare_estimate || 0;
  // Validation rule
  if (distanceKm > 0 && etaMin === 0) {
    console.warn("INVALID_ROUTE_METRICS", result);
  }

  // Build transfer name set for O(1) lookup in timeline
  const transferStopNames = new Set(
    (result?.transfers || []).map(t => t.stop_name)
  );

  // Generate stop times from route_path (aligned with map data source)
  const timelineStops = result?.route_path || [];
  const stopTimes = timelineStops.map((_, i, arr) => {
    const minutesPerStop = etaMin / Math.max(arr.length - 1, 1);
    const minutesFromStart = Math.round(i * minutesPerStop);
    return `${minutesFromStart} min`;
  });

  const sourceStopName = stops.find(s => String(s.stop_id) === formData.source_id)?.stop_name || '';
  const destStopName = stops.find(s => String(s.stop_id) === formData.destination_id)?.stop_name || '';

  return (
    <div className="trip-planner-root" style={{ display: 'flex', flexDirection: 'column', gap: 0, minHeight: '100%' }}>

      {/* ── SECTION 1: Sticky Search Bar ──────────────────────────────────── */}
      <div
        ref={searchRef}
        className="journey-search-sticky"
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 30,
          background: 'var(--st-bg)',
          borderBottom: '1px solid var(--st-border)',
          padding: '16px 0 12px 0',
          marginBottom: 24,
        }}
      >
        {/* Page Header */}
        <div style={{ marginBottom: 14 }}>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--st-ink)', margin: 0, lineHeight: 1.2 }}>
            Journey Planner
          </h1>
          <p style={{ fontSize: 13, color: 'var(--st-muted)', marginTop: 4 }}>
            Find the best route, know your travel time, and plan better.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            background: 'var(--st-card-bg)',
            border: '1px solid var(--st-card-border)',
            borderRadius: 20,
            boxShadow: 'var(--st-shadow-sm)',
            padding: '16px 20px',
          }}
        >
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            {/* From */}
            <div style={{ flex: '1 1 200px', minWidth: 180 }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: '#2563EB', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
                From
              </label>
              <select
                className="journey-select"
                value={formData.source_id}
                onChange={e => setFormData({ ...formData, source_id: e.target.value })}
                disabled={stopsLoading || stops.length === 0}
                required
                style={{
                  width: '100%',
                  background: 'var(--st-input-bg)',
                  border: '1.5px solid var(--st-input-border)',
                  borderRadius: 12,
                  padding: '10px 14px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--st-ink)',
                  outline: 'none',
                  cursor: 'pointer',
                  transition: 'border-color 0.2s',
                }}
              >
                <option value="">{stopsLoading ? 'Loading stops...' : stops.length === 0 ? 'No stops available' : 'Select departure stop...'}</option>
                {stops.map(stop => (
                  <option key={stop.stop_id} value={stop.stop_id} disabled={String(stop.stop_id) === formData.destination_id}>
                    {stop.stop_name} ({stop.stop_id})
                  </option>
                ))}
              </select>
            </div>

            {/* Swap Button */}
            <button
              type="button"
              onClick={handleSwap}
              disabled={!formData.source_id && !formData.destination_id}
              title="Swap locations"
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                background: 'rgba(37,99,235,0.1)',
                border: '1.5px solid rgba(37,99,235,0.25)',
                color: '#2563EB',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s',
                flexShrink: 0,
              }}
            >
              <ArrowLeftRight size={18} />
            </button>

            {/* To */}
            <div style={{ flex: '1 1 200px', minWidth: 180 }}>
              <label style={{ fontSize: 11, fontWeight: 700, color: '#EF4444', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
                To
              </label>
              <select
                className="journey-select"
                value={formData.destination_id}
                onChange={e => setFormData({ ...formData, destination_id: e.target.value })}
                disabled={stopsLoading || stops.length === 0}
                required
                style={{
                  width: '100%',
                  background: 'var(--st-input-bg)',
                  border: '1.5px solid var(--st-input-border)',
                  borderRadius: 12,
                  padding: '10px 14px',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--st-ink)',
                  outline: 'none',
                  cursor: 'pointer',
                  transition: 'border-color 0.2s',
                }}
              >
                <option value="">{stopsLoading ? 'Loading stops...' : stops.length === 0 ? 'No stops available' : 'Select destination stop...'}</option>
                {stops.map(stop => (
                  <option key={stop.stop_id} value={stop.stop_id} disabled={String(stop.stop_id) === formData.source_id}>
                    {stop.stop_name} ({stop.stop_id})
                  </option>
                ))}
              </select>
            </div>

            

            {/* Search Button */}
            <button
              type="submit"
              disabled={!isValid || loading || stopsLoading || stops.length === 0}
              style={{
                height: 46,
                padding: '0 28px',
                borderRadius: 14,
                background: isValid && !loading ? 'linear-gradient(135deg, #2563EB 0%, #1d4ed8 100%)' : 'var(--st-border)',
                color: isValid && !loading ? '#fff' : 'var(--st-muted)',
                fontWeight: 700,
                fontSize: 14,
                border: 'none',
                cursor: isValid && !loading ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                boxShadow: isValid && !loading ? '0 4px 16px rgba(37,99,235,0.35)' : 'none',
                transition: 'all 0.2s',
                flexShrink: 0,
                whiteSpace: 'nowrap',
              }}
            >
              {loading ? <><Loader2 size={16} className="animate-spin" /> Searching...</> : <><Search size={16} /> Search Journey</>}
            </button>
          </div>

          {/* Error / Status Messages */}
          {error && (
            <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 10, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#EF4444', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={15} /> {error}
            </div>
          )}
          {stopsError && !stopsLoading && (
            <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 10, background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', color: '#F59E0B', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={15} /> {stopsError}
              <button onClick={loadStops} style={{ marginLeft: 'auto', fontWeight: 700, textDecoration: 'underline', background: 'none', border: 'none', color: '#F59E0B', cursor: 'pointer' }}>Retry</button>
            </div>
          )}
        </form>
      </div>

      {/* ── Loading State ──────────────────────────────────────────────────── */}
      {loading && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          padding: '60px 24px',
          background: 'var(--st-card-bg)',
          border: '1px solid var(--st-card-border)',
          borderRadius: 24,
          boxShadow: 'var(--st-shadow-sm)',
          textAlign: 'center',
        }}>
          <div style={{ position: 'relative', width: 64, height: 64 }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'linear-gradient(135deg, rgba(37,99,235,0.15), rgba(37,99,235,0.05))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Loader2 size={28} color="#2563EB" className="animate-spin" />
            </div>
          </div>
          <div>
            <p style={{ fontSize: 18, fontWeight: 800, color: 'var(--st-ink)', marginBottom: 6 }}>Finding the best route for you…</p>
            <p style={{ fontSize: 13, color: 'var(--st-muted)' }}>Analysing live traffic, demand forecast, and bus availability</p>
          </div>
          {/* Animated dots */}
          <div style={{ display: 'flex', gap: 6 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 8, height: 8, borderRadius: '50%', background: '#2563EB',
                animation: `dot-bounce 1.2s ${i * 0.2}s infinite ease-in-out`,
              }} />
            ))}
          </div>
        </div>
      )}

      {/* ── Results ────────────────────────────────────────────────────────── */}
      {result && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* ── SECTION 2: Route Overview ──────────────────────────────────── */}
          <div style={{
            background: 'var(--st-card-bg)',
            border: '1px solid var(--st-card-border)',
            borderRadius: 24,
            boxShadow: 'var(--st-shadow-sm)',
            overflow: 'hidden',
          }}>
            {/* Best Route Badge + Stats Row */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(37,99,235,0.02) 100%)',
              borderBottom: '1px solid var(--st-card-border)',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 12,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px', background: '#2563EB', borderRadius: 20 }}>
                  <Star size={13} color="#fff" />
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>Best Route</span>
                </div>
                <div>
                  <span style={{ fontSize: 36, fontWeight: 900, color: 'var(--st-ink)', lineHeight: 1 }}>{etaMin}</span>
                  <span style={{ fontSize: 14, color: 'var(--st-muted)', marginLeft: 4 }}>min</span>
                </div>
                <span style={{ fontSize: 13, color: 'var(--st-muted)' }}>Total Travel Time</span>
              </div>
              <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
                {[
                  { icon: '📍', label: 'Distance', value: `${distanceKm} km` },
                  { icon: '🚏', label: 'Stops', value: totalStops },
                  { icon: <ArrowLeftRight size={16} />, label: 'Transfers', value: transferCount },
                  { icon: <CreditCard size={16} />, label: 'Fare (Approx.)', value: `₹${fare}` },
                ].map((item) => (
                  <div key={item.label} style={{ textAlign: 'center' }}>
                    <p style={{ fontSize: 11, color: 'var(--st-muted)', marginBottom: 2 }}>{item.icon} {item.label}</p>
                    <p style={{ fontSize: 16, fontWeight: 800, color: 'var(--st-ink)' }}>{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Route Map */}
            <div style={{ width: '100%', minHeight: 360, position: 'relative' }}>
              {(() => {
                // Phase 1 — required spec debug logs
                console.log("ROUTE_PATH_FULL", result?.route_path);
                console.log("ROUTE_GEOMETRY", result?.route_geometry); // undefined until backend adds it
                console.log("ROUTE_PATH_LENGTH", result?.route_path?.length ?? 0);
                console.log("STOPS_LENGTH", result?.stops?.length ?? 0);
                console.log("TOTAL_STOPS_API", result?.total_stops ?? 0);
                
                // Verify duplicates check logic requested by spec
                const stopIds = result?.route_path?.map(s => s.stop_id) || [];
                const uniqueIds = new Set(stopIds);
                console.log("HAS_DUPLICATES", stopIds.length !== uniqueIds.size);
                
                return result?.route_path?.length > 0;
              })() ? (
                <RouteMap
                  routePath={result.route_path}
                  transfers={result.transfers}
                  polyline={result.polyline}
                  stats={{
                    totalStops,
                    distanceKm,
                    etaMin,
                    routeId: result.route_path?.[0]?.route_id
                  }}
                />
              ) : (
                <div style={{ minHeight: 360, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, color: 'var(--st-muted)' }}>
                  <MapPin size={40} color="var(--st-muted-2)" />
                  <p style={{ fontSize: 14, fontWeight: 500 }}>Route map not available for this journey.</p>
                </div>
              )}
            </div>

            {/* Live Traffic Strip */}
            {result?.context?.traffic && (
              <div style={{
                borderTop: '1px solid var(--st-card-border)',
                padding: '10px 20px',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: 'var(--st-bg)',
              }}>
                <span style={{ fontSize: 12, color: 'var(--st-muted)', fontWeight: 600 }}>Live Traffic:</span>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  padding: '3px 10px', borderRadius: 20,
                  background: result.context.traffic === 'Low' ? 'rgba(22,163,74,0.12)' : result.context.traffic === 'High' ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.12)',
                  color: result.context.traffic === 'Low' ? '#16A34A' : result.context.traffic === 'High' ? '#EF4444' : '#F59E0B',
                  fontSize: 12, fontWeight: 700,
                }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }} />
                  {result.context.traffic}
                </span>
              </div>
            )}
          </div>

          {/* ── SECTION 3 & 4 removed ─────────────── */}

          {/* ── SECTION 5: Journey Timeline ─────────────────────────────────── */}
          <div style={{
            background: 'var(--st-card-bg)',
            border: '1px solid var(--st-card-border)',
            borderRadius: 24,
            boxShadow: 'var(--st-shadow-sm)',
            overflow: 'hidden',
          }}>
            {/* Sticky Timeline Header */}
            <div style={{
              position: 'sticky',
              top: 0,
              zIndex: 5,
              background: 'var(--st-card-bg)',
              borderBottom: '1px solid var(--st-card-border)',
              padding: '14px 20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 32, height: 32, borderRadius: 10, background: 'rgba(37,99,235,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span style={{ fontSize: 16 }}>🚏</span>
                </div>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--st-ink)', margin: 0 }}>Your Journey</h2>
                {totalStops > 0 && (
                  <span style={{ padding: '2px 10px', borderRadius: 20, background: 'rgba(37,99,235,0.12)', color: '#2563EB', fontSize: 12, fontWeight: 700 }}>
                    {totalStops} Stops
                  </span>
                )}
              </div>
              <button
                onClick={() => setTimelineExpanded(p => !p)}
                style={{ display: 'flex', alignItems: 'center', gap: 5, background: 'none', border: 'none', color: '#2563EB', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
              >
                {timelineExpanded ? <><ChevronUp size={16} /> Collapse</> : <><ChevronDown size={16} /> View all stops</>}
              </button>
            </div>

            {/* Timeline Body — driven by route_path (same data source as the map) */}
            <div style={{ padding: '20px 24px', maxHeight: timelineExpanded ? 600 : 220, overflow: 'auto', transition: 'max-height 0.4s ease' }}>
              {timelineStops.length > 0 ? (
                <div>
                  {(timelineExpanded ? timelineStops : timelineStops.slice(0, 3)).map((stop, idx) => {
                    // Transfer: use route_path's own is_transfer flag OR check transfers list by name
                    const isTransfer = stop.is_transfer === true || transferStopNames.has(stop.stop_name);
                    return (
                      <TimelineStop
                        key={stop.stop_id ? `${stop.stop_id}-${idx}` : idx}
                        stop={stop.stop_name}
                        time={stopTimes[idx]}
                        isFirst={idx === 0}
                        isLast={idx === timelineStops.length - 1}
                        isTransfer={isTransfer}
                        index={idx}
                      />
                    );
                  })}
                  {!timelineExpanded && timelineStops.length > 3 && (
                    <div style={{ color: 'var(--st-muted)', fontSize: 12, paddingLeft: 42, paddingTop: 4 }}>
                      + {timelineStops.length - 3} more stops
                    </div>
                  )}
                </div>
              ) : result?.stops?.length > 0 ? (
                // Fallback: render plain stops strings if route_path is absent
                <div>
                  {(timelineExpanded ? result.stops : result.stops.slice(0, 3)).map((stopName, idx) => (
                    <TimelineStop
                      key={idx}
                      stop={stopName}
                      time={stopTimes[idx]}
                      isFirst={idx === 0}
                      isLast={idx === result.stops.length - 1}
                      isTransfer={false}
                      index={idx}
                    />
                  ))}
                  {!timelineExpanded && result.stops.length > 3 && (
                    <div style={{ color: 'var(--st-muted)', fontSize: 12, paddingLeft: 42, paddingTop: 4 }}>
                      + {result.stops.length - 3} more stops
                    </div>
                  )}
                </div>
              ) : (
                <p style={{ color: 'var(--st-muted)', fontSize: 13, fontStyle: 'italic' }}>No stop details available.</p>
              )}
            </div>
          </div>

          {/* ── SECTION 6: Next Buses ─────────────────────────────────────────── */}
          <div>
            <SectionHeader icon={<Bus size={16} />} title="Next Buses" />
            <div style={{
              background: 'var(--st-card-bg)',
              border: '1px solid var(--st-card-border)',
              borderRadius: 16,
              padding: '16px 20px',
              boxShadow: 'var(--st-shadow-sm)',
            }}>
              {result?.service_frequency?.next_arrivals && result.service_frequency.next_arrivals.length > 0 ? (
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {result.service_frequency.next_arrivals.map((arrival, idx) => (
                    <div key={idx} style={{
                      padding: '8px 16px',
                      background: 'rgba(37,99,235,0.08)',
                      border: '1px solid rgba(37,99,235,0.2)',
                      borderRadius: 10,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}>
                      <Bus size={14} color="#2563EB" />
                      <span style={{ fontSize: 14, fontWeight: 700, color: '#2563EB' }}>
                        Bus #{arrival.bus_number || idx + 1}: {arrival.arrival_time}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ color: 'var(--st-muted)', fontSize: 13 }}>
                  No next bus information available
                </div>
              )}
            </div>
          </div>

          {/* ── SECTION 7: Trip At a Glance ─────────────────────────────────── */}
          <div>
            <SectionHeader icon={<Zap size={16} />} title="Trip At a Glance" />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 14 }}>
              <GlanceCard icon={<Clock size={16} />} label="Time" value={`${etaMin} min`} color="#2563EB" />
              <GlanceCard icon="📍" label="Distance" value={`${distanceKm} km`} color="#8B5CF6" />
              <GlanceCard icon={<ArrowLeftRight size={16} />} label="Transfers" value={transferCount} sub={transferCount === 0 ? 'Direct route' : 'Transfers required'} color="#EF4444" />
            </div>
          </div>

          {/* Bottom padding */}
          <div style={{ height: 24 }} />
        </div>
      )}

      {/* ── Empty State ─────────────────────────────────────────────────────── */}
      {!result && !loading && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          padding: '60px 24px',
          background: 'var(--st-card-bg)',
          border: '1px solid var(--st-card-border)',
          borderRadius: 24,
          boxShadow: 'var(--st-shadow-sm)',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 64 }}>🗺️</div>
          <div>
            <p style={{ fontSize: 20, fontWeight: 800, color: 'var(--st-ink)', marginBottom: 8 }}>Ready to Plan Your Journey?</p>
            <p style={{ fontSize: 14, color: 'var(--st-muted)', maxWidth: 380, lineHeight: 1.6 }}>
              Select your departure and destination stops above to discover the best route, expected crowd levels, and comfort insights.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
            {['👥 Crowd predictions', '🗺️ Route visualization'].map(feat => (
              <span key={feat} style={{ padding: '6px 14px', borderRadius: 20, background: 'rgba(37,99,235,0.08)', color: '#2563EB', fontSize: 12, fontWeight: 600 }}>
                {feat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Inline CSS ──────────────────────────────────────────────────────── */}
      <style>{`
        @keyframes dot-bounce {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
          40% { transform: scale(1); opacity: 1; }
        }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        .glance-card:hover {
          transform: translateY(-3px);
          box-shadow: var(--st-shadow-md) !important;
        }
        .why-card:hover {
          transform: translateY(-3px);
          box-shadow: var(--st-shadow-md) !important;
        }
        .alt-route-card:hover {
          transform: translateY(-2px);
        }
        .journey-select:focus {
          border-color: #2563EB !important;
          box-shadow: 0 0 0 3px rgba(37,99,235,0.15);
        }
        .timeline-stop:hover .font-semibold {
          color: #2563EB;
        }
      `}</style>
    </div>
  );
}
