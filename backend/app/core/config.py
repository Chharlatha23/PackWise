APP_TITLE = "PackWise API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "PackWise: Evidence-Driven Inverse-Design Food Packaging Recommendation System. "
    "Features evidence-driven food property inference, packaging requirement estimation, "
    "scientific hard-constraint feasibility evaluation (FEASIBLE, INFEASIBLE, UNKNOWN), "
    "multi-objective non-dominated Pareto front construction, pluggable inverse-design search "
    "(M9 deterministic enumeration, M10 adaptive heuristic search, M11 AI surrogate-assisted prioritization), "
    "exact-physics constraint verification, comprehensive explainability and counterfactual audits, "
    "and empirical trial feedback with model-update governance."
)

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_SQLITE_PATH = (_PROJECT_ROOT / "food_packaging.db").as_posix()

def _resolve_database_url(url: str) -> str:
    """Normalize relative sqlite paths to the project root for cross-platform portability."""
    if url.startswith("sqlite:///") and not url.startswith("sqlite:///:memory:"):
        path_part = url[len("sqlite:///"):]
        # If relative or generic name, anchor to project root
        p = Path(path_part)
        if not p.is_absolute():
            return f"sqlite:///{(_PROJECT_ROOT / p).as_posix()}"
    return url

class Settings:
    _raw_db_url: str = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_SQLITE_PATH}")
    DATABASE_URL: str = _resolve_database_url(_raw_db_url)
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    
    # CORS Origins: support both localhost and 127.0.0.1 for development, plus custom env
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    if FRONTEND_URL and FRONTEND_URL not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(FRONTEND_URL)

settings = Settings()
