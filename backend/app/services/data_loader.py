import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..schemas import Anomaly, LocationOut, RouteOut, ValidationReport


@dataclass
class Dataset:
    routes: list[RouteOut]
    loads: list[LocationOut]
    dumps: list[LocationOut]
    anomalies: list[Anomaly] = field(default_factory=list)

    @property
    def validation(self) -> ValidationReport:
        return ValidationReport(
            routes_loaded=len(self.routes),
            loads_loaded=len(self.loads),
            dumps_loaded=len(self.dumps),
            anomalies=self.anomalies,
        )


def _valid_coor(value) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(c, (int, float)) for c in value)
    )


def load_dataset(path: str | Path) -> Dataset:
    """Carga y valida el JSON de entrada sin modificarlo.

    Los registros inválidos se descartan y quedan registrados como anomalías;
    los problemas tolerables (nombres duplicados, radio null) solo se reportan.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de datos: {path}")

    with path.open(encoding="utf-8") as f:
        raw = json.load(f)

    anomalies: list[Anomaly] = []
    for key in ("Routes", "Load", "Dump"):
        if key not in raw or not isinstance(raw[key], list):
            raise ValueError(f"El JSON no contiene el arreglo raíz '{key}'")

    routes: list[RouteOut] = []
    seen_route_ids: set[int] = set()
    for r in raw["Routes"]:
        rid = r.get("id_trm_cs")
        points = r.get("points")
        if not isinstance(rid, int) or rid in seen_route_ids:
            anomalies.append(Anomaly(level="error", code="route_invalid_id",
                                     message=f"Tramo con id inválido o duplicado descartado: {rid}"))
            continue
        valid_points = [tuple(p) for p in points if _valid_coor(p)] if isinstance(points, list) else []
        if len(valid_points) < 2:
            anomalies.append(Anomaly(level="error", code="route_insufficient_points",
                                     message=f"Tramo {rid} descartado: polilínea con menos de 2 puntos válidos"))
            continue
        if len(valid_points) != len(points):
            anomalies.append(Anomaly(level="warning", code="route_malformed_points",
                                     message=f"Tramo {rid}: se ignoraron {len(points) - len(valid_points)} puntos malformados"))
        color = r.get("color") if isinstance(r.get("color"), str) else "#3388ff"
        routes.append(RouteOut(id_trm_cs=rid, nombre_tramo=str(r.get("nombre_tramo", "")),
                               color=color, points=valid_points))
        seen_route_ids.add(rid)

    dup_names = [n for n, c in Counter(r.nombre_tramo for r in routes).items() if c > 1]
    if dup_names:
        anomalies.append(Anomaly(level="warning", code="route_duplicate_names",
                                 message=f"{len(dup_names)} nombres de tramo repetidos; se usa id_trm_cs como identificador"))

    def load_locations(key: str, code_prefix: str) -> list[LocationOut]:
        result: list[LocationOut] = []
        seen_ids: set[int] = set()
        for loc in raw[key]:
            lid = loc.get("id")
            if not isinstance(lid, int) or lid in seen_ids or not _valid_coor(loc.get("coor")):
                anomalies.append(Anomaly(level="error", code=f"{code_prefix}_invalid",
                                         message=f"Ubicación de {key} descartada por id o coordenada inválida: {lid}"))
                continue
            radio = loc.get("radio")
            if radio is None:
                anomalies.append(Anomaly(level="info", code=f"{code_prefix}_no_radius",
                                         message=f"{key} {lid} ('{loc.get('name')}') sin radio definido"))
            result.append(LocationOut(id=lid, name=str(loc.get("name", "")),
                                      coor=tuple(loc["coor"]), radio=radio))
            seen_ids.add(lid)
        return result

    loads = load_locations("Load", "load")
    dumps = load_locations("Dump", "dump")

    if not routes or not loads or not dumps:
        raise ValueError("El dataset no tiene tramos, cargas o descargas válidos suficientes")

    return Dataset(routes=routes, loads=loads, dumps=dumps, anomalies=anomalies)
