import pytest

from app.services.graph import haversine_m


def test_components_detected(network):
    assert network.component_count == 2


def test_shortest_path_follows_network(network):
    start = (-15.0, -75.0)
    end = (-15.002, -75.001)
    path, dist = network.shortest_path(start, end)
    assert path[0] == start
    assert path[-1] == end
    # Debe pasar por los nodos intermedios de la red, no ir en línea recta
    assert (-15.001, -75.0) in path
    assert dist > haversine_m(start, end)


def test_no_path_between_components(network):
    result = network.shortest_path((-15.0, -75.0), (-15.5, -75.5))
    assert result is None


def test_nearest_node(network):
    node, dist = network.nearest_node((-15.0001, -75.0))
    assert node == (-15.0, -75.0)
    assert dist < 20


def test_haversine_known_distance():
    # 0.001° de latitud ≈ 111.2 m
    d = haversine_m((-15.0, -75.0), (-15.001, -75.0))
    assert d == pytest.approx(111.2, abs=1)
