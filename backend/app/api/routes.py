import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..schemas import (
    ApiError,
    LocationOut,
    NetworkInfo,
    RouteOut,
    SimulationCreate,
    SimulationReport,
    SimulationState,
    SpeedRequest,
    TruckPath,
    ValidationReport,
)
from ..services.report import build_report
from ..services.simulation import AssignmentError

router = APIRouter(prefix="/api")

SIM_NOT_FOUND = {404: {"model": ApiError, "description": "No hay simulación activa"}}


@router.get("/routes", response_model=list[RouteOut], tags=["red vial"])
def get_routes(request: Request):
    return request.app.state.dataset.routes


@router.get("/locations/loads", response_model=list[LocationOut], tags=["red vial"])
def get_loads(request: Request):
    return request.app.state.dataset.loads


@router.get("/locations/dumps", response_model=list[LocationOut], tags=["red vial"])
def get_dumps(request: Request):
    return request.app.state.dataset.dumps


@router.get("/network/validation", response_model=ValidationReport, tags=["red vial"])
def get_validation(request: Request):
    return request.app.state.dataset.validation


@router.get("/network/info", response_model=NetworkInfo, tags=["red vial"])
def get_network_info(request: Request):
    network = request.app.state.network
    return NetworkInfo(
        nodes=len(network.adjacency),
        edges=network.edge_count,
        connected_components=network.component_count,
        main_component_size=network.main_component_size,
    )


# async: asyncio.create_task del loop de simulación requiere el event loop activo
@router.post("/simulation", response_model=SimulationState, status_code=201, tags=["simulación"])
async def create_simulation(request: Request, body: SimulationCreate | None = None):
    """Crea e inicia una simulación de 5 camiones; si había una activa, la reemplaza."""
    seed = body.seed if body else None
    try:
        sim = request.app.state.sim_manager.start(seed)
    except AssignmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return sim.to_state()


def _get_current_sim(request: Request):
    sim = request.app.state.sim_manager.current
    if sim is None:
        raise HTTPException(status_code=404, detail="No hay ninguna simulación activa. Cree una con POST /api/simulation")
    return sim


@router.get("/simulation", response_model=SimulationState, responses=SIM_NOT_FOUND, tags=["simulación"])
def get_simulation(request: Request):
    return _get_current_sim(request).to_state()


@router.get("/simulation/stream", responses=SIM_NOT_FOUND, tags=["simulación"])
async def stream_simulation(request: Request):
    """SSE con el estado de la simulación en cada tick; termina al finalizar la flota."""
    sim = _get_current_sim(request)
    tick = request.app.state.settings.tick_seconds

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            payload = sim.to_state().model_dump_json()
            yield f"data: {payload}\n\n"
            if sim.status == "finished":
                yield f"event: end\ndata: {json.dumps({'simulation_id': sim.id})}\n\n"
                break
            await asyncio.sleep(tick)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/simulation/pause", response_model=SimulationState, responses=SIM_NOT_FOUND, tags=["simulación"])
def pause_simulation(request: Request):
    """Pausa el avance de la simulación conservando todo su estado."""
    sim = _get_current_sim(request)
    if sim.status == "finished":
        raise HTTPException(status_code=409, detail="La simulación ya finalizó; reiníciela para continuar")
    sim.paused = True
    return sim.to_state()


@router.post("/simulation/resume", response_model=SimulationState, responses=SIM_NOT_FOUND, tags=["simulación"])
def resume_simulation(request: Request):
    """Reanuda una simulación pausada desde donde quedó."""
    sim = _get_current_sim(request)
    if sim.status == "finished":
        raise HTTPException(status_code=409, detail="La simulación ya finalizó; reiníciela para continuar")
    sim.paused = False
    return sim.to_state()


@router.post("/simulation/speed", response_model=SimulationState, responses=SIM_NOT_FOUND, tags=["simulación"])
def set_simulation_speed(request: Request, body: SpeedRequest):
    """Cambia el factor de velocidad de la simulación (1x a 8x) sin alterar el muestreo."""
    sim = _get_current_sim(request)
    if sim.status == "finished":
        raise HTTPException(status_code=409, detail="La simulación ya finalizó; reiníciela para continuar")
    sim.time_scale = body.factor
    return sim.to_state()


@router.get("/simulation/trucks/{truck_id}/path", response_model=TruckPath, responses=SIM_NOT_FOUND, tags=["simulación"])
def get_truck_path(request: Request, truck_id: str):
    """Recorrido completo asignado a un camión, con su origen y destino."""
    sim = _get_current_sim(request)
    truck = next((t for t in sim.trucks if t.id == truck_id), None)
    if truck is None:
        raise HTTPException(status_code=404, detail=f"No existe el camión {truck_id} en la simulación actual")
    return TruckPath(truck_id=truck.id, origin=truck.origin, destination=truck.destination, path=truck.path)


@router.get("/simulation/report", response_model=SimulationReport, responses=SIM_NOT_FOUND, tags=["simulación"])
def get_report(request: Request):
    sim = _get_current_sim(request)
    return build_report(sim, request.app.state.settings)
