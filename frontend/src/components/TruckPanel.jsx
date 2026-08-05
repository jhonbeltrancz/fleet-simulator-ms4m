import { TRUCK_COLORS } from '../constants';

const STATUS_LABEL = { en_route: 'En ruta', finished: 'Finalizado' };

export function TruckPanel({ trucks, selectedId, onSelect }) {
  if (!trucks.length) {
    return <p className="empty-state">Sin camiones. Inicie una simulación para ver la flota.</p>;
  }
  return (
    <ul className="truck-list">
      {trucks.map((truck, i) => (
        <li
          key={truck.id}
          className={`truck-card${truck.id === selectedId ? ' selected' : ''}`}
          onClick={() => onSelect(truck.id)}
        >
          <div className="truck-card-header">
            <span className="truck-badge" style={{ background: TRUCK_COLORS[i % TRUCK_COLORS.length] }}>
              {truck.id}
            </span>
            <span className={`status-chip status-${truck.status}`}>{STATUS_LABEL[truck.status] ?? truck.status}</span>
          </div>
          <div className="truck-card-body">
            <span className="truck-speed">{truck.speed_kmh.toFixed(1)} km/h</span>
            <span className="truck-route" title={`${truck.origin_name} a ${truck.destination_name}`}>
              {truck.origin_name} a {truck.destination_name}
            </span>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${truck.progress_pct}%` }} />
            </div>
            <span className="truck-progress">{truck.progress_pct.toFixed(0)}% de {(truck.distance_total_m / 1000).toFixed(2)} km</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
