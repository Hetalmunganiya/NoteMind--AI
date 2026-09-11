"""
frontend/app.py
----------------
Streamlit frontend for NoteMind AI (Intelligent PDF Study Assistant).
Connects to FastAPI backend for Authentication, PDF RAG QA, Notes Generation,
and Interactive Quizzes.
"""

import time
from datetime import datetime, timedelta
import streamlit as st
import requests
import extra_streamlit_components as stx

# Backend API Base URL
API_URL = "http://localhost:8000"

# ---------------------------------------------------------------------
# 1. Page Configuration & Session State Initialization
# ---------------------------------------------------------------------

st.set_page_config(
    page_title="NoteMind AI - Study Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit settings menu, header, footer, and deploy button
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

# Initialize Cookie Manager
cookie_manager = stx.CookieManager()

# Initialize persistent session state variables
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "just_logged_out" not in st.session_state:
    st.session_state.just_logged_out = False

# Auto-restore session from cookies on refresh (only if user didn't just logout)
if not st.session_state.just_logged_out:
    cookies = cookie_manager.get_all()
    if not st.session_state.token and cookies:
        saved_token = cookies.get("notemind_token")
        if saved_token and str(saved_token).strip():
            st.session_state.token = saved_token
            st.session_state.user_email = cookies.get("notemind_email")
            if "notemind_session_id" in cookies:
                st.session_state.session_id = cookies.get("notemind_session_id")
            if "notemind_filename" in cookies:
                st.session_state.uploaded_filename = cookies.get("notemind_filename")
            st.rerun()
else:
    st.session_state.just_logged_out = False


def get_auth_headers():
    """Return authorization headers with Bearer token."""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


# ---------------------------------------------------------------------
# 2. Sidebar: Authentication & Navigation
# ---------------------------------------------------------------------

with st.sidebar:
    st.title("🧠 NoteMind AI")
    st.caption("Your Intelligent PDF Study Assistant")
    st.markdown("---")

    if not st.session_state.token:
        # Show Login / Register forms when not logged in
        auth_mode = st.radio("Account Access", ["Login", "Register"], horizontal=True)

        if auth_mode == "Login":
            st.subheader("Login")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="student@example.com")
                password = st.text_input("Password", type="password")
                login_btn = st.form_submit_button("Sign In", use_container_width=True)

                if login_btn:
                    if email and password:
                        try:
                            res = requests.post(
                                f"{API_URL}/api/login",
                                json={"email": email, "password": password},
                            )
                            if res.status_code == 200:
                                data = res.json()
                                st.session_state.token = data["access_token"]
                                st.session_state.user_email = email
                                st.session_state.just_logged_out = False

                                # Save in cookies with 7-day expiration
                                expire_time = datetime.now() + timedelta(days=7)
                                cookie_manager.set("notemind_token", data["access_token"], expires_at=expire_time, key="set_tok")
                                cookie_manager.set("notemind_email", email, expires_at=expire_time, key="set_em")
                                time.sleep(0.3)

                                st.success("Logged in successfully!")
                                st.rerun()
                            else:
                                st.error(res.json().get("detail", "Login failed."))
                        except Exception as e:
                            st.error(f"Cannot connect to backend: {e}")
                    else:
                        st.warning("Please fill in both email and password.")

        else:
            st.subheader("Register")
            with st.form("register_form"):
                reg_email = st.text_input("Email", placeholder="student@example.com")
                reg_password = st.text_input("Password", type="password")
                reg_btn = st.form_submit_button("Create Account", use_container_width=True)

                if reg_btn:
                    if reg_email and reg_password:
                        try:
                            res = requests.post(
                                f"{API_URL}/api/register",
                                json={"email": reg_email, "password": reg_password},
                            )
                            if res.status_code == 201:
                                st.success("Account created! Please log in.")
                            else:
                                st.error(res.json().get("detail", "Registration failed."))
                        except Exception as e:
                            st.error(f"Cannot connect to backend: {e}")
                    else:
                        st.warning("Please fill in all fields.")

    else:
        # User is authenticated
        st.success(f"👤 Logged in as:\n**{st.session_state.user_email}**")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.just_logged_out = True
            st.session_state.token = None
            st.session_state.user_email = None
            st.session_state.session_id = None
            st.session_state.uploaded_filename = None
            st.session_state.chat_history = []
            st.session_state.quiz_data = []
            st.session_state.quiz_submitted = False

            # Safe cookie expiration without crashing on KeyError
            past_time = datetime.now() - timedelta(days=1)
            cookie_manager.set("notemind_token", "", expires_at=past_time, key="clr_tok")
            cookie_manager.set("notemind_email", "", expires_at=past_time, key="clr_em")
            cookie_manager.set("notemind_session_id", "", expires_at=past_time, key="clr_sid")
            cookie_manager.set("notemind_filename", "", expires_at=past_time, key="clr_fn")

            time.sleep(0.3)
            st.rerun()

        st.markdown("---")
        st.subheader("Navigation")
        navigation = st.radio(
            "Go to",
            ["📖 Study Room", "📂 My Saved Notes"],
            label_visibility="collapsed",
        )


