import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';

export function useSimulation() {
  const [simulation, setSimulation] = useState(null);
  const [report, setReport] = useState(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);
  const sourceRef = useRef(null);

  const start = useCallback(async (seed) => {
    setStarting(true);
    setError(null);
    setReport(null);
    sourceRef.current?.close();
    try {
      const sim = await api.createSimulation(seed);
      setSimulation(sim);

      const source = new EventSource(api.streamUrl);
      source.onmessage = (e) => setSimulation(JSON.parse(e.data));
      source.addEventListener('end', async () => {
        source.close();
        try {
          setReport(await api.getReport());
        } catch (err) {
          setError(err.message);
        }
      });
      source.onerror = () => {
        source.close();
        setError('Se perdió la conexión con la transmisión de la simulación');
      };
      sourceRef.current = source;
    } catch (err) {
      setError(err.message);
    } finally {
      setStarting(false);
    }
  }, []);

  const setSpeed = useCallback(async (factor) => {
    setError(null);
    try {
      setSimulation(await api.setSimulationSpeed(factor));
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const togglePause = useCallback(async (paused) => {
    setError(null);
    try {
      setSimulation(paused ? await api.resumeSimulation() : await api.pauseSimulation());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const refreshReport = useCallback(async () => {
    setError(null);
    try {
      setReport(await api.getReport());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => () => sourceRef.current?.close(), []);

  return { simulation, report, starting, error, start, setSpeed, togglePause, refreshReport };
}
