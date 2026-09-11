"""
backend/config.py
-----------------
Configuration settings for NoteMind AI.
Loads environment variables from a .env file and provides default fallbacks.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()


class Settings:
    # -----------------------------
    # Database Configuration
    # -----------------------------
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "notemind_db")

    # Render ka DATABASE_URL pehle read karein, agar na mile tab MySQL fallback lein
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # -----------------------------
    # JWT Authentication
    # -----------------------------
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "super_secret_notemind_jwt_key_change_in_production"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )  # Default: 24 hours

    # -----------------------------
    # Google Gemini API
    # -----------------------------
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # -----------------------------
    # Vector Search & RAG Settings
    # -----------------------------
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    TOP_K: int = 5
    EMBEDDING_MODEL_NAME: str = "models/text-embedding-004"


# Create a single reusable instance
settings = Settings()