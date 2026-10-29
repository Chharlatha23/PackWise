import sys
from pathlib import Path

# Ensure project root and backend are in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND = _ROOT / "backend"
for _p in [str(_ROOT), str(_BACKEND)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.auth_routes import auth_router
from app.core.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION, settings
from app.core.database import engine, Base
import app.models  # Ensure all SQLAlchemy models are registered

# Ensure tables exist (graceful fallback if schema is already managed by MySQL / Alembic)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    # Dialect specific warning or existing schema
    pass

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import RedirectResponse

@app.get("/")
def root():
    return {
        "service": APP_TITLE,
        "version": APP_VERSION,
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
        "frontend": settings.FRONTEND_URL,
    }

app.include_router(router)
app.include_router(auth_router)

