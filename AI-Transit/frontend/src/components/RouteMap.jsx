/**
 * RouteMap.jsx
 * Reusable interactive Leaflet map for route visualization.
 *
 * Props
 * ─────
 * routePath    {Array}  – [{stop_name, lat, lon, route_id, is_transfer}, ...]
 * transfers    {Array}  – [{stop_name, from_route, to_route}, ...]
 * polyline     {Array}  – [[lat, lon], ...] optional pre-computed coordinates
 *
 * All props are optional; the component renders a safe empty state when absent.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  Tooltip,
  ZoomControl,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// ─── Fix Leaflet's default icon path issue with Vite bundling ────────────────
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl:
    'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// ─── Custom div-icon factory ─────────────────────────────────────────────────
function makeDivIcon({ bg, border, text, label, size = 32 }) {
  const half = size / 2;
  return L.divIcon({
    className: '',
    iconSize:   [size, size],
    iconAnchor: [half, half],
    popupAnchor:[0, -half - 4],
    html: `
      <div style="
        width:${size}px; height:${size}px;
        background:${bg}; border:2.5px solid ${border};
        border-radius:50%; display:flex; align-items:center;
        justify-content:center; box-shadow:0 2px 6px rgba(0,0,0,.25);
        font-family:Inter,sans-serif; font-size:9px; font-weight:700;
        color:${text}; text-align:center; line-height:1.1;
        user-select:none;
      ">${label}</div>`,
  });
}

// Pre-built static icons (created once, never recreated on live updates) ──────
const SOURCE_ICON = makeDivIcon({
  bg: '#10b981', border: '#065f46', text: '#fff', label: 'START', size: 38,
});

const DEST_ICON = makeDivIcon({
  bg: '#ef4444', border: '#991b1b', text: '#fff', label: 'END', size: 38,
});

const TRANSFER_ICON = makeDivIcon({
  bg: '#f97316', border: '#9a3412', text: '#fff', label: '⇄', size: 34,
});

function getStopIcon(index) {
  return makeDivIcon({
    bg: '#2563EB', border: '#1e3a8a', text: '#fff', label: String(index), size: 24,
  });
}

// ─── Map auto-fit helper (runs once per new routePath) ───────────────────────
function FitBounds({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (!positions || positions.length === 0) return;
    if (positions.length === 1) {
      map.setView(positions[0], 14, { animate: true });
      return;
    }
    const bounds = L.latLngBounds(positions);
    map.fitBounds(bounds, { padding: [48, 48], animate: true, maxZoom: 15 });
  }, [map, positions]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function RouteMap({
  routePath = [],
  transfers = [],
  polyline = [],
  stats = null,
}) {
  console.log("ROUTEMAP_PROPS", { routePath, polyline, transfers });
  // Phase 5 — MAP_STOP_COUNT: total markers that will be rendered (start + mid + end)
  console.log("MAP_STOP_COUNT", routePath.length);

  const [visibleStops, setVisibleStops] = useState(0);

  useEffect(() => {
    if (!routePath || routePath.length === 0) return;
    setVisibleStops(1);
    
    // Playback animation
    const interval = setInterval(() => {
      setVisibleStops((prev) => {
        if (prev >= routePath.length) {
          clearInterval(interval);
          return routePath.length;
        }
        return prev + 1;
      });
    }, 400); // Reveal one stop every 400ms

    return () => clearInterval(interval);
  }, [routePath]);

  // ── Derived map data (stable: only changes when routePath changes) ───────────
  const transferNames = useMemo(
    () => new Set(Array.isArray(transfers) ? transfers.map((t) => t.stop_name) : []),
    [transfers]
  );

  const polylinePositions = useMemo(
    () => {
      if (polyline && polyline.length > 0) {
        return polyline;
      }
      return routePath.slice(0, visibleStops).map((s) => [s.lat, s.lon]);
    },
    [routePath, polyline, visibleStops]
  );

  const tileUrl = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

  // ── Empty state guard ─────────────────────────────────────────────────────
  if (!routePath || routePath.length === 0) {
    return (
      <div
        style={{ minHeight: 450 }}
        className="w-full flex flex-col items-center justify-center
                   rounded-2xl border border-dashed border-border
                   bg-background/60 gap-3 text-muted"
      >
        <svg
          className="w-10 h-10 text-slate-300"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 13l4.553 2.276A1 1 0 0021 21.382V10.618a1 1 0 00-.553-.894L15 7m0 13V7m0 0L9 7"
          />
        </svg>
        <p className="text-sm font-medium">No route available for map visualization.</p>
        <p className="text-xs text-muted-2">Plan a trip above to see the interactive map.</p>
      </div>
    );
  }

  const first = routePath[0];
  const last = routePath[routePath.length - 1];
  const midStops = routePath.slice(1, -1);

  const mapCenter =
    routePath?.length > 0
      ? [routePath[0].lat, routePath[0].lon]
      : [12.9716, 77.5946];

  return (
    <div
      className="w-full rounded-2xl overflow-hidden border border-border shadow-st-sm"
      style={{ minHeight: 450 }}
    >
      {/* ── Legend bar ── */}
      <div className="flex flex-wrap items-center gap-4 px-4 py-2.5
                      bg-surface border-b border-border text-xs font-medium text-muted relative">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> Start
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> Destination
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-orange-400 inline-block" /> Transfer
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-blue-600 inline-block" /> Stop
        </span>
        
        <span className="ml-auto text-muted-2 font-normal">
          {routePath.length} stops · {Array.isArray(transfers) ? transfers.length : (transfers || 0)} transfer{Array.isArray(transfers) && transfers.length !== 1 ? 's' : ''}
        </span>
      </div>

      {stats && (
        <div style={{
          position: 'absolute', top: 60, right: 16, zIndex: 400,
          background: 'rgba(255, 255, 255, 0.95)', backdropFilter: 'blur(8px)',
          padding: '12px 16px', borderRadius: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          border: '1px solid var(--st-card-border)', display: 'flex', flexDirection: 'column', gap: 6,
          minWidth: 160
        }}>
          <p style={{ margin: 0, fontSize: 11, fontWeight: 700, color: 'var(--st-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Route Stats</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontSize: 13, alignItems: 'center' }}>
            <span style={{ color: 'var(--st-muted)' }}>Stops:</span>
            <span style={{ fontWeight: 600, color: 'var(--st-ink)' }}>{stats.totalStops}</span>
            <span style={{ color: 'var(--st-muted)' }}>Distance:</span>
            <span style={{ fontWeight: 600, color: 'var(--st-ink)' }}>{stats.distanceKm} km</span>
            <span style={{ color: 'var(--st-muted)' }}>ETA:</span>
            <span style={{ fontWeight: 600, color: 'var(--st-ink)' }}>{stats.etaMin} min</span>
            {stats.routeId && (
              <>
                <span style={{ color: 'var(--st-muted)' }}>Route:</span>
                <span style={{ fontWeight: 600, color: '#2563EB' }}>{stats.routeId}</span>
              </>
            )}
            {stats.frequency && (
              <>
                <span style={{ color: 'var(--st-muted)' }}>Fleet:</span>
                <span style={{ fontWeight: 600, color: '#10b981' }}>{stats.frequency}</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Map ── */}
      <MapContainer
        center={mapCenter}
        zoom={12}
        scrollWheelZoom
        zoomControl={false}
        style={{ height: 400, width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url={tileUrl}
        />
        <ZoomControl position="bottomright" />

        {/* Auto-fit map to the route (runs once per routePath) */}
        <FitBounds positions={routePath.map(s => [s.lat, s.lon])} />

        {/* ── Route Polyline ── */}
        {polylinePositions.length > 1 && (
          <Polyline
            positions={polylinePositions}
            pathOptions={{
              color:    '#2563EB',
              weight:   5,
              opacity:  0.85,
              lineJoin: 'round',
              lineCap:  'round',
            }}
          />
        )}

        {/* ── Source Marker (stable) ── */}
        <Marker position={[first.lat, first.lon]} icon={SOURCE_ICON}>
          <Tooltip direction="top" offset={[0, -20]} opacity={1} permanent={false}>
            <span style={{ fontWeight: 600, color: '#10b981' }}>{first.stop_name} (Start)</span>
          </Tooltip>
          <Popup>
            <div className="font-sans text-sm">
              <p className="font-bold text-emerald-700 mb-0.5">🟢 Start</p>
              <p className="text-slate-700">{first.stop_name}</p>
              <p className="text-xs text-slate-400 mt-1">Route {first.route_id}</p>
            </div>
          </Popup>
        </Marker>

        {/* ── Intermediate stop markers (stable) ── */}
        {midStops.map((stop, i) => {
          const actualIndex = i + 1; // offset by 1 because first is Start
          if (actualIndex >= visibleStops) return null; // Hide if not yet reached in playback
          
          const isTransfer = stop.is_transfer || transferNames.has(stop.stop_name);
          return (
            <Marker
              key={`stop-${i}`}
              position={[stop.lat, stop.lon]}
              icon={isTransfer ? TRANSFER_ICON : getStopIcon(actualIndex + 1)}
            >
              <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                <span style={{ fontWeight: 600 }}>{stop.stop_name}</span>
                {isTransfer && <span style={{ marginLeft: 6, background: '#f97316', color: '#fff', padding: '2px 6px', borderRadius: 4, fontSize: 10 }}>Transfer</span>}
              </Tooltip>
              <Popup>
                <div className="font-sans text-sm">
                  {isTransfer ? (
                    <>
                      <p className="font-bold text-orange-600 mb-0.5">🔄 Transfer Point</p>
                      <p className="text-slate-700">{stop.stop_name}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        Switch to Route {stop.route_id}
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-semibold text-slate-800 mb-0.5">{actualIndex + 1}. {stop.stop_name}</p>
                      <p className="text-xs text-slate-400">Route {stop.route_id}</p>
                    </>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
        
        {/* ── Destination Marker (stable) ── */}
        {visibleStops >= routePath.length && (
          <Marker position={[last.lat, last.lon]} icon={DEST_ICON}>
            <Tooltip direction="top" offset={[0, -20]} opacity={1} permanent={false}>
              <span style={{ fontWeight: 600, color: '#ef4444' }}>{last.stop_name} (End)</span>
            </Tooltip>
            <Popup>
              <div className="font-sans text-sm">
                <p className="font-bold text-red-600 mb-0.5">🔴 Destination</p>
                <p className="text-slate-700">{last.stop_name}</p>
                <p className="text-xs text-slate-400 mt-1">Route {last.route_id}</p>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>

      
    </div>
  );
}
