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
from typing import List, Optional
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

def _build_user_database_url() -> Optional[str]:
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_name = os.getenv("DB_NAME")

    if db_host and db_user and db_name:
        if db_port == "3306":
            pw_part = f":{db_password}" if db_password else ""
            port_part = f":{db_port}" if db_port else ":3306"
            return f"mysql+pymysql://{db_user}{pw_part}@{db_host}{port_part}/{db_name}"
        else:
            pw_part = f":{db_password}" if db_password else ""
            port_part = f":{db_port}" if db_port else ":5432"
            return f"postgresql+psycopg://{db_user}{pw_part}@{db_host}{port_part}/{db_name}"
    return None

def _build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return _resolve_database_url(explicit_url)
    return f"sqlite:///{_DEFAULT_SQLITE_PATH}"

class Settings:
    _raw_db_url: str = _build_database_url()
    DATABASE_URL: str = _raw_db_url
    USER_DATABASE_URL: Optional[str] = _build_user_database_url()
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

    # JWT Authentication & Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "packwise_secret_key_development_only_change_in_production_32char")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/login")

    # SMTP Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else 587
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "PackWise")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")
    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USERNAME", "foodpackai@gmail.com")))

settings = Settings()