# ---------------------------------------------------------------------
# 3. Main Area: Require Login Check
# ---------------------------------------------------------------------

if not st.session_state.token:
    st.info("👋 Welcome to NoteMind AI! Please **Log in** or **Register** from the sidebar to begin.")
    st.stop()


# ---------------------------------------------------------------------
# 4. View: 📖 Study Room
# ---------------------------------------------------------------------

if navigation == "📖 Study Room":
    st.header("📖 Study Room")
    st.write("Upload course slides, textbooks, or research papers to unlock AI study tools.")

    # PDF Uploader Section
    col_upload, col_status = st.columns([2, 1])

    with col_upload:
        uploaded_pdf = st.file_uploader(
            "Upload your PDF document",
            type=["pdf"],
            help="Select a PDF to extract and analyze.",
        )

    with col_status:
        st.write("")
        st.write("")
        if uploaded_pdf and st.button("⚡ Process PDF", use_container_width=True):
            with st.spinner("Processing PDF..."):
                try:
                    files = {"file": (uploaded_pdf.name, uploaded_pdf.getvalue(), "application/pdf")}
                    res = requests.post(
                        f"{API_URL}/api/upload-pdf",
                        headers=get_auth_headers(),
                        files=files,
                    )
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.session_id = data["session_id"]
                        st.session_state.uploaded_filename = data["filename"]
                        st.session_state.chat_history = []
                        st.session_state.quiz_data = []
                        st.session_state.quiz_submitted = False

                        # Persist active document to cookies
                        expire_time = datetime.now() + timedelta(days=7)
                        cookie_manager.set("notemind_session_id", str(data["session_id"]), expires_at=expire_time, key="set_sid")
                        cookie_manager.set("notemind_filename", data["filename"], expires_at=expire_time, key="set_fn")
                        time.sleep(0.2)

                        st.success(f"✅ **{data['filename']}** processed successfully!")
                    else:
                        st.error(res.json().get("detail", "Failed to process PDF."))
                except Exception as e:
                    st.error(f"Error uploading PDF: {e}")

    if st.session_state.session_id:
        st.info(f"📄 Active Document: **{st.session_state.uploaded_filename}**")

        # Sub-tabs for Study Features
        tab_notes, tab_chat, tab_quiz = st.tabs(
            ["📝 Notes & Summary", "💬 Chat with PDF", "🎯 Practice Quiz"]
        )

        # ----------------- Sub-Tab 1: Notes & Summary -----------------
        with tab_notes:
            st.subheader("Automated Study Notes & Summary")
            col_b1, col_b2 = st.columns(2)

            with col_b1:
                if st.button("✨ Generate Comprehensive Notes", use_container_width=True):
                    with st.spinner("Generating structured study notes..."):
                        try:
                            res = requests.post(
                                f"{API_URL}/api/generate-notes",
                                headers=get_auth_headers(),
                                json={"session_id": st.session_state.session_id},
                            )
                            if res.status_code == 200:
                                st.session_state["notes_view_mode"] = "comprehensive"
                                st.session_state["last_comprehensive_notes"] = res.json()
                                st.success("Comprehensive notes generated and saved to your library!")
                            else:
                                st.error(res.json().get("detail", "Error generating notes."))
                        except Exception as e:
                            st.error(f"Request failed: {e}")

            with col_b2:
                if st.button("📌 Quick Summary & Takeaways", use_container_width=True):
                    with st.spinner("Generating quick summary..."):
                        try:
                            res = requests.post(
                                f"{API_URL}/api/summary",
                                headers=get_auth_headers(),
                                json={"session_id": st.session_state.session_id},
                            )
                            if res.status_code == 200:
                                st.session_state["notes_view_mode"] = "summary"
                                st.session_state["last_quick_summary"] = res.json()
                            else:
                                st.error(res.json().get("detail", "Error generating summary."))
                        except Exception as e:
                            st.error(f"Request failed: {e}")

            # Visual separation based on selected button view
            view_mode = st.session_state.get("notes_view_mode")

            if view_mode == "comprehensive" and "last_comprehensive_notes" in st.session_state:
                data = st.session_state["last_comprehensive_notes"]
                st.markdown("---")
                st.info("💡 Viewing: **Comprehensive Study Notes**")

                st.markdown("### 📋 Executive Summary")
                st.write(data.get("summary", "No summary available."))

                st.markdown("### 🔑 Key Takeaways")
                for pt in data.get("key_points", []):
                    st.markdown(f"- {pt}")

                st.markdown("### 📚 Full Study Notes")
                st.markdown(data.get("notes", "No notes available."))

            elif view_mode == "summary" and "last_quick_summary" in st.session_state:
                sum_data = st.session_state["last_quick_summary"]
                st.markdown("---")
                st.info("💡 Viewing: **Quick Summary & Takeaways Only**")

                st.markdown("### 📋 Quick Summary")
                st.write(sum_data.get("summary", "No summary available."))

                st.markdown("### 🔑 Key Takeaways")
                for pt in sum_data.get("key_points", []):
                    st.markdown(f"- {pt}")

        # ----------------- Sub-Tab 2: Chat with PDF -----------------
        with tab_chat:
            st.subheader("Ask Questions About Your Document")

            # Render Chat History
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # User Question Input
            user_query = st.chat_input("Ask a question about this document...")
            if user_query:
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(user_query)

                with st.chat_message("assistant"):
                    with st.spinner("Searching document & generating answer..."):
                        try:
                            res = requests.post(
                                f"{API_URL}/api/chat",
                                headers=get_auth_headers(),
                                json={
                                    "question": user_query,
                                    "session_id": st.session_state.session_id,
                                },
                            )
                            if res.status_code == 200:
                                resp_data = res.json()
                                answer = resp_data.get("answer", "")
                                st.markdown(answer)
                                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                            else:
                                st.error(f"Error: {res.status_code} - {res.text}")
                        except Exception as e:
                            st.error(f"Request failed: {e}")

        # ----------------- Sub-Tab 3: Practice Quiz -----------------
        with tab_quiz:
            st.subheader("🎯 Practice Quiz")
            if st.button("Generate Quiz from Document", use_container_width=True):
                with st.spinner("Generating quiz questions..."):
                    try:
                        res = requests.post(
                            f"{API_URL}/api/quiz",
                            headers=get_auth_headers(),
                            json={"session_id": st.session_state.session_id},
                        )
                        if res.status_code == 200:
                            st.session_state.quiz_data = res.json().get("quiz", [])
                            st.session_state.quiz_submitted = False
                            st.rerun()
                        else:
                            st.error(f"Failed to generate quiz: {res.text}")
                    except Exception as e:
                        st.error(f"Error: {e}")

            if st.session_state.quiz_data:
                for idx, q in enumerate(st.session_state.quiz_data, 1):
                    st.markdown(f"**Q{idx}. {q.get('question')}**")
                    options = q.get("options", [])
                    st.radio("Options", options, key=f"q_{idx}", label_visibility="collapsed")

                    # Submitted state me feedback
                    if st.session_state.quiz_submitted:
                        user_ans = st.session_state.get(f"q_{idx}")
                        # Fallback for any key returned by AI
                        correct_ans = q.get("answer") or q.get("correct_answer") or q.get("correctAnswer")
                        
                        if user_ans and correct_ans and user_ans.strip() == correct_ans.strip():
                            st.success(f"✅ Correct! Answer: {correct_ans}")
                        else:
                            st.error(f"❌ Incorrect! Correct Answer: {correct_ans}")
                    st.write("")

                if st.button("Submit Quiz", use_container_width=True):
                    st.session_state.quiz_submitted = True
                    score = 0
                    for idx, q in enumerate(st.session_state.quiz_data, 1):
                        selected = st.session_state.get(f"q_{idx}")
                        correct = q.get("answer") or q.get("correct_answer") or q.get("correctAnswer")
                        if selected and correct and selected.strip() == correct.strip():
                            score += 1
                    st.success(f"🎉 Final Score: {score}/{len(st.session_state.quiz_data)}")
                    st.rerun()

