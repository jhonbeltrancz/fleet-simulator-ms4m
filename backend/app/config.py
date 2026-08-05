from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración vía variables de entorno con prefijo SIM_."""

    data_file_path: str = str(Path(__file__).resolve().parents[1] / "data-prueba.json")

    # Rango de velocidades aleatorias (km/h) e intervalo de actualización
    speed_min_kmh: float = 15.0
    speed_max_kmh: float = 45.0
    tick_seconds: float = 1.0

    # Umbrales de la explicación heurística del reporte
    report_deviation_threshold_pct: float = 10.0
    report_min_samples: int = 10

    cors_origins: str = "http://localhost:5173"

    model_config = {"env_prefix": "SIM_", "env_file": ".env"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
