# Simulador de flota — Evaluación MS4M

Aplicación full stack que carga una red vial minera desde un JSON, la visualiza en un mapa y simula cinco camiones desplazándose desde ubicaciones de carga hacia ubicaciones de descarga sobre los tramos disponibles, con reporte de velocidades y explicación en lenguaje humano.

- **Frontend (demo):** https://fleet-simulator-ms4m.vercel.app — React (Vite) + Leaflet, desplegado en Vercel
- **Backend (API):** https://fleet-simulator-ms4m-production.up.railway.app — Python 3.12 / FastAPI, desplegado en Railway
- **Documentación interactiva de la API:** https://fleet-simulator-ms4m-production.up.railway.app/docs

## Arquitectura

```
backend/
  app/
    main.py            arranque, CORS, ciclo de vida
    config.py          configuración vía variables de entorno (prefijo SIM_)
    schemas.py         contratos Pydantic de la API
    services/
      data_loader.py   carga y validación del JSON (no modifica el archivo)
      graph.py         grafo vial, componentes conectados y Dijkstra
      simulation.py    motor de simulación en memoria (asyncio + semilla)
      report.py        estadísticas y explicación heurística
    api/routes.py      endpoints REST + SSE
  tests/               pytest (unitarios + API)
  data-prueba.json     insumo (solo lectura)
  Dockerfile           imagen para Railway (usuario no-root)
frontend/
  src/                 React: mapa Leaflet, panel de flota, reporte
```

## Ejecución local

Backend (puerto 8000):

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # Linux/macOS: .venv/bin/pip
.venv\Scripts\uvicorn app.main:app --reload
```

Frontend (puerto 5173):

```bash
cd frontend
npm install
copy .env.example .env        # ajustar VITE_API_URL si el backend no está en localhost:8000
npm run dev
```

Tests del backend:

```bash
cd backend
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `SIM_DATA_FILE_PATH` | `backend/data-prueba.json` | Ruta del JSON de insumo |
| `SIM_SPEED_MIN_KMH` | `15` | Velocidad mínima generada |
| `SIM_SPEED_MAX_KMH` | `45` | Velocidad máxima generada |
| `SIM_TICK_SECONDS` | `1.0` | Intervalo de actualización de la simulación |
| `SIM_REPORT_DEVIATION_THRESHOLD_PCT` | `10` | Umbral (%) para destacar desvíos vs. promedio de flota |
| `SIM_REPORT_MIN_SAMPLES` | `10` | Mínimo de muestras antes de advertir baja representatividad |
| `SIM_CORS_ORIGINS` | `http://localhost:5173` | Orígenes permitidos, separados por coma |
| `VITE_API_URL` (frontend) | `http://localhost:8000` | URL base del backend |

## Contrato API

La documentación se genera automáticamente desde el código (OpenAPI) y se sirve en el propio backend:

| Recurso | Local | Producción |
|---|---|---|
| Swagger UI (interactiva, permite ejecutar endpoints) | http://localhost:8000/docs | https://fleet-simulator-ms4m-production.up.railway.app/docs |
| ReDoc (solo lectura) | http://localhost:8000/redoc | https://fleet-simulator-ms4m-production.up.railway.app/redoc |
| Especificación OpenAPI (JSON) | http://localhost:8000/openapi.json | https://fleet-simulator-ms4m-production.up.railway.app/openapi.json |

Resumen de endpoints:

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio |
| GET | `/api/routes` | Tramos con polilínea y color |
| GET | `/api/locations/loads` | Ubicaciones de carga |
| GET | `/api/locations/dumps` | Ubicaciones de descarga |
| GET | `/api/network/validation` | Anomalías detectadas en el JSON de entrada |
| GET | `/api/network/info` | Nodos, aristas y componentes conectados del grafo |
| POST | `/api/simulation` | Crea e inicia la simulación (reemplaza la anterior). Body opcional: `{"seed": 42}` |
| GET | `/api/simulation` | Estado actual (camiones, posiciones, velocidades, asignaciones) |
| GET | `/api/simulation/stream` | SSE: estado en cada tick; evento `end` al finalizar |
| POST | `/api/simulation/pause` | Pausa el avance conservando el estado |
| POST | `/api/simulation/resume` | Reanuda desde donde quedó, sin saltos de tiempo |
| POST | `/api/simulation/speed` | Cambia el factor de velocidad de la simulación (1x a 8x). Body: `{"factor": 4}` |
| GET | `/api/simulation/trucks/{id}/path` | Recorrido completo asignado a un camión, con origen y destino |
| GET | `/api/simulation/report` | Reporte por camión + explicación en lenguaje humano |

