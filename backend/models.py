"""
backend/models.py
-----------------
SQLAlchemy ORM models defining the database schema for NoteMind AI.
Includes the User and Note tables with their relationships.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    """
    User model representing registered users.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # One-to-many relationship: One user can have multiple notes
    # Cascade delete ensures user's notes are removed if the user is deleted
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")


class Note(Base):
    """
    Note model representing uploaded PDF study materials and AI-generated content.
    """
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)
    notes_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Many-to-one relationship back to the User
    owner = relationship("User", back_populates="notes")

    