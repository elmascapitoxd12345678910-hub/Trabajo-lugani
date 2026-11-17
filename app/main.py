"""Punto de entrada principal de la aplicación FastAPI."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.database import Base, engine, get_db
import app.models  # noqa: F401 – registra todos los modelos en Base.metadata
from app.routers import auth_router, pedidos_router, productos_router, usuarios_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea todas las tablas e inicializa el catálogo si está vacío."""
    Base.metadata.create_all(bind=engine)
    # Migración defensiva: asegurar columna categoria en SQLite si la tabla productos ya existía
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(productos)"))
            columnas = [row[1] for row in result.fetchall()]
            if "categoria" not in columnas:
                conn.execute(text("ALTER TABLE productos ADD COLUMN categoria VARCHAR(100)"))
                conn.commit()
    except Exception:
        pass

    try:
        from app.seed import seed_productos
        seed_productos()
    except Exception as exc:
        import logging
        logging.getLogger("uvicorn.error").warning("Aviso durante seeding inicial: %s", exc)
    yield


# Inicialización de la aplicación FastAPI con metadata descriptiva
app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    description=(
        "Backend profesional de E-Commerce conforme a la Ley 24.240 de Defensa del Consumidor, "
        "Disposición 954/2025 (Botón de Arrepentimiento) y Ley 25.326 de Protección de Datos Personales."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración de CORSMiddleware
# En desarrollo: acepta todos los orígenes de la lista del .env (incluye todos los puertos de Vite)
_cors_origins = settings.origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Creación garantizada y montaje del directorio de archivos estáticos
Path("uploads/productos").mkdir(parents=True, exist_ok=True)
Path("app/static/demo").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory="uploads"), name="static")
app.mount("/demo", StaticFiles(directory="app/static/demo"), name="demo")

# Inclusión modular de routers
app.include_router(auth_router)
app.include_router(productos_router)
app.include_router(pedidos_router)
app.include_router(usuarios_router)


@app.get("/salud", tags=["Salud"])
def salud(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"estado": "ok", "base": "ok"}


@app.get(
    "/",
    tags=["General"],
    summary="Estado de la API y marco normativo",
    description="Endpoint raíz de verificación de disponibilidad y conformidad legal.",
)
def root() -> dict[str, str]:
    """Retorna el estado de disponibilidad y cumplimiento legal del servicio."""
    return {
        "proyecto": settings.PROJECT_NAME,
        "status": "online",
        "normativa": (
            "En cumplimiento estricto con la Ley 24.240 (Defensa del Consumidor), "
            "Disposición 954/2025 y Ley 25.326 (Protección de los Datos Personales)."
        ),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
