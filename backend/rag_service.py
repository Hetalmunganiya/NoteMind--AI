"""
backend/rag_service.py
-----------------------
RAG and AI services for NoteMind AI.
Uses TF-IDF + FAISS for fast, reliable local search (no embedding API errors),
and Gemini 1.5-Flash for generative AI answers and study tools.
"""

import io
import json
import re
from typing import List, Tuple, Dict, Any
import numpy as np
import faiss
from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
import google.generativeai as genai

from config import settings

if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

GEMINI_MODEL_NAME = "gemini-3.6-flash"

# Global vectorizer store for search matching
vectorizer = TfidfVectorizer(max_features=768, stop_words="english")


def _call_gemini(prompt: str) -> str:
    """Helper function to query Gemini API safely."""
    if not settings.GEMINI_API_KEY:
        return "Gemini API key is not configured. Please set GEMINI_API_KEY in .env."
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error communicating with Gemini AI: {str(e)}"


def extract_text_from_pdf(file_bytes: bytes) -> str:
    pdf_file = io.BytesIO(file_bytes)
    reader = PdfReader(pdf_file)
    extracted_text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            extracted_text.append(page_text)
    return "\n".join(extracted_text)


def create_chunks(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    cleaned_text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    start = 0
    text_length = len(cleaned_text)

    if text_length <= chunk_size:
        return [cleaned_text] if cleaned_text else []

    while start < text_length:
        end = start + chunk_size
        chunk = cleaned_text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def process_pdf(file_bytes: bytes) -> Tuple[List[str], faiss.IndexFlatL2, str]:
    full_text = extract_text_from_pdf(file_bytes)
    if not full_text.strip():
        raise ValueError("The uploaded PDF does not contain extractable text.")

    chunks = create_chunks(
        full_text,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )

    # Fast local TF-IDF vectorization (No Google API dependency for embeddings)
    tfidf_matrix = vectorizer.fit_transform(chunks).toarray().astype(np.float32)
    
    # Normalize vectors for cosine similarity search
    faiss.normalize_L2(tfidf_matrix)

    dimension = tfidf_matrix.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(tfidf_matrix)

    return chunks, index, full_text


def ask_question(
    question: str, index: faiss.IndexFlatIP, chunks: List[str], top_k: int = 5
) -> Tuple[str, List[str]]:
    query_vec = vectorizer.transform([question]).toarray().astype(np.float32)
    faiss.normalize_L2(query_vec)

    actual_k = min(top_k, len(chunks))
    distances, indices = index.search(query_vec, actual_k)

    retrieved_chunks = [chunks[idx] for idx in indices[0] if idx < len(chunks)]
    context = "\n---\n".join(retrieved_chunks)

    prompt = f"""You are NoteMind AI, an intelligent and helpful study assistant.
Use the following context extracted from a study document to answer the student's question accurately.
If the answer cannot be found in the context, state that clearly, but provide helpful general knowledge if relevant.

Context from Document:
{context}

Question:
{question}

Answer:"""

    answer = _call_gemini(prompt)
    return answer, retrieved_chunks


def generate_study_notes(full_text: str) -> str:
    sample_text = full_text[:15000]
    prompt = f"""You are an expert tutor. Create clear, comprehensive, and well-organized study notes based on the following text.
Use Markdown formatting with main headings, sub-headings, bullet points, and highlight important definitions.

Document Content:
{sample_text}

Structured Study Notes:"""
    return _call_gemini(prompt)


def generate_summary_and_keypoints(full_text: str) -> Tuple[str, List[str]]:
    sample_text = full_text[:15000]
    prompt = f"""Summarize the following study document.
Respond ONLY in this exact JSON format:
{{
  "summary": "A concise 2-3 paragraph summary of the entire document.",
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3",
    "Key point 4",
    "Key point 5"
  ]
}}

Document Content:
{sample_text}"""

    raw_response = _call_gemini(prompt)
    try:
        clean_json = raw_response.strip()
        clean_json = re.sub(r"^```json\s*", "", clean_json, flags=re.MULTILINE)
        clean_json = re.sub(r"^```\s*", "", clean_json, flags=re.MULTILINE)
        clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

        data = json.loads(clean_json)
        summary = data.get("summary", "Summary could not be generated.")
        key_points = data.get("key_points", [])
        return summary, key_points
    except Exception:
        return raw_response, []


def generate_eli5(concept_or_text: str) -> str:
    prompt = f"""Explain the following concept or text like I am 5 years old (ELI5).
Use simple words, intuitive real-world analogies, and keep it fun and engaging.

Topic / Content:
{concept_or_text}

ELI5 Explanation:"""
    return _call_gemini(prompt)


def generate_mcq_quiz(full_text: str, num_questions: int = 5) -> List[Dict[str, Any]]:
    sample_text = full_text[:15000]
    prompt = f"""Generate {num_questions} multiple-choice quiz questions (MCQs) based on the text below to test student comprehension.
Each question must have 4 distinct options and a clear correct answer.

Respond ONLY with a valid raw JSON array of objects. Do not add markdown fences, comments, or extra text.
Schema:
[
  {{
    "question": "Question text here?",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "answer": "Exact text of the correct option here"
  }}
]

Document Content:
{sample_text}"""

    raw_response = _call_gemini(prompt)
    try:
        clean_json = raw_response.strip()
        clean_json = re.sub(r"^```json\s*", "", clean_json, flags=re.MULTILINE)
        clean_json = re.sub(r"^```\s*", "", clean_json, flags=re.MULTILINE)
        clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

        quiz_data = json.loads(clean_json)
        if isinstance(quiz_data, list):
            for q in quiz_data:
                if "correct_answer" in q and "answer" not in q:
                    q["answer"] = q["correct_answer"]
            return quiz_data
        return []
    except Exception as e:
        print(f"Quiz JSON parse error: {e}")
        return []