Errores: `404` si no hay simulación activa o el camión no existe, `409` al intentar avanzar una simulación finalizada, `422` si no se pudo asignar un par carga/descarga alcanzable o el body es inválido. Formato: `{"detail": "mensaje"}`.

Nota sobre `speed`: el factor multiplica el tiempo real transcurrido, pero el motor avanza siempre en pasos exactos del tick configurado (con residuo acumulado), de modo que cada muestra representa el mismo intervalo simulado y el promedio del reporte sigue siendo una media aritmética válida aunque el factor cambie a mitad de simulación.

Ejemplo de respuesta de `POST /api/simulation` (recortado):

```json
{
  "id": "a1b2c3d4e5f6",
  "status": "running",
  "seed": 42,
  "trucks": [
    {
      "id": "CAM-001",
      "status": "en_route",
      "position": [-15.1521, -75.7238],
      "speed_kmh": 32.4,
      "progress_pct": 12.5,
      "origin_name": "MJ-692_CA15",
      "destination_name": "STK-806-SUL10_C"
    }
  ],
  "assignments": [
    {
      "truck_id": "CAM-001",
      "load_id": 4,
      "dump_id": 21,
      "distance_m": 3120.2,
      "rejected_pairs": [
        {
          "load_id": 9,
          "dump_id": 55,
          "reason": "sin recorrido: origen y destino en componentes desconectados"
        }
      ]
    }
  ]
}
```

## Decisiones de diseño (respuestas del formato)

### Backend y API

Construí el backend con FastAPI porque genera la documentación Swagger y OpenAPI automáticamente desde los modelos Pydantic, de modo que el contrato publicado siempre coincide con el código, y porque su soporte asyncio permite que la simulación corra en segundo plano mientras la API sigue atendiendo peticiones. Para las actualizaciones en vivo usé SSE. La información viaja en un solo sentido, del servidor al navegador, así que no necesitaba el canal bidireccional de WebSocket, que además es más complejo de operar detrás de proxies. La alternativa considerada fue polling, más simple pero con retardo y peticiones redundantes. Con más tiempo permitiría varias simulaciones concurrentes y versionaría la API para evolucionarla sin romper a los clientes existentes.

### Red y selección de recorridos

Convertí los tramos en un grafo no dirigido donde cada punto de una polilínea es un nodo y cada par consecutivo forma una arista cuyo costo es la distancia geográfica real (haversine, en metros). Verifiqué que los tramos que se unen comparten coordenadas exactamente iguales, así que la propia coordenada sirve como identificador de nodo sin necesidad de pegar puntos cercanos por tolerancia. La ruta se calcula con Dijkstra implementado a mano sobre una cola de prioridad, el grafo es pequeño y así evito una dependencia dejando el criterio algorítmico explícito. Al construir el grafo se detectan los componentes conectados (el dataset tiene 4, uno principal y 3 aislados) y si un par de carga y descarga no está en el mismo componente se descarta, se intenta otro y el descarte queda visible en la respuesta de la API. Con más tiempo usaría el algoritmo A estrella, que llega al mismo resultado explorando menos nodos.

### Simulación

