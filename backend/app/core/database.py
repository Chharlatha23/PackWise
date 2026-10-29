from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import os

# Default to Postgres / SQLite for scientific inverse-design engine
url = os.environ.get("USE_TEST_DB_URL", settings.DATABASE_URL)

connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# User / Auth DB Engine (supports MySQL foodpack_ai when DB_HOST is set, or falls back to engine)
user_db_url = os.environ.get("USE_TEST_DB_URL", settings.USER_DATABASE_URL or settings.DATABASE_URL)
user_connect_args = {"check_same_thread": False} if user_db_url.startswith("sqlite") else {}
user_engine = create_engine(user_db_url, connect_args=user_connect_args)
UserSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_db():
    db = UserSessionLocal()
    try:
        yield db
    finally:
        db.close()

