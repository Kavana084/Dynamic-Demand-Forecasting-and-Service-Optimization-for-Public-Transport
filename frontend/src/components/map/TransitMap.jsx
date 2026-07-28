import { MapContainer, TileLayer, Polyline, Marker, Popup, ZoomControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useMemo } from 'react';
import L from 'leaflet';

// Fix for default leaflet icons not showing in Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom Bus Icon
const busIcon = new L.Icon({
  iconUrl: 'https://img.icons8.com/color/48/000000/bus.png',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const mockRoutes = [
  {
    id: 'R-12',
    name: 'Central District Loop',
    load: 'high', // red
    positions: [
      [12.9716, 77.5946],
      [12.9800, 77.6000],
      [12.9900, 77.6100],
      [13.0000, 77.6200],
    ]
  },
  {
    id: 'R-45',
    name: 'Riverside Express',
    load: 'medium', // orange
    positions: [
      [12.9600, 77.5800],
      [12.9500, 77.5700],
      [12.9400, 77.5600],
      [12.9300, 77.5500],
    ]
  },
  {
    id: 'R-08',
    name: 'South Point',
    load: 'low', // green
    positions: [
      [12.9500, 77.6100],
      [12.9400, 77.6200],
      [12.9300, 77.6300],
      [12.9200, 77.6400],
    ]
  }
];

const mockBuses = [
  { id: 'B1', route: 'R-12', position: [12.9800, 77.6000] },
  { id: 'B2', route: 'R-12', position: [12.9900, 77.6100] },
  { id: 'B3', route: 'R-45', position: [12.9500, 77.5700] },
  { id: 'B4', route: 'R-08', position: [12.9400, 77.6200] },
];

export default function TransitMap() {
  const getRouteColor = (load) => {
    switch(load) {
      case 'high': return '#ef4444'; // red-500
      case 'medium': return '#f59e0b'; // amber-500
      case 'low': return '#10b981'; // emerald-500
      default: return '#94a3b8'; // slate-400
    }
  };

  return (
    <div className="h-full w-full relative rounded-2xl overflow-hidden border border-slate-200">
      <MapContainer 
        center={[12.9716, 77.5946]} 
        zoom={12} 
        scrollWheelZoom={true}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        />
        <ZoomControl position="bottomright" />
        
        {/* Render Routes */}
        {mockRoutes.map((route) => (
          <Polyline 
            key={route.id}
            positions={route.positions}
            pathOptions={{ color: getRouteColor(route.load), weight: 5, opacity: 0.8 }}
          />
        ))}

        {/* Render Buses */}
        {mockBuses.map((bus) => (
          <Marker key={bus.id} position={bus.position} icon={busIcon}>
            <Popup>
              <div className="font-sans">
                <p className="font-bold text-slate-800">Bus {bus.id}</p>
                <p className="text-sm text-slate-600">Route: {bus.route}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
