from datetime import datetime, timezone

from ..config import Settings
from ..schemas import SimulationReport, TruckReport
from .simulation import Simulation


def build_report(sim: Simulation, settings: Settings) -> SimulationReport:
    stats = []
    for truck in sim.trucks:
        speeds = [s.speed_kmh for s in truck.samples]
        # Media aritmética: los intervalos de muestreo son uniformes
        avg = sum(speeds) / len(speeds) if speeds else 0.0
        stats.append((truck.id, speeds, avg))

    fleet_avg = round(sum(avg for _, _, avg in stats) / len(stats), 2) if stats else 0.0

    trucks = [
        TruckReport(
            truck_id=truck_id,
            samples=len(speeds),
            speed_min_kmh=round(min(speeds), 2) if speeds else 0.0,
            speed_max_kmh=round(max(speeds), 2) if speeds else 0.0,
            speed_avg_kmh=round(avg, 2),
            deviation_from_fleet_pct=round((avg - fleet_avg) / fleet_avg * 100, 1) if fleet_avg > 0 else 0.0,
        )
        for truck_id, speeds, avg in stats
    ]

    return SimulationReport(
        simulation_id=sim.id,
        generated_at=datetime.now(timezone.utc),
        fleet_avg_kmh=fleet_avg,
        trucks=trucks,
        explanation=build_explanation(trucks, fleet_avg, settings),
    )


def build_explanation(trucks: list[TruckReport], fleet_avg: float, settings: Settings) -> list[str]:
    """Genera la explicación en lenguaje humano solo a partir de los valores calculados."""
    if not trucks or all(t.samples == 0 for t in trucks):
        return ["Aún no hay muestras suficientes para generar una explicación."]

    lines: list[str] = []
    threshold = settings.report_deviation_threshold_pct

    fastest = max(trucks, key=lambda t: t.speed_avg_kmh)
    slowest = min(trucks, key=lambda t: t.speed_avg_kmh)
    lines.append(
        f"La velocidad promedio de la flota es {fleet_avg} km/h. "
        f"El camión más rápido es {fastest.truck_id} ({fastest.speed_avg_kmh} km/h) "
        f"y el más lento es {slowest.truck_id} ({slowest.speed_avg_kmh} km/h)."
    )

    for t in trucks:
        if t.deviation_from_fleet_pct > threshold:
            lines.append(
                f"{t.truck_id} está un {abs(t.deviation_from_fleet_pct)}% por encima del promedio de la flota."
            )
        elif t.deviation_from_fleet_pct < -threshold:
            lines.append(
                f"{t.truck_id} está un {abs(t.deviation_from_fleet_pct)}% por debajo del promedio de la flota."
            )

    spread = fastest.speed_avg_kmh - slowest.speed_avg_kmh
    if fleet_avg > 0 and spread / fleet_avg * 100 <= threshold:
        lines.append(
            f"Los promedios de los camiones son homogéneos: la diferencia máxima entre ellos "
            f"es de {round(spread, 2)} km/h, dentro del umbral del {threshold}%."
        )

    low_sample = [t.truck_id for t in trucks if t.samples < settings.report_min_samples]
    if low_sample:
        lines.append(
            f"Advertencia: {', '.join(low_sample)} tiene(n) menos de {settings.report_min_samples} muestras; "
            "sus estadísticas pueden no ser representativas."
        )

    return lines
