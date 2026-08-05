import json

import pytest

from app.config import Settings
from app.services.data_loader import load_dataset
from app.services.graph import RoadNetwork

# Red mínima con dos componentes: A-B-C conectados y D-E aislados.
# Coordenadas separadas ~100 m para que las distancias sean predecibles.
FIXTURE = {
    "Routes": [
        {"id_trm_cs": 1, "nombre_tramo": "T1", "color": "#ff0000",
         "points": [[-15.0, -75.0], [-15.001, -75.0], [-15.002, -75.0]]},
        {"id_trm_cs": 2, "nombre_tramo": "T2", "color": "#00ff00",
         "points": [[-15.002, -75.0], [-15.002, -75.001]]},
        {"id_trm_cs": 3, "nombre_tramo": "Aislado", "color": "#0000ff",
         "points": [[-15.5, -75.5], [-15.501, -75.5]]},
    ],
    "Load": [
        {"id": 10, "name": "Carga A", "coor": [-15.0, -75.0], "radio": 20},
        {"id": 11, "name": "Carga aislada", "coor": [-15.5, -75.5], "radio": None},
    ],
    "Dump": [
        {"id": 20, "name": "Descarga C", "coor": [-15.002, -75.001], "radio": 15},
    ],
}


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(FIXTURE), encoding="utf-8")
    return path


@pytest.fixture
def dataset(data_file):
    return load_dataset(data_file)


@pytest.fixture
def network(dataset):
    return RoadNetwork(dataset)


@pytest.fixture
def settings(data_file):
    return Settings(data_file_path=str(data_file), tick_seconds=0.01)


@pytest.fixture
def snap(dataset, network):
    result = {}
    for kind, locs in (("load", dataset.loads), ("dump", dataset.dumps)):
        for loc in locs:
            result[(kind, loc.id)], _ = network.nearest_node(loc.coor)
    return result
