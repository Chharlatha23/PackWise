APP_TITLE = "FoodPack AI API"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = (
    "Phase 1: Project Foundation + Input Validation. "
    "Material recommendation, optimization, and AI features are not yet implemented."
)

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:5432/food_packaging_db")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

settings = Settings()
