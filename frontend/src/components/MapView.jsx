import { useEffect, useMemo, useState } from 'react';
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import { TRUCK_COLORS } from '../constants';

// Tamaños según zoom para que el mapa no se sature al alejar
function sizesForZoom(zoom) {
  if (zoom >= 15) return { location: 7, truck: 26, route: 3 };
  if (zoom >= 14) return { location: 5, truck: 22, route: 2.5 };
  if (zoom >= 13) return { location: 3.5, truck: 18, route: 2 };
  return { location: 2.5, truck: 14, route: 1.5 };
}

function ZoomWatcher({ onZoom }) {
  const map = useMapEvents({ zoomend: () => onZoom(map.getZoom()) });
  useEffect(() => {
    onZoom(map.getZoom());
  }, [map, onZoom]);
  return null;
}

function truckIcon(truck, color, size) {
  const number = Number(truck.id.split('-')[1]);
  return L.divIcon({
    className: 'truck-icon',
    html: `<div class="truck-dot" style="background:${color};width:${size}px;height:${size}px;font-size:${Math.round(size * 0.45)}px">${number}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function flagIcon(kind) {
  const stroke = kind === 'start' ? '#1b7f37' : '#a03410';
  const fill = kind === 'start' ? '#2eb350' : '#e05a2b';
  return L.divIcon({
    className: 'flag-icon',
    html: `<svg width="24" height="24" viewBox="0 0 24 24">
      <line x1="4" y1="23" x2="4" y2="2" stroke="${stroke}" stroke-width="2.5"/>
      <path d="M4 3h15l-4.5 4.5L19 12H4z" fill="${fill}" stroke="${stroke}" stroke-width="1"/>
    </svg>`,
    iconSize: [24, 24],
    iconAnchor: [4, 23],
  });
}

export function MapView({ routes, loads, dumps, trucks, selected, onSelectTruck }) {
  const [zoom, setZoom] = useState(14);
  const sizes = sizesForZoom(zoom);
  // Con un camión seleccionado, el resto de capas se atenúa para destacar su recorrido
  const dim = selected != null;

  const bounds = useMemo(() => {
    const points = routes.flatMap((r) => r.points);
    return points.length ? L.latLngBounds(points) : L.latLngBounds([[-15.15, -75.72], [-15.13, -75.7]]);
  }, [routes]);

  const selectedIndex = trucks.findIndex((t) => t.id === selected?.truckId);
  const selectedColor = selectedIndex >= 0 ? TRUCK_COLORS[selectedIndex % TRUCK_COLORS.length] : '#1f6feb';

  return (
    <MapContainer bounds={bounds} className="map" scrollWheelZoom>
      <ZoomWatcher onZoom={setZoom} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {routes.map((route) => (
        <Polyline
          key={route.id_trm_cs}
          positions={route.points}
          pathOptions={{ color: route.color, weight: sizes.route, opacity: dim ? 0.2 : 0.85 }}
        >
          <Tooltip sticky>{route.nombre_tramo} (id {route.id_trm_cs})</Tooltip>
        </Polyline>
      ))}

      {loads.map((loc) => (
        <CircleMarker
          key={`load-${loc.id}`}
          center={loc.coor}
          radius={sizes.location}
          pathOptions={{ color: '#1b7f37', fillColor: '#2eb350', fillOpacity: dim ? 0.3 : 0.9, opacity: dim ? 0.3 : 1, weight: 1.5 }}
        >
          <Tooltip>Carga: {loc.name}{loc.radio != null ? ` (radio ${loc.radio} m)` : ''}</Tooltip>
        </CircleMarker>
      ))}

      {dumps.map((loc) => (
        <CircleMarker
          key={`dump-${loc.id}`}
          center={loc.coor}
          radius={sizes.location}
          pathOptions={{ color: '#a03410', fillColor: '#e05a2b', fillOpacity: dim ? 0.3 : 0.9, opacity: dim ? 0.3 : 1, weight: 1.5 }}
        >
          <Tooltip>Descarga: {loc.name}{loc.radio != null ? ` (radio ${loc.radio} m)` : ''}</Tooltip>
        </CircleMarker>
      ))}

      {selected && (
        <>
          <Polyline positions={selected.path} pathOptions={{ color: selectedColor, weight: 5, opacity: 0.95 }} />
          <Marker position={selected.path[0]} icon={flagIcon('start')}>
            <Tooltip direction="top" offset={[0, -20]}>Inicio: {selected.origin.name}</Tooltip>
          </Marker>
          <Marker position={selected.path[selected.path.length - 1]} icon={flagIcon('end')}>
            <Tooltip direction="top" offset={[0, -20]}>Fin: {selected.destination.name}</Tooltip>
          </Marker>
        </>
      )}

      {trucks.map((truck, i) => (
        <Marker
          key={truck.id}
          position={truck.position}
          icon={truckIcon(truck, TRUCK_COLORS[i % TRUCK_COLORS.length], sizes.truck)}
          opacity={dim && truck.id !== selected?.truckId ? 0.4 : 1}
          eventHandlers={{ click: () => onSelectTruck(truck.id) }}
        >
          <Tooltip direction="top" offset={[0, -12]}>
            <strong>{truck.id}</strong>
            <br />
            {truck.speed_kmh} km/h · {truck.status === 'en_route' ? 'En ruta' : 'Finalizado'}
            <br />
            {truck.origin_name} a {truck.destination_name}
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
