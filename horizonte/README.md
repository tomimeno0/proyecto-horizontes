# Proyecto Horizonte

Horizonte es una API modular construida con FastAPI para explorar inferencias de IA abiertas, auditables y con gobernanza participativa. El repositorio incluye un núcleo transparente, auditoría verificable, tooling de calidad y stubs preparados para expansión en red y educación.

## Requisitos

- Python 3.12
- SQLite (incluido) o PostgreSQL (vía `DB_URL`)
- Make, Docker y Docker Compose opcionales para flujos alternativos

## Configuración local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn horizonte.api.main:app --reload
```

Variables configurables en `.env` (ver `.env.example`).

## Uso rápido

```bash
curl -X POST http://localhost:8000/inferencia \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Impacto de la deforestación en Sudamérica?"}'

curl http://localhost:8000/auditoria

curl http://localhost:8000/health
```

## Tooling y DX

```bash
make fmt    # black
make lint   # ruff
make type   # mypy
make test   # pytest
```

Para instalar pre-commit:

```bash
make prep
```

## Docker

```bash
docker compose up --build
```

El stack levanta:

- `api`: servicio FastAPI con rate limiting, CORS seguro y ledger SQLite.
- `verifier`: microservicio que expone `/health` y `/verify` para validar hashes.

### Fase 2 – Consenso y Transparencia

- Nodo verifier: simula validación distribuida.
- Dashboard: métricas públicas en /dashboard.
- Ejecutar con Docker:
  ```bash
  docker compose up --build
  ```

## Scripts útiles

```bash
python scripts/dev_seed.py  # Carga datos de ejemplo en el ledger
bash scripts/smoke.sh       # Smoke test end-to-end
```

## Tests

```bash
pytest -q
```

Las pruebas cubren inferencias, auditoría y núcleo determinista.

## Seguridad, auditoría y supervisión

- Limitación de tasa configurable con SlowAPI.
- Tamaño máximo de payload definido en configuración.
- Logging estructurado en JSON con identificación del nodo.
- Manejo consistente de errores y ocultamiento de trazas internas.
- `SecurityMonitor` calcula hashes de código, ledger y reportes auditados para detectar cambios no autorizados. Las correcciones en producción requieren aprobación explícita (`approved_by`).
- `audit_snapshot()` genera `horizonte/governance/audit_report.json` con firma SHA-256 y sello temporal; su contenido puede verificarse reproduciendo el hash del bloque `snapshot`.
- Nuevas rutas API:
  - `GET /supervision/status`: estado de integridad y alertas registradas.
  - `POST /audit/generate`: ejecuta una auditoría completa y devuelve el JSON firmado.
  - `GET /audit/report`: descarga el último informe disponible.
- Panel visual en `/dashboard/audit` (o `/audit`), donde puede generarse el informe, revisar incidencias y descargar el JSON firmado.
- Los hashes publicados permiten comparaciones entre nodos para confirmar sincronización ética, cognitiva y de red.

## Próximos pasos

Fase 2 contempla consenso entre nodos, dashboard público y sincronización gRPC real.

---
Made by ChatGPT (AUREUS Core — Proyecto Horizonte)
