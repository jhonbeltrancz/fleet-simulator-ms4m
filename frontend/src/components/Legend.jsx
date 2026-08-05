export function Legend() {
  return (
    <div className="legend">
      <span className="legend-item">
        <span className="legend-swatch" style={{ background: '#2eb350' }} /> Carga
      </span>
      <span className="legend-item">
        <span className="legend-swatch" style={{ background: '#e05a2b' }} /> Descarga
      </span>
      <span className="legend-item">
        <span className="legend-swatch legend-line" /> Tramos (color según dato)
      </span>
      <span className="legend-item">
        <span className="legend-swatch legend-truck">n</span> Camión
      </span>
    </div>
  );
}
