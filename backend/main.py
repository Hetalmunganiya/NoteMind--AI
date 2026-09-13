"""
backend/main.py
----------------
FastAPI REST API application for NoteMind AI.
Exposes endpoints for User Authentication, PDF Processing,
Vector Search / Q&A, Notes Generation, ELI5, MCQ Quizzes, and Notes History.
"""

import uuid
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import engine, Base, get_db
import models
import schemas
import auth
import rag_service

# Create database tables automatically if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NoteMind AI - Backend API",
    description="Intelligent PDF Study Assistant with RAG, Summarization, ELI5, and Quiz Generation",
    version="1.0.0",
)

# Enable CORS so Streamlit frontend can communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active document sessions
DOC_SESSIONS: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------
# Helper Request Schemas for Session-based Endpoints
# ---------------------------------------------------------------------

class SessionRequest(BaseModel):
    session_id: str


class Eli5Request(BaseModel):
    concept: str


# =====================================================================
# 1. Authentication Endpoints
# =====================================================================

@app.post("/api/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user with email and password."""
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    hashed_pwd = auth.hash_password(user_data.password)
    new_user = models.User(email=user_data.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/api/login", response_model=schemas.Token)
def login(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Authenticate user credentials and return a JWT access token."""
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# =====================================================================
# 2. PDF Upload & Vector Indexing Endpoint
# =====================================================================

@app.post("/api/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Upload a PDF file, extract text, build FAISS vector index,
    and create an active study session.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported."
        )

    try:
        file_bytes = await file.read()
        chunks, index, full_text = rag_service.process_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process PDF: {str(e)}"
        )

    session_id = str(uuid.uuid4())
    DOC_SESSIONS[session_id] = {
        "chunks": chunks,
        "index": index,
        "full_text": full_text,
        "filename": file.filename,
        "user_id": current_user.id,
    }

    return {
        "session_id": session_id,
        "filename": file.filename,
        "total_chunks": len(chunks),
        "message": "PDF processed and indexed successfully.",
    }


# =====================================================================
# 3. AI Study Features (Notes, Chat, Summary, ELI5, Quiz)
# =====================================================================

@app.post("/api/chat", response_model=schemas.AskQuestionResponse)
def chat_with_pdf(
    req: schemas.AskQuestionRequest,
    current_user: models.User = Depends(auth.get_current_user),
):
    """Ask questions against the uploaded PDF using FAISS semantic search and Gemini."""
    if not req.session_id or req.session_id not in DOC_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session not found. Please upload a PDF first."
        )

    session_data = DOC_SESSIONS[req.session_id]
    answer, sources = rag_service.ask_question(
        question=req.question,
        index=session_data["index"],
        chunks=session_data["chunks"],
    )
    return {"answer": answer, "sources": sources}


@app.post("/api/generate-notes")
def generate_notes(
    req: SessionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Generate structured revision notes, summary, key points, and save them to the database."""
    if req.session_id not in DOC_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session not found. Please upload a PDF first."
        )

    session_data = DOC_SESSIONS[req.session_id]
    full_text = session_data["full_text"]

    notes = rag_service.generate_study_notes(full_text)
    summary, key_points = rag_service.generate_summary_and_keypoints(full_text)

    # Save generated study note to database
    new_note = models.Note(
        user_id=current_user.id,
        title=session_data["filename"].replace(".pdf", ""),
        filename=session_data["filename"],
        summary=summary,
        key_points="\n".join(key_points) if isinstance(key_points, list) else str(key_points),
        notes_content=notes,
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return {
        "note_id": new_note.id,
        "title": new_note.title,
        "notes": notes,
        "notes_content": notes,
        "summary": summary,
        "key_points": key_points,
    }


@app.post("/api/summary")
def get_summary(
    req: SessionRequest,
    current_user: models.User = Depends(auth.get_current_user),
):
    """Generate a quick summary and key takeaway points from the uploaded PDF."""
    if req.session_id not in DOC_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session not found. Please upload a PDF first."
        )

    session_data = DOC_SESSIONS[req.session_id]
    summary, key_points = rag_service.generate_summary_and_keypoints(session_data["full_text"])
    return {"summary": summary, "key_points": key_points}


@app.post("/api/eli5")
def eli5_explanation(
    req: Eli5Request,
    current_user: models.User = Depends(auth.get_current_user),
):
    """Simplify any complex concept using the ELI5 (Explain Like I'm 5) technique."""
    explanation = rag_service.generate_eli5(req.concept)
    return {"concept": req.concept, "explanation": explanation}


@app.post("/api/quiz", response_model=schemas.QuizResponse)
def get_quiz(
    req: SessionRequest,
    current_user: models.User = Depends(auth.get_current_user),
):
    """Generate a multiple-choice practice quiz based on the PDF contents."""
    if req.session_id not in DOC_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session not found. Please upload a PDF first."
        )

    session_data = DOC_SESSIONS[req.session_id]
    quiz_data = rag_service.generate_mcq_quiz(session_data["full_text"], num_questions=5)

    # Normalize keys so both 'answer' and 'correct_answer' exist to satisfy Pydantic schema & UI
    for q in quiz_data:
        val = q.get("answer") or q.get("correct_answer")
        q["answer"] = val
        q["correct_answer"] = val

    return {"quiz": quiz_data}


# =====================================================================
# 4. Saved Notes Management (CRUD)
# =====================================================================

@app.get("/api/notes")
def get_user_notes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Retrieve all previously saved notes and summaries for the current user.
    Maps both `notes` and `notes_content` so Streamlit displays full notes without missing fields.
    """
    notes = (
        db.query(models.Note)
        .filter(models.Note.user_id == current_user.id)
        .order_by(models.Note.created_at.desc())
        .all()
    )
    result = []
    for n in notes:
        content = n.notes_content if getattr(n, "notes_content", None) else ""
        result.append({
            "id": n.id,
            "title": n.title,
            "filename": getattr(n, "filename", ""),
            "summary": n.summary or "",
            "key_points": n.key_points or "",
            "notes": content,
            "notes_content": content,
            "created_at": str(n.created_at) if getattr(n, "created_at", None) else "",
        })
    return result


@app.delete("/api/notes/{note_id}", status_code=status.HTTP_200_OK)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Delete a saved note belonging to the current user."""
    note = (
        db.query(models.Note)
        .filter(models.Note.id == note_id, models.Note.user_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found."
        )

    db.delete(note)
    db.commit()
    return {"message": f"Note {note_id} deleted successfully."}

