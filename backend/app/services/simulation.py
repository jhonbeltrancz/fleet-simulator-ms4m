import asyncio
import itertools
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..config import Settings
from ..schemas import (
    AssignmentDecision,
    Coordinate,
    LocationOut,
    SimulationState,
    TruckState,
)
from .data_loader import Dataset
from .graph import RoadNetwork

TRUCK_COUNT = 5
MAX_ASSIGNMENT_ATTEMPTS = 20


class AssignmentError(RuntimeError):
    """No fue posible asignar un par carga/descarga alcanzable."""


@dataclass
class SpeedSample:
    timestamp: datetime
    speed_kmh: float


@dataclass
class Truck:
    id: str
    origin: LocationOut
    destination: LocationOut
    path: list[Coordinate]
    cumulative_m: list[float]
    total_m: float
    distance_m: float = 0.0
    speed_kmh: float = 0.0
    status: str = "en_route"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    samples: list[SpeedSample] = field(default_factory=list)

    def position(self) -> Coordinate:
        """Interpola la posición sobre el recorrido según la distancia acumulada."""
        if self.distance_m <= 0:
            return self.path[0]
        if self.distance_m >= self.total_m:
            return self.path[-1]
        # Búsqueda del segmento que contiene la distancia actual
        lo, hi = 0, len(self.cumulative_m) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.cumulative_m[mid] < self.distance_m:
                lo = mid + 1
            else:
                hi = mid
        i = lo
        seg_start, seg_end = self.cumulative_m[i - 1], self.cumulative_m[i]
        t = (self.distance_m - seg_start) / (seg_end - seg_start) if seg_end > seg_start else 0.0
        a, b = self.path[i - 1], self.path[i]
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def to_state(self) -> TruckState:
        return TruckState(
            id=self.id,
            status=self.status,
            position=self.position(),
            speed_kmh=round(self.speed_kmh, 2),
            progress_pct=round(min(self.distance_m / self.total_m, 1.0) * 100, 2) if self.total_m else 100.0,
            distance_total_m=round(self.total_m, 1),
            distance_covered_m=round(min(self.distance_m, self.total_m), 1),
            origin_name=self.origin.name,
            destination_name=self.destination.name,
            updated_at=self.updated_at,
        )


class Simulation:
    """Simulación en memoria de la flota. El avance se calcula con step(dt),
    lo que permite ejecutarla en tiempo real o de forma determinista en tests."""

    def __init__(self, dataset: Dataset, network: RoadNetwork, settings: Settings,
                 snap: dict[tuple[str, int], Coordinate], seed: int | None = None):
        self.id = uuid.uuid4().hex[:12]
        self.seed = seed
        self.rng = random.Random(seed)
        self.settings = settings
        self.started_at = datetime.now(timezone.utc)
        self.status = "running"
        self.time_scale = 1.0
        self.paused = False
        self._carry = 0.0
        self.trucks: list[Truck] = []
        self.assignments: list[AssignmentDecision] = []
        self._assign_trucks(dataset, network, snap)

    def _assign_trucks(self, dataset: Dataset, network: RoadNetwork,
                       snap: dict[tuple[str, int], Coordinate]) -> None:
        for n in range(1, TRUCK_COUNT + 1):
            truck_id = f"CAM-{n:03d}"
            rejected: list[dict] = []
            for _ in range(MAX_ASSIGNMENT_ATTEMPTS):
                load = self.rng.choice(dataset.loads)
                dump = self.rng.choice(dataset.dumps)
                origin_node = snap[("load", load.id)]
                dest_node = snap[("dump", dump.id)]
                result = network.shortest_path(origin_node, dest_node)
                if result is None:
                    rejected.append({
                        "load_id": load.id, "load_name": load.name,
                        "dump_id": dump.id, "dump_name": dump.name,
                        "reason": "sin recorrido: origen y destino en componentes desconectados",
                    })
                    continue
                path, total = result
                cumulative = list(itertools.accumulate(
                    [0.0] + [network.adjacency[path[i]][path[i + 1]] for i in range(len(path) - 1)]
                ))
                self.trucks.append(Truck(
                    id=truck_id, origin=load, destination=dump,
                    path=path, cumulative_m=cumulative, total_m=total,
                ))
                self.assignments.append(AssignmentDecision(
                    truck_id=truck_id, load_id=load.id, load_name=load.name,
                    dump_id=dump.id, dump_name=dump.name,
                    distance_m=round(total, 1), rejected_pairs=rejected,
                ))
                break
            else:
                raise AssignmentError(f"No se encontró par carga/descarga alcanzable para {truck_id}")

    def step(self, dt_seconds: float) -> None:
        if self.status != "running":
            return
        now = datetime.now(timezone.utc)
        for truck in self.trucks:
            if truck.status != "en_route":
                continue
            truck.speed_kmh = self.rng.uniform(self.settings.speed_min_kmh, self.settings.speed_max_kmh)
            truck.distance_m += truck.speed_kmh / 3.6 * dt_seconds
            truck.updated_at = now
            truck.samples.append(SpeedSample(timestamp=now, speed_kmh=truck.speed_kmh))
            if truck.distance_m >= truck.total_m:
                truck.distance_m = truck.total_m
                truck.speed_kmh = 0.0
                truck.status = "finished"
        if all(t.status == "finished" for t in self.trucks):
            self.status = "finished"

    def advance(self, seconds: float) -> None:
        """Avanza en pasos exactos del tick, acumulando el residuo para el siguiente avance.

        Así cada muestra representa siempre el mismo intervalo simulado y el promedio
        del reporte sigue siendo una media aritmética válida aunque cambie time_scale.
        """
        self._carry += seconds
        tick = self.settings.tick_seconds
        while self._carry >= tick and self.status == "running":
            self.step(tick)
            self._carry -= tick

    def to_state(self) -> SimulationState:
        return SimulationState(
            id=self.id,
            status=self.status,
            seed=self.seed,
            time_scale=self.time_scale,
            paused=self.paused,
            started_at=self.started_at,
            trucks=[t.to_state() for t in self.trucks],
            assignments=self.assignments,
        )


class SimulationManager:
    """Mantiene la simulación vigente y su loop asyncio; POST reinicia reemplazándola."""

    def __init__(self, dataset: Dataset, network: RoadNetwork, settings: Settings):
        self.dataset = dataset
        self.network = network
        self.settings = settings
        self.current: Simulation | None = None
        self._task: asyncio.Task | None = None
        # Nodo de red más cercano por ubicación, precalculado una sola vez:
        # el camión parte y llega siempre sobre la red, nunca fuera de ella
        self.snap: dict[tuple[str, int], Coordinate] = {}
        for kind, locs in (("load", dataset.loads), ("dump", dataset.dumps)):
            for loc in locs:
                self.snap[(kind, loc.id)], _ = network.nearest_node(loc.coor)

    def start(self, seed: int | None = None) -> Simulation:
        self.stop()
        self.current = Simulation(self.dataset, self.network, self.settings, self.snap, seed)
        self._task = asyncio.create_task(self._run_loop(self.current))
        return self.current

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _run_loop(self, sim: Simulation) -> None:
        loop = asyncio.get_running_loop()
        last = loop.time()
        while sim.status == "running":
            await asyncio.sleep(self.settings.tick_seconds)
            now = loop.time()
            # dt real escalado por el factor de velocidad vigente; en pausa el
            # reloj de referencia se actualiza igual para no saltar al reanudar
            if not sim.paused:
                sim.advance((now - last) * sim.time_scale)
            last = now
