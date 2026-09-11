# 🧠 NoteMind AI – Intelligent PDF Study Assistant

NoteMind AI is a full-stack, beginner-friendly AI study assistant that transforms lecture notes, textbooks, and research papers into interactive study rooms. Upload any PDF to ask questions using context-aware Retrieval-Augmented Generation (RAG), generate structured revision notes and summaries, simplify difficult concepts with ELI5, and test your knowledge with interactive practice quizzes.

---

## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python REST API)
- **Frontend:** [Streamlit](https://streamlit.io/) (Clean, interactive Python web UI)
- **Database & ORM:** [MySQL](https://www.mysql.com/) with [SQLAlchemy](https://www.sqlalchemy.org/)
- **Vector Search (RAG):** [FAISS](https://github.com/facebookresearch/faiss) (`IndexFlatL2`, chunk size: 500, overlap: 100, top_k: 5)
- **Embeddings:** [Sentence Transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`)
- **LLM / AI Model:** [Google Gemini API](https://aistudio.google.com/) (`gemini-1.5-flash`)
- **Authentication:** JWT (JSON Web Tokens) with `bcrypt` password hashing

---

## ✨ Key Features

1. **🔐 User Authentication**
   - Secure registration and login with bcrypt password hashing and JWT authorization.
2. **📄 PDF Ingestion & Semantic Search**
   - Fast PDF text extraction, sliding-window chunking, and FAISS vector indexing.
3. **💬 Context-Aware Document Q&A**
   - Ask any question about your PDF and receive grounded answers with exact source chunk citations.
4. **📝 Automated Study Notes & Summaries**
   - Generates structured revision notes with main headings, subheadings, key points, and executive summaries (automatically saved to MySQL).
5. **🎯 Practice MCQ Quiz Generator**
   - Creates 5 interactive multiple-choice questions with instant scoring, feedback, and answer explanations.
6. **💡 ELI5 Concept Explainer**
   - Simplifies complex topics, jargon, and technical concepts using intuitive real-world analogies.
7. **📂 Saved Notes Management**
   - View, read, and delete past revision notes anytime from your saved study library.

---

## 📁 Project Structure

```text
notemind-ai/
│
├── backend/
│   ├── .env.example         # Environment variables template
│   ├── config.py            # App & Database configuration
│   ├── database.py          # SQLAlchemy database engine and session
│   ├── models.py            # User and Note ORM models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── auth.py              # Password hashing & JWT helpers
│   ├── rag_service.py       # PDF parsing, FAISS, Embeddings & Gemini
│   ├── main.py              # FastAPI REST endpoints
│   └── requirements.txt     # Python dependencies
│
├── frontend/
│   └── app.py               # Streamlit multi-tab user interface
│
└── README.md                # Project documentation