export function ReportPanel({ report, simulation, onRefresh }) {
  if (!simulation) {
    return <p className="empty-state">El reporte estará disponible cuando exista una simulación.</p>;
  }
  return (
    <div className="report">
      <div className="report-header">
        <h3>Reporte de velocidades</h3>
        <button className="btn btn-secondary" onClick={onRefresh}>
          {simulation.status === 'finished' ? 'Actualizar' : 'Ver parcial'}
        </button>
      </div>

      {!report ? (
        <p className="empty-state">
          {simulation.status === 'finished'
            ? 'Cargando reporte…'
            : 'La simulación sigue en curso. El reporte final aparecerá al terminar; puede consultar un parcial.'}
        </p>
      ) : (
        <>
          <table className="report-table">
            <thead>
              <tr>
                <th>Camión</th>
                <th>Muestras</th>
                <th>Mín</th>
                <th>Máx</th>
                <th>Promedio (km/h)</th>
                <th>vs flota</th>
              </tr>
            </thead>
            <tbody>
              {report.trucks.map((t) => (
                <tr key={t.truck_id}>
                  <td>{t.truck_id}</td>
                  <td>{t.samples}</td>
                  <td>{t.speed_min_kmh.toFixed(1)}</td>
                  <td>{t.speed_max_kmh.toFixed(1)}</td>
                  <td>{t.speed_avg_kmh.toFixed(1)}</td>
                  <td className={t.deviation_from_fleet_pct >= 0 ? 'dev-above' : 'dev-below'}>
                    {t.deviation_from_fleet_pct >= 0 ? '+' : ''}{t.deviation_from_fleet_pct.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="fleet-avg">Promedio de la flota: {report.fleet_avg_kmh.toFixed(1)} km/h</p>
          <div className="explanation">
            <h4>Explicación</h4>
            {report.explanation.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
