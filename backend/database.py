"""
backend/database.py
-------------------
Database connection and session management for NoteMind AI.
Sets up the SQLAlchemy engine, session maker, and base model class.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# Database URL fetch karein
db_url = settings.DATABASE_URL

# Render aur Neon ke postgres:// prefix ko SQLAlchemy-compatible postgresql:// me convert karein
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# SQLite ke liye check_same_thread chahiye hota hai, PostgreSQL ke liye nahi
connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}

# Engine create karein
engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True
)

# Session factory bound to the database engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all SQLAlchemy database models to inherit from
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session per request.
    Ensures the session is always closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()