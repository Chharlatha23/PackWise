from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os

# Default to Postgres, but allow SQLite for testing migrations/connectivity in isolated environments
url = os.environ.get("USE_TEST_DB_URL", settings.DATABASE_URL)

connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