# ---------------------------------------------------------------------
# 5. View: 📂 My Saved Notes
# ---------------------------------------------------------------------

elif navigation == "📂 My Saved Notes":
    st.header("📂 My Saved Notes")
    st.write("Browse your saved study notes and summaries.")

    try:
        res = requests.get(f"{API_URL}/api/notes", headers=get_auth_headers())
        if res.status_code == 200:
            saved_notes = res.json()
            if not saved_notes:
                st.info("No saved notes found yet. Go to the Study Room to generate notes!")
            else:
                for note in saved_notes:
                    note_id = note.get("id")
                    with st.expander(f"📄 {note.get('title', 'Untitled')} - {note.get('created_at', '')[:10]}"):
                        st.markdown("### Executive Summary")
                        st.write(note.get("summary", "No summary available."))
                        st.markdown("### Full Notes")
                        st.markdown(note.get("notes", "No notes content."))
                        
                        st.markdown("---")
                        # Delete button
                        if st.button("🗑️ Delete Note", key=f"del_note_{note_id}"):
                            del_res = requests.delete(f"{API_URL}/api/notes/{note_id}", headers=get_auth_headers())
                            if del_res.status_code == 200:
                                st.success("Note deleted!")
                                st.rerun()
                            else:
                                st.error("Failed to delete note.")
        else:
            st.error("Failed to fetch saved notes.")
    except Exception as e:
        st.error(f"Error loading notes: {e}")