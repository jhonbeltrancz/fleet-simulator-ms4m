import json

import pytest

from app.services.data_loader import load_dataset


def test_loads_valid_dataset(dataset):
    assert len(dataset.routes) == 3
    assert len(dataset.loads) == 2
    assert len(dataset.dumps) == 1


def test_reports_null_radius_as_info(dataset):
    codes = [a.code for a in dataset.anomalies]
    assert "load_no_radius" in codes


def test_discards_route_with_insufficient_points(tmp_path):
    raw = {
        "Routes": [
            {"id_trm_cs": 1, "nombre_tramo": "ok", "color": "#fff",
             "points": [[-15.0, -75.0], [-15.001, -75.0]]},
            {"id_trm_cs": 2, "nombre_tramo": "malo", "color": "#fff", "points": [[-15.0, -75.0]]},
        ],
        "Load": [{"id": 1, "name": "L", "coor": [-15.0, -75.0], "radio": 5}],
        "Dump": [{"id": 1, "name": "D", "coor": [-15.001, -75.0], "radio": 5}],
    }
    path = tmp_path / "d.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    ds = load_dataset(path)
    assert len(ds.routes) == 1
    assert any(a.code == "route_insufficient_points" for a in ds.anomalies)


def test_missing_root_key_raises(tmp_path):
    path = tmp_path / "d.json"
    path.write_text(json.dumps({"Routes": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="Load"):
        load_dataset(path)


def test_input_file_is_not_modified(data_file):
    before = data_file.read_bytes()
    load_dataset(data_file)
    assert data_file.read_bytes() == before
