import { useEffect, useState } from 'react';
import { api } from './api';
import { Legend } from './components/Legend';
import { MapView } from './components/MapView';
import { ReportPanel } from './components/ReportPanel';
import { TruckPanel } from './components/TruckPanel';
import { useSimulation } from './hooks/useSimulation';

export default function App() {
  const [network, setNetwork] = useState({ routes: [], loads: [], dumps: [] });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [seedInput, setSeedInput] = useState('');
  const [selected, setSelected] = useState(null);
  const [selectionError, setSelectionError] = useState(null);
  const { simulation, report, starting, error, start, setSpeed, togglePause, refreshReport } = useSimulation();
  const speedFactor = simulation?.time_scale ?? 1;
  const running = simulation?.status === 'running';

  // Ciclo x1 -> x2 -> x4 -> x8 -> x1
  const handleSpeedToggle = () => setSpeed(speedFactor >= 8 ? 1 : speedFactor * 2);

  async function loadNetwork() {
    setLoading(true);
    setLoadError(null);
    try {
      const [routes, loads, dumps] = await Promise.all([api.getRoutes(), api.getLoads(), api.getDumps()]);
      setNetwork({ routes, loads, dumps });
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNetwork();
  }, []);

  const handleStart = () => {
    const seed = seedInput.trim() === '' ? null : Number(seedInput);
    setSelected(null);
    setSelectionError(null);
    start(Number.isNaN(seed) ? null : seed);
  };

  // Clic sobre un camión: alterna la selección y trae su recorrido una sola vez
  const handleSelectTruck = async (truckId) => {
    setSelectionError(null);
    if (!truckId || selected?.truckId === truckId) {
      setSelected(null);
      return;
    }
    try {
      const data = await api.getTruckPath(truckId);
      setSelected({ truckId, ...data });
    } catch (err) {
      setSelectionError(err.message);
    }
  };

  if (loading) {
    return <div className="screen-state">Cargando red vial…</div>;
  }

  if (loadError) {
    return (
      <div className="screen-state">
        <p>No se pudo cargar la red vial: {loadError}</p>
        <button className="btn btn-primary" onClick={loadNetwork}>Reintentar</button>
      </div>
    );
  }

  if (!network.routes.length) {
    return <div className="screen-state">El backend no devolvió tramos para mostrar.</div>;
  }

  const banner = error ?? selectionError;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Simulador de flota</h1>
          <span className="subtitle">
            {network.routes.length} tramos · {network.loads.length} cargas · {network.dumps.length} descargas
          </span>
        </div>
        <div className="controls">
          <div className="new-sim-group" title="La semilla hace la corrida reproducible: mismas asignaciones y velocidades. Vacía, cada simulación es distinta. Se aplica al pulsar Nueva simulación.">
            <input
              className="seed-input"
              type="number"
              placeholder="Semilla (opcional)"
              value={seedInput}
              onChange={(e) => setSeedInput(e.target.value)}
            />
            <button className="btn btn-primary" onClick={handleStart} disabled={starting}>
              {starting ? 'Iniciando…' : simulation ? 'Nueva simulación' : 'Iniciar simulación'}
            </button>
          </div>
          <button
            className="btn btn-secondary"
            onClick={() => togglePause(simulation.paused)}
            disabled={!running || starting}
          >
            {simulation?.paused ? 'Continuar' : 'Pausar'}
          </button>
          <button
            className={`btn btn-secondary${speedFactor > 1 ? ' btn-speed-active' : ''}`}
            onClick={handleSpeedToggle}
            disabled={!running || starting}
            title="Acelera la simulación sin alterar el muestreo del reporte"
          >
            Velocidad ×{speedFactor}
          </button>
        </div>
      </header>

      {banner && <div className="error-banner">{banner}</div>}

      <div className="layout">
        <main className="map-area">
          <MapView
            routes={network.routes}
            loads={network.loads}
            dumps={network.dumps}
            trucks={simulation?.trucks ?? []}
            selected={selected}
            onSelectTruck={handleSelectTruck}
          />
          <Legend />
        </main>
        <aside className="sidebar">
          <section>
            <h2>Flota</h2>
            <TruckPanel
              trucks={simulation?.trucks ?? []}
              selectedId={selected?.truckId ?? null}
              onSelect={handleSelectTruck}
            />
          </section>
          <section>
            <ReportPanel report={report} simulation={simulation} onRefresh={refreshReport} />
          </section>
        </aside>
      </div>
    </div>
  );
}
