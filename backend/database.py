"""
backend/database.py
-------------------
Database connection and session management for NoteMind AI.
Configured for TiDB Cloud Serverless (MySQL).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# Database URL fetch karein
db_url = settings.DATABASE_URL

# Agar URL 'mysql://' se shuru ho rahi ho toh pymysql driver enforce karein
if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

# SQLite ke liye fallback (agar local testing ho)
connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}

# Engine create karein with pooling for TiDB Cloud stability
engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,       # Connection alive hai ya nahi verify karega
    pool_recycle=300,         # Idle drops rokne ke liye har 5 min me connection refresh hoga
    pool_size=5,
    max_overflow=10
)

# Session factory bound to the database engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()


def get_db():
    """FastAPI dependency to yield database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()