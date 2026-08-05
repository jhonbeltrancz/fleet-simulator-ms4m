import pytest

from app.services.report import build_report
from app.services.simulation import Simulation


def test_creates_five_trucks_with_stable_ids(dataset, network, settings, snap):
    sim = Simulation(dataset, network, settings, snap, seed=42)
    assert [t.id for t in sim.trucks] == [f"CAM-{i:03d}" for i in range(1, 6)]


def test_rejected_pairs_are_visible(dataset, network, settings, snap):
    # Con la carga aislada en el dataset, algún intento debe quedar registrado como rechazado
    found_rejection = False
    for seed in range(30):
        sim = Simulation(dataset, network, settings, snap, seed=seed)
        if any(a.rejected_pairs for a in sim.assignments):
            found_rejection = True
            rejected = next(a for a in sim.assignments if a.rejected_pairs).rejected_pairs[0]
            assert "componentes desconectados" in rejected["reason"]
            break
    assert found_rejection


def test_same_seed_reproduces_run(dataset, network, settings, snap):
    sim1 = Simulation(dataset, network, settings, snap, seed=7)
    sim2 = Simulation(dataset, network, settings, snap, seed=7)
    for _ in range(10):
        sim1.step(1.0)
        sim2.step(1.0)
    for t1, t2 in zip(sim1.trucks, sim2.trucks):
        assert t1.origin.id == t2.origin.id
        assert t1.destination.id == t2.destination.id
        assert t1.distance_m == t2.distance_m
        assert [s.speed_kmh for s in t1.samples] == [s.speed_kmh for s in t2.samples]


def test_trucks_advance_and_finish_on_route(dataset, network, settings, snap):
    sim = Simulation(dataset, network, settings, snap, seed=1)
    for _ in range(1000):
        sim.step(1.0)
        for t in sim.trucks:
            assert 0 <= t.distance_m <= t.total_m
        if sim.status == "finished":
            break
    assert sim.status == "finished"
    for t in sim.trucks:
        assert t.position() == t.path[-1]
        assert t.speed_kmh == 0.0


def test_speeds_within_configured_range(dataset, network, settings, snap):
    sim = Simulation(dataset, network, settings, snap, seed=3)
    sim.step(1.0)
    for t in sim.trucks:
        for s in t.samples:
            assert settings.speed_min_kmh <= s.speed_kmh <= settings.speed_max_kmh


def test_advance_keeps_uniform_sampling(dataset, network, settings, snap):
    sim = Simulation(dataset, network, settings, snap, seed=9)
    # 5.5 s con tick de 0.01 s: ~550 pasos uniformes (±1 por residuo de punto flotante)
    sim.advance(5.5)
    active = [t for t in sim.trucks if t.samples]
    assert active
    counts = {len(t.samples) for t in active}
    assert len(counts) == 1
    assert counts.pop() in (550, 551)


def test_advance_accumulates_residue(dataset, network, settings, snap):
    sim = Simulation(dataset, network, settings, snap, seed=2)
    # Medio tick no genera muestra; el residuo se acumula hasta completar el tick
    sim.advance(0.005)
    assert all(len(t.samples) == 0 for t in sim.trucks)
    sim.advance(0.005)
    assert all(len(t.samples) == 1 for t in sim.trucks)


def test_report_statistics(dataset, network, settings, snap):
    sim = Simulation(dataset, network, settings, snap, seed=5)
    for _ in range(20):
        sim.step(1.0)
    report = build_report(sim, settings)
    assert len(report.trucks) == 5
    for tr in report.trucks:
        truck = next(t for t in sim.trucks if t.id == tr.truck_id)
        speeds = [s.speed_kmh for s in truck.samples]
        assert tr.samples == len(speeds)
        assert tr.speed_avg_kmh == round(sum(speeds) / len(speeds), 2)
        assert tr.speed_min_kmh == round(min(speeds), 2)
        assert tr.speed_max_kmh == round(max(speeds), 2)
        expected_dev = (sum(speeds) / len(speeds) - report.fleet_avg_kmh) / report.fleet_avg_kmh * 100
        assert tr.deviation_from_fleet_pct == pytest.approx(expected_dev, abs=0.11)
    assert report.explanation
    assert any("más rápido" in line for line in report.explanation)