La simulación vive en memoria del servidor. Al crearla nacen los cinco camiones, cada uno con un origen de carga y un destino de descarga verificado como alcanzable. Un proceso en segundo plano avanza la simulación cada tick según el tiempo real transcurrido, cada camión recibe una velocidad aleatoria dentro del rango configurable (15 a 45 km/h por defecto) y su posición se interpola sobre la polilínea de su recorrido, de modo que nunca se sale de la red y termina exactamente en el destino. Con una semilla la corrida se repite idéntica, lo que hace las pruebas reproducibles. El motor también soporta pausa sin saltos de tiempo y un factor de velocidad de x1 a x8 que acelera sin comprometer los datos porque siempre avanza en pasos exactos del tick. Consideré velocidades suavizadas, más realistas, pero el rango uniforme es más fácil de documentar y verificar. Con más tiempo modelaría el ciclo minero completo y agregaría persistencia del historial.

### Frontend

La interfaz es una sola pantalla con el mapa como protagonista y un panel lateral con la flota y el reporte, porque toda la información del problema es espacial. Los tramos se dibujan con su color original, las cargas y descargas se distinguen por color y los camiones son marcadores numerados que se actualizan en vivo por SSE, con carga automática del reporte al terminar. Para la legibilidad, los tamaños de marcadores y trazos se reducen al alejar el zoom, y al hacer clic en un camión se resalta su recorrido con banderas de inicio y fin mientras el resto se atenúa. Ese recorrido se pide a la API solo en ese momento para no engordar cada mensaje SSE. Los estados de carga, error y ausencia de datos son explícitos. Consideré MapLibre GL, mejor para escenas con miles de elementos, pero para 553 tramos Leaflet es suficiente y más directo. Con más tiempo animaría el movimiento entre ticks para que se vea continuo.

### Reporte y explicación heurística

El reporte calcula por camión la cantidad de muestras y las velocidades mínima, máxima y promedio. El promedio es la media aritmética simple, válida porque todas las muestras representan el mismo intervalo de tiempo, algo que el motor garantiza incluso al acelerar la simulación. La explicación se construye solo con los valores calculados, sin inventar cifras. Identifica el camión más rápido y el más lento, muestra el desvío de cada camión frente al promedio de la flota y lo comenta cuando supera un umbral configurable, además de advertir cuando hay pocas muestras. No usé un LLM porque el formato lo marca opcional y las reglas heurísticas son deterministas, se prueban con tests y no dependen de servicios externos ni credenciales. Con más tiempo integraría un LLM que reciba el JSON del reporte como datos estructurados, sin exponer secretos y con la heurística actual como respuesta de respaldo cuando el servicio no esté disponible, y agregaría el promedio ponderado por tiempo para escenarios con muestreo variable.

## Supuestos y limitaciones

- El camión parte del **nodo de red más cercano** a la coordenada de la carga y llega al más cercano a la descarga (todas las ubicaciones están a <100 m de la red en el dataset); no se dibuja conector fuera de la red.
- Los nombres duplicados de tramos/ubicaciones se toleran: el identificador operativo es siempre el id numérico. Las anomalías del JSON se exponen en `/api/network/validation` sin modificar el archivo.
- Una sola simulación activa a la vez; `POST /api/simulation` reinicia reemplazando la anterior. El estado vive en memoria y se pierde al reiniciar el proceso (aceptado por el formato).
- El promedio del reporte asume ticks uniformes; el dt real puede variar milisegundos entre ticks, efecto despreciable para el indicador.


## Despliegue

- **Frontend (Vercel):** proyecto apuntando a `frontend/`, build `npm run build`, output `dist/`, con `VITE_API_URL` apuntando al backend público.
- **Backend (Railway):** servicio con *Root Directory* `backend/`; Railway construye el `Dockerfile` (imagen `python:3.12-slim`, proceso con usuario no-root). Configurar `SIM_CORS_ORIGINS` con el dominio de Vercel. Se eligió Railway sobre Render porque su plan de prueba no suspende el servicio por inactividad, evitando arranques en frío durante la revisión.

## Uso de IA

El desarrollo se realizó con asistencia de Claude Code bajo revisión y decisión humana en cada paso, el análisis previo del dataset (estructura, componentes conectados, anomalías) definió el diseño; la elección de stack, algoritmo de ruteo, mecanismo de tiempo real y heurísticas del reporte fueron decisiones técnicas discutidas y aprobadas antes de implementar. Todo el código generado fue verificado con la suite de tests (30 pruebas) y smoke tests contra el dataset real.
