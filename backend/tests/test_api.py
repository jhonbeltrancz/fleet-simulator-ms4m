import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def client(data_file, monkeypatch):
    monkeypatch.setenv("SIM_DATA_FILE_PATH", str(data_file))
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def test_get_routes(client):
    res = client.get("/api/routes")
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_get_locations(client):
    assert len(client.get("/api/locations/loads").json()) == 2
    assert len(client.get("/api/locations/dumps").json()) == 1


def test_validation_report(client):
    res = client.get("/api/network/validation")
    assert res.status_code == 200
    assert res.json()["routes_loaded"] == 3


def test_simulation_requires_creation(client):
    assert client.get("/api/simulation").status_code == 404
    assert client.get("/api/simulation/report").status_code == 404


def test_simulation_lifecycle(client):
    res = client.post("/api/simulation", json={"seed": 42})
    assert res.status_code == 201
    body = res.json()
    assert len(body["trucks"]) == 5
    assert body["status"] == "running"

    res = client.get("/api/simulation")
    assert res.status_code == 200
    assert res.json()["id"] == body["id"]

    res = client.get("/api/simulation/report")
    assert res.status_code == 200
    assert len(res.json()["trucks"]) == 5


def test_speed_factor_is_applied(client):
    sim = client.post("/api/simulation", json={"seed": 42}).json()
    assert sim["time_scale"] == 1.0
    res = client.post("/api/simulation/speed", json={"factor": 4})
    assert res.status_code == 200
    assert res.json()["time_scale"] == 4.0


def test_speed_rejects_invalid_factor(client):
    client.post("/api/simulation", json={"seed": 42})
    assert client.post("/api/simulation/speed", json={"factor": 0}).status_code == 422
    assert client.post("/api/simulation/speed", json={"factor": 32}).status_code == 422


def test_speed_requires_simulation(client):
    assert client.post("/api/simulation/speed", json={"factor": 2}).status_code == 404


def test_pause_and_resume(client):
    sim = client.post("/api/simulation", json={"seed": 42}).json()
    assert sim["paused"] is False
    res = client.post("/api/simulation/pause")
    assert res.status_code == 200
    assert res.json()["paused"] is True
    res = client.post("/api/simulation/resume")
    assert res.json()["paused"] is False


def test_pause_requires_simulation(client):
    assert client.post("/api/simulation/pause").status_code == 404


def test_truck_path_endpoint(client):
    client.post("/api/simulation", json={"seed": 42})
    res = client.get("/api/simulation/trucks/CAM-001/path")
    assert res.status_code == 200
    body = res.json()
    assert len(body["path"]) >= 2
    assert body["origin"]["name"]
    assert client.get("/api/simulation/trucks/CAM-999/path").status_code == 404


def test_restart_replaces_simulation(client):
    first = client.post("/api/simulation", json={"seed": 1}).json()["id"]
    second = client.post("/api/simulation", json={"seed": 1}).json()["id"]
    assert first != second
