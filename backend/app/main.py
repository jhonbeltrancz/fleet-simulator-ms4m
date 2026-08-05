from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .services.data_loader import load_dataset
from .services.graph import RoadNetwork
from .services.simulation import SimulationManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    dataset = load_dataset(settings.data_file_path)
    network = RoadNetwork(dataset)
    app.state.settings = settings
    app.state.dataset = dataset
    app.state.network = network
    app.state.sim_manager = SimulationManager(dataset, network, settings)
    yield
    app.state.sim_manager.stop()


app = FastAPI(
    title="Simulador de Flota MS4M",
    description="API para visualizar la red vial y simular una flota de camiones sobre ella.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["salud"])
def health():
    return {"status": "ok"}
