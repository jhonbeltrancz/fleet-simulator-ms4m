import heapq
import math
from collections import defaultdict

from ..schemas import Coordinate
from .data_loader import Dataset

EARTH_RADIUS_M = 6_371_000


def haversine_m(a: Coordinate, b: Coordinate) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


class RoadNetwork:
    """Grafo no dirigido: nodos = coordenadas de las polilíneas, costo = distancia haversine.

    Las polilíneas comparten coordenadas idénticas en sus uniones, por lo que
    la coordenada exacta funciona como clave de nodo sin necesidad de snapping.
    """

    def __init__(self, dataset: Dataset):
        self.adjacency: dict[Coordinate, dict[Coordinate, float]] = defaultdict(dict)
        for route in dataset.routes:
            pts = route.points
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                if a == b:
                    continue
                cost = haversine_m(a, b)
                self.adjacency[a][b] = cost
                self.adjacency[b][a] = cost

        self.component: dict[Coordinate, int] = {}
        self._label_components()
        self.edge_count = sum(len(n) for n in self.adjacency.values()) // 2

    def _label_components(self) -> None:
        cid = 0
        for node in self.adjacency:
            if node in self.component:
                continue
            stack = [node]
            self.component[node] = cid
            while stack:
                current = stack.pop()
                for neighbor in self.adjacency[current]:
                    if neighbor not in self.component:
                        self.component[neighbor] = cid
                        stack.append(neighbor)
            cid += 1
        self.component_count = cid

    @property
    def main_component_size(self) -> int:
        sizes: dict[int, int] = defaultdict(int)
        for cid in self.component.values():
            sizes[cid] += 1
        return max(sizes.values()) if sizes else 0

    def nearest_node(self, coor: Coordinate) -> tuple[Coordinate, float]:
        best, best_dist = None, math.inf
        for node in self.adjacency:
            d = haversine_m(coor, node)
            if d < best_dist:
                best, best_dist = node, d
        return best, best_dist

    def same_component(self, a: Coordinate, b: Coordinate) -> bool:
        return self.component.get(a) is not None and self.component.get(a) == self.component.get(b)

    def shortest_path(self, start: Coordinate, end: Coordinate) -> tuple[list[Coordinate], float] | None:
        """Dijkstra con heap; retorna (camino, distancia en metros) o None si no hay conexión."""
        if start not in self.adjacency or end not in self.adjacency:
            return None
        if not self.same_component(start, end):
            return None

        dist: dict[Coordinate, float] = {start: 0.0}
        prev: dict[Coordinate, Coordinate] = {}
        heap: list[tuple[float, Coordinate]] = [(0.0, start)]
        visited: set[Coordinate] = set()

        while heap:
            d, node = heapq.heappop(heap)
            if node in visited:
                continue
            if node == end:
                break
            visited.add(node)
            for neighbor, cost in self.adjacency[node].items():
                nd = d + cost
                if nd < dist.get(neighbor, math.inf):
                    dist[neighbor] = nd
                    prev[neighbor] = node
                    heapq.heappush(heap, (nd, neighbor))

        if end not in dist:
            return None

        path = [end]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path, dist[end]
