from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Coordinate = tuple[float, float]


class RouteOut(BaseModel):
    id_trm_cs: int
    nombre_tramo: str
    color: str
    points: list[Coordinate]


class LocationOut(BaseModel):
    id: int
    name: str
    coor: Coordinate
    radio: int | None = None


class Anomaly(BaseModel):
    level: Literal["error", "warning", "info"]
    code: str
    message: str


class ValidationReport(BaseModel):
    routes_loaded: int
    loads_loaded: int
    dumps_loaded: int
    anomalies: list[Anomaly]


class NetworkInfo(BaseModel):
    nodes: int
    edges: int
    connected_components: int
    main_component_size: int


class SimulationCreate(BaseModel):
    seed: int | None = None


class AssignmentDecision(BaseModel):
    truck_id: str
    load_id: int
    load_name: str
    dump_id: int
    dump_name: str
    distance_m: float
    rejected_pairs: list[dict]


class TruckState(BaseModel):
    id: str
    status: Literal["en_route", "finished"]
    position: Coordinate
    speed_kmh: float
    progress_pct: float
    distance_total_m: float
    distance_covered_m: float
    origin_name: str
    destination_name: str
    updated_at: datetime


class SimulationState(BaseModel):
    id: str
    status: Literal["running", "finished"]
    seed: int | None
    time_scale: float
    paused: bool
    started_at: datetime
    trucks: list[TruckState]
    assignments: list[AssignmentDecision]


class SpeedRequest(BaseModel):
    factor: float = Field(ge=1, le=8)


class TruckPath(BaseModel):
    truck_id: str
    origin: LocationOut
    destination: LocationOut
    path: list[Coordinate]


class TruckReport(BaseModel):
    truck_id: str
    samples: int
    speed_min_kmh: float
    speed_max_kmh: float
    speed_avg_kmh: float
    # Desvío del promedio del camión respecto al promedio de la flota
    deviation_from_fleet_pct: float


class SimulationReport(BaseModel):
    simulation_id: str
    generated_at: datetime
    fleet_avg_kmh: float
    trucks: list[TruckReport]
    explanation: list[str]


class ApiError(BaseModel):
    detail: str
