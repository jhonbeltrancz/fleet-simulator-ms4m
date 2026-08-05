const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error('No se pudo conectar con el backend');
  }
  if (!res.ok) {
    let detail;
    try {
      detail = (await res.json()).detail;
    } catch {
      detail = null;
    }
    throw new Error(detail ?? `Error ${res.status} del servidor`);
  }
  return res.json();
}

export const api = {
  getRoutes: () => request('/api/routes'),
  getLoads: () => request('/api/locations/loads'),
  getDumps: () => request('/api/locations/dumps'),
  getReport: () => request('/api/simulation/report'),
  getTruckPath: (truckId) => request(`/api/simulation/trucks/${truckId}/path`),
  pauseSimulation: () => request('/api/simulation/pause', { method: 'POST' }),
  resumeSimulation: () => request('/api/simulation/resume', { method: 'POST' }),
  setSimulationSpeed: (factor) =>
    request('/api/simulation/speed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ factor }),
    }),
  createSimulation: (seed) =>
    request('/api/simulation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(seed == null ? {} : { seed }),
    }),
  streamUrl: `${API_URL}/api/simulation/stream`,
};
